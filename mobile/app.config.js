// Configuration Expo. En .js et non en .json pour lire l'hôte du serveur
// depuis l'environnement : il apparaît à la fois dans la configuration réseau
// Android (quel hôte épingler) et dans les valeurs par défaut de l'app.
//
//   SPOTIFY_SORT_HOST=192.0.2.10 SPOTIFY_SORT_PORT=8000 npx expo prebuild

const HOST = process.env.SPOTIFY_SORT_HOST || '192.0.2.10';
const PORT = process.env.SPOTIFY_SORT_PORT || '8000';

module.exports = {
  expo: {
    name: 'spotify-sort',
    slug: 'spotify-sort',
    version: '0.5.0',
    orientation: 'portrait',
    scheme: 'spotifysort',
    userInterfaceStyle: 'dark',
    icon: './assets/icon.png',
    // Icônes produites par tools/make-icons.py. Motif propre au projet : le
    // logo Spotify est une marque déposée, et leurs Developer Terms interdisent
    // de l'employer comme icône d'application.
    android: {
      package: 'fr.spotifysort.app',
      versionCode: 1,
      permissions: ['INTERNET'],
      adaptiveIcon: {
        foregroundImage: './assets/adaptive-icon.png',
        backgroundColor: '#121212',
      },
    },
    plugins: [
      'expo-router',
      [
        'expo-splash-screen',
        {
          image: './assets/splash-icon.png',
          backgroundColor: '#121212',
          imageWidth: 200,
        },
      ],
      'expo-secure-store',
      // `disableIOS` parce que le projet est Android uniquement : sans cela le
      // plugin exige un bundleIdentifier iOS qui n'a pas lieu d'exister.
      // `text/*` couvre le text/plain que partage Spotify, et ses variantes.
      ['expo-share-intent', { disableIOS: true, androidIntentFilters: ['text/*'] }],
      // Épinglage : l'app ne fait confiance qu'à notre autorité pour cet hôte,
      // et refuse explicitement les autorités système. Voir plugins/.
      ['./plugins/withCertificatePinning', { host: HOST }],
      // Ne fait rien tant que SPOTIFY_SORT_KEYSTORE n'est pas défini.
      './plugins/withReleaseSigning',
    ],
    extra: {
      defaultBaseUrl: `https://${HOST}:${PORT}`,
      pinnedHost: HOST,
      router: {},
    },
  },
};
