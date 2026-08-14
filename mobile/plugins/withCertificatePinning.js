/**
 * Plugin de configuration Expo : épinglage du certificat du serveur.
 *
 * Écrit `res/xml/network_security_config.xml` et y déclare, POUR LE SEUL hôte
 * de spotify-sort, une confiance limitée à notre autorité — les autorités
 * système sont explicitement exclues. Une autorité publique compromise ne peut
 * donc pas se faire passer pour le serveur.
 *
 * L'épinglage vit au niveau du système Android, pas dans le code JavaScript :
 * `fetch` reste du `fetch` ordinaire, aucun écran n'a de logique TLS.
 *
 * Prérequis : `assets/ca.crt`, produit par `deploy/make-certs.sh`.
 */

const fs = require('fs');
const path = require('path');
const {
  AndroidConfig,
  withAndroidManifest,
  withDangerousMod,
} = require('expo/config-plugins');

const CA_ASSET = 'assets/ca.crt';
const RAW_NAME = 'spotify_sort_ca';

function networkSecurityConfig(host) {
  // cleartextTrafficPermitted=false : même une redirection vers http:// est
  // refusée, pour que l'app ne puisse pas silencieusement retomber en clair.
  return `<?xml version="1.0" encoding="utf-8"?>
<!-- Généré par plugins/withCertificatePinning.js — ne pas éditer à la main. -->
<network-security-config>
    <domain-config cleartextTrafficPermitted="false">
        <domain includeSubdomains="false">${host}</domain>
        <trust-anchors>
            <certificates src="@raw/${RAW_NAME}" />
        </trust-anchors>
    </domain-config>
    <base-config cleartextTrafficPermitted="false">
        <trust-anchors>
            <certificates src="system" />
        </trust-anchors>
    </base-config>
</network-security-config>
`;
}

const withFiles = (config, { host }) =>
  withDangerousMod(config, [
    'android',
    async (cfg) => {
      const res = path.join(cfg.modRequest.platformProjectRoot, 'app/src/main/res');

      const source = path.join(cfg.modRequest.projectRoot, CA_ASSET);
      if (!fs.existsSync(source)) {
        throw new Error(
          `withCertificatePinning : ${CA_ASSET} est introuvable.\n` +
            "Génère les certificats sur le serveur puis copie l'autorité :\n" +
            '  ./deploy/make-certs.sh <ip-du-serveur>\n' +
            '  cp secrets/ca.crt mobile/assets/ca.crt\n' +
            "Sans ce fichier l'app ne pourrait joindre aucun serveur."
        );
      }

      fs.mkdirSync(path.join(res, 'raw'), { recursive: true });
      fs.mkdirSync(path.join(res, 'xml'), { recursive: true });
      fs.copyFileSync(source, path.join(res, 'raw', `${RAW_NAME}.crt`));
      fs.writeFileSync(
        path.join(res, 'xml', 'network_security_config.xml'),
        networkSecurityConfig(host)
      );
      return cfg;
    },
  ]);

const withManifest = (config) =>
  withAndroidManifest(config, (cfg) => {
    const application = AndroidConfig.Manifest.getMainApplicationOrThrow(cfg.modResults);
    application.$['android:networkSecurityConfig'] = '@xml/network_security_config';
    // Par défaut Android 9+ interdit déjà le trafic en clair ; on le rend
    // explicite pour que la valeur ne dépende pas de la version cible.
    application.$['android:usesCleartextTraffic'] = 'false';
    return cfg;
  });

module.exports = (config, options = {}) => {
  const host = options.host;
  if (!host) {
    throw new Error("withCertificatePinning : l'option `host` est obligatoire.");
  }
  return withManifest(withFiles(config, { host }));
};
