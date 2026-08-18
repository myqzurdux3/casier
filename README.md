# Casier

Récupère tous tes titres likés Spotify, les trie en playlists thématiques
(mood, genre, décennie, catégories spéciales), exporte le résultat en JSON/CSV,
puis crée les playlists sur ton compte quand tu le décides.

Un titre peut appartenir à plusieurs playlists, et aucun titre n'est laissé de côté.

## Comment ça marche

Le tri se fait en deux étages :

| Étage | Ce qu'il décide | Comment |
|---|---|---|
| Règles | décennies (1960s → 2020s), « très vieux » | date de sortie de l'album |
| Claude | mood, genre, classiques, troll, films/séries, white girl music… | jugement sémantique sur les métadonnées |

> **Pourquoi Claude et pas l'API Spotify ?** Spotify a supprimé l'accès aux
> *audio features* (energy, danceability, valence, tempo) pour les nouvelles
> applications fin 2024. Et même avec elles, aucune API ne sait dire si un
> morceau est « troll » ou apparaît dans une série.

## Playlists générées

**Moods** — Chill · Vibe · Fête · Mélancolie · Énergie · Romance
**Genres** — Rap US · Rap UK · Rap FR · Pop · Rock · Metal · Électro · R&B/Soul · Jazz/Blues · Reggae/Afro · Latino · Country/Folk · Classique/Instrumental · Chanson française
**Spéciales** — Classiques · Classiques français · White girl music · Troll · Films et séries · Très vieux
**Décennies** — 1950s → 2020s

Tout est modifiable dans `spotify_sort/config.py` : ajoute une clé au bon
dictionnaire avec une description, elle est automatiquement prise en compte par
le prompt, l'export et l'import.

### Régler le remplissage

`TOLERANCE` dans `config.py` :

- `"large"` (défaut) — playlists bien remplies : plusieurs moods et genres par
  titre, et une correspondance raisonnable suffit pour les catégories spéciales.
- `"stricte"` — un seul mood, un seul genre, et uniquement les évidences.

### Playlists de référence

Le meilleur moyen de cadrer une catégorie floue est de montrer des exemples
plutôt que de les décrire. `REFERENCE_PLAYLISTS` associe une playlist existante
de ton compte à une catégorie :

```python
REFERENCE_PLAYLISTS = {
    "white girl music vieux": "white-girl-music",
}
```

Ses titres sont lus et injectés dans le prompt comme référence faisant autorité :
le modèle en déduit l'esprit commun et l'applique largement, y compris à des
artistes absents de ta liste. `sort` les récupère tout seul au premier lancement ;
`python main.py reference` force la relecture après avoir modifié la playlist.

## Installation

```bash
pip install -r requirements.txt
```

### 1. App Spotify

Crée une app sur <https://developer.spotify.com/dashboard>, ajoute cette
Redirect URI **exactement** :

```
http://127.0.0.1:8888/callback
```

Puis :

```bash
export SPOTIFY_CLIENT_ID=ton_client_id
```

Pas de client secret : l'outil utilise le flow OAuth PKCE. Le token est mis en
cache dans `~/.spotify-sort/token.json` et rafraîchi automatiquement.

### 2. Clé API Claude

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

(ou `ant auth login`, que le SDK détecte tout seul).

## Utilisation

```bash
# 1. Récupérer les titres likés (et les genres des artistes)
python main.py fetch

# 2. Trier et exporter — n'écrit que des fichiers, ne touche pas au compte
python main.py sort

# Test rapide sur 40 titres avant de lancer sur toute la bibliothèque
python main.py sort --limit 40

# 3. Voir ce que l'import ferait, sans rien créer
python main.py import out/playlists.json --dry-run

# 4. Créer les playlists sur ton compte
python main.py import out/playlists.json

# Ou seulement certaines
python main.py import out/playlists.json --only troll white-girl-music rap-us
```

### Cohérence avec les Titres likés

Tout morceau rangé dans une playlist est aussi ajouté aux Titres likés s'il n'y
est pas déjà — que ce soit via `import` ou `track --add`.

Pour rattraper l'existant :

```bash
python main.py sync-likes --dry-run   # liste sans rien modifier
python main.py sync-likes             # like les manquants
```

Parcourt les playlists dont tu es propriétaire, repère les titres absents des
likés et les ajoute. Bouton équivalent sur le tableau de bord web.

> Ces opérations exigent le scope `user-library-modify`. Un token obtenu avant
> son ajout ne l'a pas : l'outil le détecte et redemande une autorisation.

### Trier un titre à l'unité

Pour un morceau découvert après coup, sans relancer tout le classement :

```bash
# Dit dans quelles playlists il va, sans rien modifier
python main.py track "https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT"

# Et l'y ajoute réellement
python main.py track "https://open.spotify.com/track/..." --add

# Plusieurs d'un coup
python main.py track LIEN1 LIEN2 LIEN3 --add
```

Accepte un lien `open.spotify.com` (avec ou sans `?si=`, y compris les URL
`/intl-xx/`), une URI `spotify:track:…` ou un ID brut. Avec `--add`, un titre
déjà présent n'est pas ajouté deux fois, et les playlists qui n'existent pas
encore sur ton compte sont signalées plutôt que créées.

### Fichiers produits

| Fichier | Contenu |
|---|---|
| `out/liked.json` | cache brut des titres likés |
| `out/playlists.json` | le classement — c'est ce fichier que `import` consomme |
| `out/tracks.csv` | une ligne par titre avec ses playlists, pour relire dans un tableur |

Comme `playlists.json` est un simple fichier texte, tu peux le corriger à la
main avant l'import : déplacer un titre, vider une playlist, renommer.

## Interface web

Mono-utilisateur, pensée pour tourner derrière un reverse proxy HTTPS.

```bash
pip install -r requirements.txt

export WEB_PASSWORD='une phrase de passe longue'   # obligatoire, 12 car. minimum
export BASE_URL='https://sort.mondomaine.fr'       # obligatoire
export SPOTIFY_CLIENT_ID='...'
export ANTHROPIC_API_KEY='sk-ant-...'

gunicorn -w 1 -b 127.0.0.1:8000 webapp:app
```

Ajoute `https://sort.mondomaine.fr/spotify/callback` aux Redirect URIs de ton app
Spotify — l'interface l'affiche sur le tableau de bord si tu as un doute.

> **`-w 1` n'est pas optionnel.** Les tâches et leur journal vivent en mémoire du
> processus. Avec plusieurs workers, une page de progression tomberait au hasard
> sur un worker qui ne connaît pas le job.

`TRUST_PROXY=1` est nécessaire derrière un reverse proxy : sans lui, l'app ignore
`X-Forwarded-Proto` et génère un `redirect_uri` en `http://` que Spotify refuse.

### Exposer directement sur le réseau (0.0.0.0)

Sans reverse proxy, sur un LAN ou un VPN de confiance :

```bash
export WEB_PASSWORD='une phrase de passe longue'
export HOST=0.0.0.0
export ALLOW_INSECURE=1        # sinon le cookie exige HTTPS et la connexion boucle
gunicorn -w 1 -b 0.0.0.0:8000 webapp:app
```

Laisse `TRUST_PROXY` **non défini** : exposé en direct, faire confiance à
`X-Forwarded-For` laisserait n'importe qui forger son IP et contourner la limite
de tentatives de connexion.

Trois conséquences à connaître :

1. **Tout circule en clair.** Mot de passe et cookie de session sont lisibles par
   quiconque écoute le réseau. Le serveur affiche un avertissement au démarrage.
   Acceptable sur un LAN privé ou un VPN, jamais sur Internet.
2. **`ALLOW_INSECURE=1` retire le flag `Secure` du cookie.** `HttpOnly` et
   `SameSite=Lax` restent en place, mais le cookie devient interceptable.
3. **La connexion Spotify ne peut pas se faire depuis cette adresse.** Spotify
   n'accepte que des Redirect URIs en HTTPS, à l'exception de l'adresse de
   bouclage littérale `127.0.0.1`. Un `http://192.168.x.x:8000/spotify/callback`
   est refusé côté Spotify.

   Contournement : autorise une fois en local, puis sers-toi du dashboard réseau.
   Le token est mis en cache dans `~/.spotify-sort/token.json` et partagé par la
   CLI et l'interface web.

   ```bash
   python main.py doctor      # sur la machine, ouvre le navigateur en 127.0.0.1
   ```

Pour un accès distant réel, un VPN (Tailscale, WireGuard) est préférable à une
exposition directe : tu gardes un LAN de confiance sans ouvrir de port.

### Pages

| Page | Rôle |
|---|---|
| Tableau de bord | état (Spotify, clé Claude, caches), lancement des tâches, diagnostic |
| Progression | journal en direct de la tâche en cours, rafraîchi chaque seconde |
| Résultat | playlists et titres, retrait d'un titre, sélection puis import |
| Titre à l'unité | coller un lien, voir les playlists proposées, ajouter |
| Réglages | tolérance, playlists de référence, édition de la taxonomie |

Les réglages sont écrits dans `out/settings.json` et surchargent `config.py` à
chaud, sans toucher au code. La CLI lit le même fichier : les deux restent
cohérentes.

### Sécurité

Ce qui est en place, puisque l'instance est exposée :

- mot de passe obligatoire (refus de démarrer sans, ou sous 12 caractères),
  comparé en temps constant, avec limite de 8 tentatives par IP sur 5 minutes ;
- cookie de session `HttpOnly`, `SameSite=Lax`, `Secure` (désactivable par
  `ALLOW_INSECURE=1` **pour un test local en HTTP uniquement**) ;
- jeton CSRF exigé sur toute requête POST, régénéré à la connexion ;
- `?next=` restreint aux chemins internes, pas d'open redirect ;
- `meta noindex`, et aucun secret rendu dans les pages.

Ce qui reste à ta charge : **le HTTPS**. Sans lui, le mot de passe circule en
clair et Spotify refusera le callback. Exemple nginx :

```nginx
location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
}
```

`X-Forwarded-Proto` est nécessaire : sans lui l'app génère un `redirect_uri` en
`http://`, que Spotify rejette.

### Service systemd

```ini
[Unit]
Description=spotify-sort
After=network.target

[Service]
WorkingDirectory=/opt/spotify-sort
Environment=WEB_PASSWORD=...
Environment=BASE_URL=https://sort.mondomaine.fr
Environment=SPOTIFY_CLIENT_ID=...
Environment=ANTHROPIC_API_KEY=...
ExecStart=/opt/spotify-sort/.venv/bin/gunicorn -w 1 -b 127.0.0.1:8000 webapp:app
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Mets plutôt les secrets dans un fichier `EnvironmentFile=` en `chmod 600` : les
`Environment=` d'une unité systemd sont lisibles par tous via `systemctl show`.

## App Android

Une app native pilote le tout depuis le téléphone, avec la même couverture que
le panel. Le geste qui la justifie : depuis Spotify, « Partager → spotify-sort »
classe le titre et l'ajoute aux playlists comme aux likés.

```
mobile/          projet Expo — voir mobile/README.md
api.py           API JSON /api/v1 consommée par l'app
```

L'app s'authentifie avec le même `WEB_PASSWORD`, échangé une fois contre un
jeton conservé dans le stockage sécurisé du téléphone. Le serveur est joint en
TLS avec un certificat auto-signé que l'app est seule à accepter — voir
`deploy/README.md`, section 4.

### Architecture

```
spotify_sort/service.py   tâches métier, aucune dépendance Flask
webapp.py                 façade HTML : Jinja, session cookie, CSRF
api.py                    façade JSON : jeton porteur, erreurs à codes stables
```

Les deux façades partagent `service.py` et `jobs.py` : l'app et le panel voient
le même job en cours et les mêmes fichiers de sortie. Un tri lancé depuis le
téléphone se suit depuis l'ordinateur, et réciproquement.

### Tests

```bash
python -m pytest          # 73 tests : API, jobs, service, non-régression du panel
cd mobile && npm test     # client API contre un serveur local
```

## Dépannage

```bash
python main.py doctor
```

Teste un par un chaque droit d'accès — scopes du token, lecture du profil, de la
bibliothèque et des playlists, accès au catalogue, et création d'une playlist de
test aussitôt supprimée. Chaque ligne indique ✓ ou ✗ avec le message exact de
Spotify, ce qui localise précisément un `403`.

**Migration Web API du 9 mars 2026** — Spotify a supprimé plusieurs endpoints
d'écriture. Cet outil utilise les remplaçants :

| Supprimé (403 pour tous) | Remplaçant utilisé ici |
|---|---|
| `POST /users/{id}/playlists` | `POST /me/playlists` |
| `POST /playlists/{id}/tracks` | `POST /playlists/{id}/items` |
| `PUT /me/tracks` | `PUT /me/library?uris=spotify:track:…` |
| `GET /artists?ids=…` | `GET /artists/{id}`, une requête par artiste |

Deux changements de forme faciles à manquer : `PUT /me/library` attend des
**URI complets en paramètre de requête** (`uris=`), pas des identifiants nus dans
le corps, et plafonne à 40 par appel. Et **tous** les endpoints groupés par
`ids=` ont disparu — il faut une requête par élément.

Un `403` à l'écriture avec l'un des chemins de gauche dans l'URL signale du code
resté sur l'ancienne API.

**`403` à la création alors que toutes les lectures passent** — le token est
valide et le chemin est le bon ; le blocage est côté compte ou app. `doctor`
affiche le corps brut de la réponse Spotify et te donne un `curl` prêt à coller
pour reproduire hors de l'outil. Même 403 en curl ⇒ ce n'est pas le code.

1. **App en Development Mode** : dashboard Spotify → ton app → *User Management*.
   Ton compte doit y figurer avec le nom d'affichage **et** l'e-mail exacts du
   compte Spotify.
2. **Compte incapable de créer une playlist** : vérifie à la main sur
   open.spotify.com. Un compte enfant ou géré ne le peut pas.
3. **Mauvais compte connecté** : `doctor` affiche l'identifiant vu par l'API.

**`403` sur `/v1/artists`** — c'est l'étape qui récupère les genres des artistes.
Elle est facultative : l'outil bascule sur des requêtes artiste par artiste, et
si c'est aussi refusé il continue sans genres. La classification se fait alors
sur titre / artiste / album / année, ce qui reste l'essentiel du signal.

Le message exact renvoyé par Spotify est affiché — il indique la cause
(portée de token, app en Development Mode, restriction de marché…). Pour tester
la même requête à la main :

```bash
curl -s -H "Authorization: Bearer $(python -c \
  'import json,pathlib;print(json.loads((pathlib.Path.home()/".spotify-sort/token.json").read_text())["access_token"])')" \
  "https://api.spotify.com/v1/artists/0TnOYISbd1XYRBk9myaseg" | head -c 400
```

Si tu changes les scopes dans `config.py`, supprime `~/.spotify-sort/token.json`
pour forcer une nouvelle autorisation — le token en cache garde les anciens.

## Notes

- L'import **saute** toute playlist dont le nom existe déjà sur ton compte —
  aucune playlist existante n'est modifiée ou écrasée.
- L'import est reprenable : une playlist en échec est signalée et les suivantes
  continuent ; relancer la même commande ne recrée pas ce qui existe déjà.
  Après trois échecs d'affilée il s'arrête, le problème étant global.
- Les playlists sont créées en privé (`PLAYLIST_PUBLIC` dans `config.py`, ou
  `--public`).
- Coût Claude : les titres partent par lots de 40 avec le prompt en cache.
  Compte quelques dizaines de centimes pour ~1000 titres.
- Un lot qui échoue est signalé et ignoré : ses titres retombent sur leur
  playlist décennie plutôt que de faire planter tout le run.
- `fetch` écrit `liked.json` **avant** d'aller chercher les genres : un échec à
  cette étape ne fait jamais reperdre les titres déjà récupérés.
