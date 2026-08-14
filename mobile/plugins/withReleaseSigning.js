/**
 * Plugin de configuration Expo : signer la version release avec ta propre clé.
 *
 * Par défaut le gabarit Expo signe la release avec la clé de debug. Ça produit
 * un APK installable, mais la clé de debug est régénérée si le dossier
 * `android/` disparaît — et Android refuse alors la mise à jour d'une app dont
 * la signature a changé. Il faudrait désinstaller, donc perdre le jeton stocké.
 *
 * Le keystore est lu depuis `android/gradle.properties`, où `expo prebuild`
 * recopie les propriétés déclarées ici. Rien de tout ça n'est versionné.
 *
 * Sans les variables d'environnement, le plugin ne fait rien : la signature de
 * debug reste en place, et un simple `prebuild` fonctionne sans configuration.
 */

const { withAppBuildGradle, withGradleProperties } = require('expo/config-plugins');

const CONFIG = {
  storeFile: process.env.SPOTIFY_SORT_KEYSTORE,
  storePassword: process.env.SPOTIFY_SORT_KEYSTORE_PASSWORD,
  keyAlias: process.env.SPOTIFY_SORT_KEY_ALIAS || 'spotify-sort',
  keyPassword:
    process.env.SPOTIFY_SORT_KEY_PASSWORD || process.env.SPOTIFY_SORT_KEYSTORE_PASSWORD,
};

const PROPERTIES = {
  SPOTIFY_SORT_STORE_FILE: 'storeFile',
  SPOTIFY_SORT_STORE_PASSWORD: 'storePassword',
  SPOTIFY_SORT_KEY_ALIAS: 'keyAlias',
  SPOTIFY_SORT_KEY_PASSWORD: 'keyPassword',
};

const withProperties = (config) =>
  withGradleProperties(config, (cfg) => {
    for (const [key, field] of Object.entries(PROPERTIES)) {
      const existing = cfg.modResults.findIndex(
        (item) => item.type === 'property' && item.key === key
      );
      const entry = { type: 'property', key, value: CONFIG[field] };
      if (existing >= 0) cfg.modResults[existing] = entry;
      else cfg.modResults.push(entry);
    }
    return cfg;
  });

const withSigningConfig = (config) =>
  withAppBuildGradle(config, (cfg) => {
    let gradle = cfg.modResults.contents;

    if (!gradle.includes('signingConfigs {')) {
      throw new Error("withReleaseSigning : bloc signingConfigs introuvable dans build.gradle.");
    }

    // Ajout du bloc `release` à côté du `debug` existant.
    gradle = gradle.replace(
      /signingConfigs \{/,
      `signingConfigs {
        release {
            storeFile file(SPOTIFY_SORT_STORE_FILE)
            storePassword SPOTIFY_SORT_STORE_PASSWORD
            keyAlias SPOTIFY_SORT_KEY_ALIAS
            keyPassword SPOTIFY_SORT_KEY_PASSWORD
        }`
    );

    // Le gabarit met `signingConfigs.debug` dans le buildType release : on ne
    // remplace que cette occurrence-là, pas celle du buildType debug.
    gradle = gradle.replace(
      /(release \{\s*\n\s*(?:\/\/[^\n]*\n\s*)*)signingConfig signingConfigs\.debug/,
      '$1signingConfig signingConfigs.release'
    );

    cfg.modResults.contents = gradle;
    return cfg;
  });

module.exports = (config) => {
  if (!CONFIG.storeFile || !CONFIG.storePassword) {
    return config; // non configuré : on garde la signature de debug
  }
  return withSigningConfig(withProperties(config));
};
