# Casier

**Français** · [English](README.en.md)

Range tes titres likés Spotify dans des playlists thématiques — mood, genre,
décennie — en confiant le jugement à Claude. Ligne de commande, panel web et
app Android, sur le même moteur.

Un titre peut appartenir à plusieurs playlists, et aucun titre n'est laissé de côté.

```bash
python main.py fetch    # lit tes titres likés
python main.py sort     # les classe — n'écrit que des fichiers
python main.py import out/playlists.json   # crée les playlists sur ton compte
```

Rien n'est créé sur ton compte tant que tu ne lances pas `import`.

---

## Pourquoi Claude plutôt que l'API Spotify

Spotify a supprimé l'accès aux *audio features* (energy, danceability, valence,
tempo) pour les nouvelles applications fin 2024. Et même du temps où elles
existaient, aucune API ne savait dire qu'un morceau est un classique, un troll,
ou vient d'une bande originale de série.

Le tri se fait donc en deux étages :

| Étage | Ce qu'il décide | Comment |
|---|---|---|
| Règles | décennies (1950s → 2020s), « très vieux » | date de sortie de l'album |
| Claude | mood, genre, classiques, troll, films et séries… | jugement sémantique sur les métadonnées |

## Les trois surfaces

| | Pour quoi faire |
|---|---|
| **CLI** | le moteur complet, scriptable, idéal pour la première grosse passe |
| **Panel web** | tout piloter depuis un navigateur, suivre un tri en direct, éditer la taxonomie |
| **App Android** | depuis Spotify, « Partager → Casier » range un titre en un geste |

Les trois partagent `service.py` et `jobs.py` : un tri lancé depuis le téléphone
se suit depuis l'ordinateur, et réciproquement.

## Playlists générées

**Moods** — Chill · Vibe · Fête · Mélancolie · Énergie · Romance
**Genres** — Rap US · Rap UK · Rap FR · Pop · Rock · Metal · Électro · R&B/Soul · Jazz/Blues · Reggae/Afro · Latino · Country/Folk · Classique/Instrumental · Chanson française
**Spéciales** — Classiques · Classiques français · White girl music · Troll · Films et séries · Très vieux
**Décennies** — 1950s → 2020s

Tout est modifiable dans `spotify_sort/config.py` : ajoute une clé au bon
dictionnaire avec une description, elle est automatiquement prise en compte par
le prompt, l'export et l'import. Le panel web permet la même chose sans toucher
au code.

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

Ses titres sont injectés dans le prompt comme référence faisant autorité : le
modèle en déduit l'esprit commun et l'applique largement, y compris à des
artistes absents de ta liste.

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
déjà présent n'est pas ajouté deux fois, et les playlists absentes de ton compte
sont signalées plutôt que créées.

### Cohérence avec les Titres likés

Tout morceau rangé dans une playlist est aussi ajouté aux Titres likés s'il n'y
est pas déjà. Pour rattraper l'existant :

```bash
python main.py sync-likes --dry-run   # liste sans rien modifier
python main.py sync-likes             # like les manquants
```

> Ces opérations exigent le scope `user-library-modify`. Un token obtenu avant
> son ajout ne l'a pas : l'outil le détecte et redemande une autorisation.

### Fichiers produits

| Fichier | Contenu |
|---|---|
| `out/liked.json` | cache brut des titres likés |
| `out/playlists.json` | le classement — c'est ce fichier que `import` consomme |
| `out/tracks.csv` | une ligne par titre avec ses playlists, pour relire dans un tableur |

Comme `playlists.json` est un simple fichier texte, tu peux le corriger à la
main avant l'import : déplacer un titre, vider une playlist, renommer.

## Panel web

Mono-utilisateur, pensé pour tourner derrière un reverse proxy HTTPS.

```bash
export WEB_PASSWORD='une phrase de passe longue'   # obligatoire, 12 car. minimum
export BASE_URL='https://sort.mondomaine.fr'       # obligatoire
export SPOTIFY_CLIENT_ID='...'
export ANTHROPIC_API_KEY='sk-ant-...'

gunicorn -w 1 -b 127.0.0.1:8000 webapp:app
```

Ajoute `https://sort.mondomaine.fr/spotify/callback` aux Redirect URIs de ton app
Spotify — le tableau de bord affiche l'URL exacte si tu as un doute.

> **`-w 1` n'est pas optionnel.** Les tâches et leur journal vivent en mémoire du
> processus. Avec plusieurs workers, une page de progression tomberait au hasard
> sur un worker qui ne connaît pas le job.

`TRUST_PROXY=1` est nécessaire derrière un reverse proxy : sans lui, l'app ignore
`X-Forwarded-Proto` et génère un `redirect_uri` en `http://` que Spotify refuse.

Le déploiement complet — TLS, unité systemd durcie, certificat pour l'app
Android — est décrit dans [`deploy/README.md`](deploy/README.md).

| Page | Rôle |
|---|---|
| Tableau de bord | état (Spotify, clé Claude, caches), lancement des tâches, diagnostic |
| Progression | journal en direct de la tâche en cours |
| Résultat | playlists et titres, retrait d'un titre, sélection puis import |
| Titre à l'unité | coller un lien, voir les playlists proposées, ajouter |
| Réglages | tolérance, playlists de référence, édition de la taxonomie |

Les réglages sont écrits dans `out/settings.json` et surchargent `config.py` à
chaud. La CLI lit le même fichier : les deux restent cohérentes.

### Sécurité

- mot de passe obligatoire (refus de démarrer sans, ou sous 12 caractères),
  comparé en temps constant, limite de 8 tentatives par IP sur 5 minutes ;
- cookie de session `HttpOnly`, `SameSite=Lax`, `Secure` ;
- jeton CSRF exigé sur toute requête POST, régénéré à la connexion ;
- `?next=` restreint aux chemins internes, pas d'open redirect ;
- `meta noindex`, aucun secret rendu dans les pages.

Ce qui reste à ta charge : **le HTTPS**. Sans lui, le mot de passe circule en
clair et Spotify refusera le callback.

## App Android

Le geste qui la justifie : depuis Spotify, « Partager → Casier » classe le titre
et l'ajoute aux playlists comme aux likés, sans quitter l'app.

```
mobile/    projet Expo — voir mobile/README.md
api.py     API JSON /api/v1 consommée par l'app
```

L'app s'authentifie avec le même `WEB_PASSWORD`, échangé une fois contre un
jeton conservé dans le stockage sécurisé du téléphone. Le serveur est joint en
TLS avec un certificat auto-signé que l'app est **seule** à accepter : les
autorités système sont explicitement exclues pour cet hôte.

L'adresse du serveur n'a pas de valeur par défaut utilisable — le dépôt publie
`192.0.2.10`, une adresse de documentation. Renseigne la tienne à la
construction :

```bash
export SPOTIFY_SORT_HOST=ton.serveur SPOTIFY_SORT_PORT=8000
npx expo prebuild --platform android --clean
```

## Langues

L'app et le panel sont bilingues français / anglais. L'app suit la langue du
téléphone, avec un choix explicite dans Réglages ; le panel suit l'en-tête
`Accept-Language` du navigateur.

Ne sont **pas** traduits, délibérément : les noms de playlists, qui sont les
noms réels sur ton compte Spotify et que l'import retrouve par leur nom, et les
descriptions de catégories, qui constituent le prompt envoyé à Claude.

## Architecture

```
spotify_sort/service.py   tâches métier, aucune dépendance Flask
webapp.py                 façade HTML : Jinja, session cookie, CSRF
api.py                    façade JSON : jeton porteur, erreurs à codes stables
spotify_sort/jobs.py      tâches longues en arrière-plan, journal consultable
```

### Tests

```bash
python -m pytest          # API, jobs, service, non-régression du panel, traductions
cd mobile && npm test     # client API, couleurs, catalogue de messages
cd mobile && npx tsc --noEmit
```

## Dépannage

```bash
python main.py doctor
```

Teste un par un chaque droit d'accès — scopes du token, lecture du profil, de la
bibliothèque et des playlists, accès au catalogue, et création d'une playlist de
test aussitôt supprimée. Chaque ligne indique ✓ ou ✗ avec le message exact de
Spotify, ce qui localise précisément un `403`.

### Migration Web API du 9 mars 2026

Spotify a supprimé plusieurs endpoints d'écriture. Cet outil utilise les
remplaçants :

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

### `403` à la création alors que toutes les lectures passent

Le token est valide et le chemin est le bon ; le blocage est côté compte ou app.
`doctor` affiche le corps brut de la réponse et donne un `curl` prêt à coller
pour reproduire hors de l'outil. Même 403 en curl ⇒ ce n'est pas le code.

1. **App en Development Mode** : dashboard Spotify → ton app → *User Management*.
   Ton compte doit y figurer avec le nom d'affichage **et** l'e-mail exacts.
2. **Compte incapable de créer une playlist** : vérifie à la main sur
   open.spotify.com. Un compte enfant ou géré ne le peut pas.
3. **Mauvais compte connecté** : `doctor` affiche l'identifiant vu par l'API.

### `403` sur `/v1/artists`

C'est l'étape qui récupère les genres des artistes. Elle est facultative :
l'outil bascule sur des requêtes artiste par artiste, et si c'est aussi refusé
il continue sans genres. La classification se fait alors sur titre / artiste /
album / année, ce qui reste l'essentiel du signal.

Si tu changes les scopes dans `config.py`, supprime `~/.spotify-sort/token.json`
pour forcer une nouvelle autorisation — le token en cache garde les anciens.

## Notes

- L'import **saute** toute playlist dont le nom existe déjà sur ton compte —
  aucune playlist existante n'est modifiée ou écrasée.
- L'import est reprenable : une playlist en échec est signalée et les suivantes
  continuent. Après trois échecs d'affilée il s'arrête, le problème étant global.
- Les playlists sont créées en privé (`PLAYLIST_PUBLIC` dans `config.py`, ou
  `--public`).
- Coût Claude : les titres partent par lots de 40 avec le prompt en cache.
  Compte quelques dizaines de centimes pour ~1000 titres.
- Un lot qui échoue est signalé et ignoré : ses titres retombent sur leur
  playlist décennie plutôt que de faire planter tout le run.
- `fetch` écrit `liked.json` **avant** d'aller chercher les genres : un échec à
  cette étape ne fait jamais reperdre les titres déjà récupérés.

## Licence

MIT — voir [LICENSE](LICENSE).

Ce projet n'est ni affilié à Spotify ni à Anthropic. « Spotify » est une marque
déposée de Spotify AB, employée ici uniquement pour désigner le service.
