# App mobile Android pour spotify-sort — design

**Date :** 2026-08-14
**Version visée :** 0.5.0
**État :** approuvé, prêt pour le plan d'implémentation

## Objectif

Piloter spotify-sort depuis un téléphone Android, avec parité complète avec le
panel web, et un geste que l'ordinateur ne permet pas : partager un titre depuis
Spotify vers l'app pour qu'il soit classé et ajouté immédiatement.

Le backend reste sur le VPS `192.0.2.10`, dans `/opt/spotify-sort`.

## Décisions prises

| Sujet | Choix | Écarté |
|---|---|---|
| Type d'app | Native, React Native + Expo | PWA, WebView |
| Plateforme | Android uniquement | iOS, multiplateforme |
| Périmètre | Parité complète avec le panel | Titre à l'unité seul |
| Architecture | API JSON à côté du panel, logique partagée | Backend API pur, WebView |
| Transport | HTTPS, certificat auto-signé épinglé dans l'app | Domaine + Let's Encrypt, VPN, HTTP clair |
| Distribution | APK via EAS Build, installation directe | Play Store |

Le panel web reste en service et inchangé pour l'utilisateur.

## Architecture

### Découpage

`webapp.py` fait aujourd'hui 620 lignes et mélange routes HTTP, tâches métier et
rendu. Les tâches sont extraites :

```
spotify_sort/service.py   tâches métier, aucun import Flask
webapp.py                 façade HTML : Jinja, session cookie, CSRF
api.py                    façade JSON : blueprint /api/v1, jeton porteur
```

Migrent vers `service.py`, sans changement de comportement : `_task_fetch`,
`_task_reference`, `_task_sort`, `_task_import`, `_task_doctor`,
`_task_sync_likes`, `_classify_one`, et le retrait d'un titre du document de
résultat. Ces fonctions ne dépendent déjà d'aucun objet Flask — elles impriment
leur progression et retournent des données.

Les deux façades appellent le même `service.py` et le même `jobs.py`. La
contrainte d'un seul job à la fois est conservée : l'app et le panel observent le
même job en cours.

### Surface de l'API

Toutes les routes sous `/api/v1`, toutes en JSON, toutes derrière le jeton
porteur sauf `auth/login`.

```
POST   /api/v1/auth/login          {password}         -> {token}
GET    /api/v1/status                                 -> likes, spotify_ready, job courant, version
POST   /api/v1/tracks/classify     {link, add}        -> {track, rows}
POST   /api/v1/jobs/<action>       {limit?, keys?, public?} -> {job_id}
GET    /api/v1/jobs/<id>?since=N                      -> journal incrémental, statut
GET    /api/v1/result                                 -> document de playlists
DELETE /api/v1/result/<key>/<track_id>                -> retire un titre
GET    /api/v1/settings                               -> réglages courants
PUT    /api/v1/settings                               -> enregistre
```

`<action>` prend les mêmes valeurs que le panel : `fetch`, `reference`, `sort`,
`import`, `doctor`, `sync-likes`.

La route existante `/api/jobs/<id>`, utilisée par le JavaScript du panel, reste
en place et inchangée. Elle ne fait pas partie de `/api/v1`.

### Authentification

`WEB_PASSWORD` reste le mot de passe unique. `POST /api/v1/auth/login` renvoie un
jeton aléatoire de 32 octets.

- Stockage serveur : `secrets/api-tokens.json`, chaque jeton haché en SHA-256,
  jamais en clair. Fichier en 0600.
- Transport : en-tête `Authorization: Bearer <token>`.
- Stockage client : Expo SecureStore, adossé au keystore matériel Android. Pas
  `AsyncStorage`, lisible sur un téléphone rooté.
- Révocation : supprimer le fichier déconnecte tous les téléphones. Pas
  d'expiration automatique.
- La limite de tentatives existante (`_throttled`, 8 essais par 5 minutes et par
  IP) s'applique à `/api/v1/auth/login`, sinon l'API devient le point faible du
  mot de passe.

Pas de protection CSRF sur `/api/v1` : sans cookie, il n'y a rien à falsifier
depuis un autre site. C'est la raison du jeton porteur plutôt que de la session.

## Transport et certificat

### Sur le serveur

`deploy/make-certs.sh` génère un mini-CA propre à l'installation :

```
secrets/ca.crt        autorité, validité 10 ans, à embarquer dans l'app
secrets/server.crt    certificat serveur, SAN = IP:192.0.2.10
secrets/server.key    clé privée, 0600, ne quitte jamais le VPS
```

Gunicorn les sert directement via `--certfile` et `--keyfile`. Pas de reverse
proxy ajouté, donc `TRUST_PROXY` reste à 0.

### Dans l'app

Un plugin de configuration Expo écrit `res/xml/network_security_config.xml` et
copie `ca.crt` dans `res/raw`. Pour le seul domaine `192.0.2.10`, la
configuration fait confiance à ce CA et **exclut les autorités système**. Une
autorité publique compromise ne peut donc pas se faire passer pour le serveur.

Conséquence pratique : `fetch` reste du `fetch` ordinaire, aucun code réseau
particulier dans les écrans.

### Limites connues

- Le certificat ne vaut que pour l'app. Le callback OAuth Spotify passe par le
  navigateur du téléphone ou de l'ordinateur, qui affichera un avertissement à
  accepter une fois. Spotify ne vérifie pas le certificat : il exige seulement
  une URL en `https://`, ce qui est satisfait.
- `BASE_URL` doit devenir `https://192.0.2.10`, et cette URL exacte doit
  figurer dans les Redirect URIs de l'app Spotify.
- Le CA embarqué impose de reconstruire l'APK si la clé fuit, et dans dix ans à
  l'expiration. À documenter dans `deploy/README.md`.

## Application

### Pile

Expo SDK 54, TypeScript, `expo-router` en navigation par onglets.

| Écran | Contenu |
|---|---|
| Connexion | Adresse du serveur, mot de passe, stockage du jeton |
| Accueil | Nombre de likes, état Spotify, boutons des six actions |
| Job | Journal défilant, rafraîchi toutes les 1,5 s via le curseur `since` |
| Titre | Champ lien, interrupteur « ajouter réellement », tableau des playlists |
| Résultat | Playlists calculées, détail des titres, glisser pour retirer |
| Réglages | Tolérance, préfixe, playlists publiques, édition de la taxonomie |

Un module `api.ts` unique porte le client HTTP : il injecte le jeton et, sur
`401`, renvoie vers l'écran de connexion. Aucun écran ne parle du réseau
directement.

### Partage depuis Spotify

`expo-share-intent` déclare un filtre d'intention Android sur `text/plain`.
Depuis Spotify, « Partager → spotify-sort » ouvre l'app sur l'écran Titre, lien
pré-rempli, classement lancé aussitôt.

### Distribution

`eas build -p android --profile preview` produit un APK, à installer
directement. Nécessite un compte Expo gratuit ; la construction se fait sur
leurs serveurs.

## Erreurs

L'API répond toujours la même forme :

```json
{"error": {"code": "spotify_denied", "message": "403 sur /me/library — …"}}
```

| Code | HTTP | Sens |
|---|---|---|
| `bad_token` | 401 | Jeton absent, invalide ou révoqué |
| `bad_request` | 400 | Entrée invalide, lien non reconnu |
| `spotify_disconnected` | 409 | Aucun token Spotify — l'app propose la reconnexion |
| `job_busy` | 409 | Un job tourne déjà ; la réponse porte son `job_id` |
| `spotify_denied` | 502 | L'API Spotify a refusé |
| `internal` | 500 | Tout le reste |

Le message reprend `_error_text()` : le nom de la classe est inclus quand
`str(exc)` est vide. Le gestionnaire global d'exceptions couvre le blueprint, de
sorte qu'aucune page HTML ne peut être renvoyée à un client attendant du JSON.

Côté app, trois cas distincts plutôt qu'un écran générique :

1. Serveur injoignable — « Vérifie le réseau », bouton Réessayer.
2. Certificat refusé — message explicite : l'APK est plus ancien que le
   certificat du serveur.
3. Erreur métier — le message tel quel.

Un job en échec reste consultable : `status: "error"` et journal complet.

## Tests

Pytest sur la façade JSON, avec le client de test Flask :

- connexion : bon mot de passe donne un jeton ; mauvais donne 401 ; la limite de
  tentatives se déclenche
- toute route sans jeton donne 401 ; avec un jeton révoqué, 401
- `classify` : lien invalide donne 400 et non 500 ; Spotify en panne donne 502
  avec le message
- jobs : démarrage, curseur `since` qui ne renvoie jamais deux fois les mêmes
  lignes, second job refusé en 409
- `service.py` : tâches appelées avec un faux client Spotify, sans réseau ni clé
  Claude

Côté React Native : vérification TypeScript et test de `api.ts` contre un serveur
simulé. Pas de tests d'interface — l'outillage coûterait plus qu'il ne
rapporterait pour cinq écrans mono-utilisateur.

## Hors périmètre

Notifications push, mode hors-ligne, multi-utilisateur, rafraîchissement de
jeton, publication sur le Play Store, support iOS.

## Suite

Implémenté le 2026-08-14, en quatre commits :

| Commit | Contenu |
|---|---|
| `62f0471` | dépôt git initialisé sur l'état existant |
| `4d1a9f5` | extraction de `service.py` |
| `a69fb8e` | API `/api/v1` et 73 tests |
| `74c8c7f` | app Expo et TLS épinglé |

Écarts par rapport au design, tous vérifiés :

- `expo-share-intent` v5 au lieu de v4 — la v4 exige Expo 53, le projet est en
  54. Option `disableIOS` ajoutée : le plugin réclamait sinon un
  `bundleIdentifier` iOS qui n'a pas lieu d'exister sur un projet Android.
- Filtre d'intention sur `text/*` plutôt que `text/plain` seul, pour couvrir les
  variantes de type MIME sans rien perdre.
- Port 8443 plutôt que 443 : gunicorn tourne sans privilège root.
- `throttle.py` extrait en plus du découpage prévu, pour que le panel et l'API
  partagent un seul compteur de tentatives.
- Correction imprévue dans `task_doctor`, qui ne rattrapait que `SpotifyError` :
  une coupure réseau faisait planter le diagnostic.
