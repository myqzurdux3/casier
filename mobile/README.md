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

## Construire l'APK en local

Sans compte Expo ni service tiers. Prérequis : JDK 17 et le SDK Android
(`ANDROID_HOME`).

### Une seule fois — la clé de signature

```bash
keytool -genkeypair -v -storetype PKCS12 -keystore spotify-sort.keystore \
  -alias spotify-sort -keyalg RSA -keysize 2048 -validity 10000
```

**Garde ce fichier hors du dépôt et sauvegarde-le.** Android refuse de mettre à
jour une app dont la signature a changé : le perdre oblige à désinstaller puis
réinstaller, donc à se reconnecter.

### À chaque construction

```bash
export SPOTIFY_SORT_KEYSTORE=$PWD/spotify-sort.keystore
export SPOTIFY_SORT_KEYSTORE_PASSWORD='…'

npx expo prebuild --platform android --clean
cd android && ./gradlew assembleRelease
```

APK dans `android/app/build/outputs/apk/release/app-release.apk`. Compter une
dizaine de minutes la première fois, beaucoup moins ensuite.

Sans ces variables la construction fonctionne quand même : `withReleaseSigning`
ne s'active pas et Gradle retombe sur la clé de debug d'Expo. Suffisant pour un
essai, à éviter pour l'app que tu gardes.

### Installer

```bash
adb install -r android/app/build/outputs/apk/release/app-release.apk
```

Ou copie l'APK sur le téléphone et ouvre-le.

### Vérifier ce que contient l'APK

```bash
apksigner verify --print-certs app-release.apk
unzip -p app-release.apk res/DB.crt | openssl x509 -noout -fingerprint -sha256
```

L'empreinte doit être celle de `secrets/ca.crt` sur le serveur. Le nom du
fichier de ressource change d'une construction à l'autre — AAPT renomme les
ressources en release.

### Alternative : EAS Build

```bash
npx eas login && npm run build:apk
```

Construit dans le cloud, gère la signature tout seul. Utile sans SDK Android
local. Pour changer d'adresse de serveur, édite `eas.json`
(`SPOTIFY_SORT_HOST`, `SPOTIFY_SORT_PORT`) — l'hôte entre à la fois dans
l'épinglage et dans l'adresse proposée à la connexion.

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
