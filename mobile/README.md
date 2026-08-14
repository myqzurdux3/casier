# spotify-sort — app Android

App native Expo, parité complète avec le panel web, plus le geste qui justifie
le natif : depuis Spotify, « Partager → spotify-sort » classe le titre et
l'ajoute aux playlists et aux likés.

## Prérequis

- Le backend déployé en TLS — voir `../deploy/README.md`, section 4.
- Node 20 ou plus.
- Un compte Expo (gratuit) pour construire l'APK.

## Installation

```bash
cd mobile
npm install
cp ../secrets/ca.crt assets/ca.crt      # depuis le serveur
```

Sans `assets/ca.crt`, `expo prebuild` s'arrête avec un message explicite : un
APK sans l'autorité ne pourrait joindre aucun serveur.

## Construire l'APK

```bash
npx eas login
npm run build:apk
```

EAS construit sur ses serveurs et renvoie un lien de téléchargement. Installe le
fichier sur le téléphone (autoriser « sources inconnues » à la première fois).

Pour changer d'adresse de serveur, édite `eas.json` (`SPOTIFY_SORT_HOST` et
`SPOTIFY_SORT_PORT`) — l'hôte entre à la fois dans l'épinglage du certificat et
dans l'adresse proposée à la connexion.

## Développement

```bash
npm run typecheck   # vérification TypeScript
npm test            # tests du client API contre un serveur local
npm start           # Metro, avec un build de développement
```

## Épinglage du certificat

`plugins/withCertificatePinning.js` écrit `res/xml/network_security_config.xml`
et y déclare, **pour le seul hôte du serveur**, une confiance limitée à ton
autorité — les autorités système sont explicitement exclues. Une autorité
publique compromise ne peut donc pas se faire passer pour ton serveur.

L'épinglage vit au niveau du système Android : `fetch` reste du `fetch`
ordinaire et aucun écran ne contient de logique TLS.

Conséquence : régénérer les certificats du serveur impose de reconstruire
l'APK. L'app le dit clairement plutôt que d'afficher une panne réseau.

## Structure

| Chemin | Rôle |
|---|---|
| `lib/api.ts` | seul module réseau — jeton, erreurs typées, délais |
| `lib/session.ts` | jeton dans SecureStore, adresse du serveur |
| `app/login.tsx` | mot de passe échangé contre un jeton |
| `app/(tabs)/index.tsx` | état et lancement des tâches |
| `app/job.tsx` | journal, curseur `since` toutes les 1,5 s |
| `app/(tabs)/track.tsx` | titre à l'unité et partage Spotify |
| `app/(tabs)/result.tsx` | playlists calculées, retrait d'un titre |
| `app/(tabs)/settings.tsx` | tolérance, préfixe, taxonomie |

## Ce que l'app ne fait pas

La connexion OAuth à Spotify passe par un navigateur : elle se fait depuis le
panel web, une fois. L'app consomme ensuite le token du serveur.

Pas de notifications push, pas de mode hors-ligne. Un job lancé depuis le
téléphone continue sur le serveur si l'app est fermée ; il suffit de rouvrir
l'app pour retrouver sa progression.
