/**
 * Catalogue des messages de l'interface, et traduction pure.
 *
 * Séparé de `i18n.tsx` pour ne contenir aucun JSX : ce fichier se compile seul
 * et `tests/messages.test.js` peut le vérifier sous Node, sans monter React.
 *
 * Jumeau de `spotify_sort/i18n.py`, mais les deux catalogues ne se recouvrent
 * presque pas : le serveur ne traduit que ce qu'il produit lui-même (erreurs,
 * libellés de tâches), le client tout le reste. Les verdicts de classement sont
 * la seule zone commune — le serveur les envoie sous forme de clés, et c'est
 * ici qu'ils deviennent lisibles, sans aller-retour réseau.
 *
 * Ne sont pas traduits, et c'est délibéré : les noms de playlists, qui sont les
 * noms réels sur le compte Spotify, et les journaux de progression, produits en
 * français par le cœur métier.
 */

export type Lang = 'fr' | 'en';
/** `auto` suit la langue du téléphone ; les autres l'imposent. */
export type LangPref = 'auto' | Lang;

const PREF_KEY = 'casier_language';

export const MESSAGES: Record<string, Record<Lang, string>> = {
  // --- Commun ---
  'commun.reessayer': { fr: 'Réessayer', en: 'Retry' },
  'commun.annuler': { fr: 'Annuler', en: 'Cancel' },
  'commun.ouverture': { fr: 'Ouverture…', en: 'Opening…' },
  'commun.lecture_etat': { fr: "Lecture de l'état…", en: 'Reading status…' },

  // --- Bandeau d'erreur ---
  'erreur.oauth_navigateur': {
    fr: "La liaison OAuth passe par un navigateur : ouvre le panel web sur un ordinateur et connecte ton compte Spotify depuis le tableau de bord.",
    en: 'OAuth linking goes through a browser: open the web panel on a computer and connect your Spotify account from the dashboard.',
  },
  'erreur.certificat': {
    fr: "Sur le serveur : ./deploy/make-certs.sh, puis copie secrets/ca.crt dans mobile/assets/ et reconstruis l'APK.",
    en: 'On the server: ./deploy/make-certs.sh, then copy secrets/ca.crt into mobile/assets/ and rebuild the APK.',
  },

  // --- Onglets et titres d'écran ---
  'onglet.casier': { fr: 'Casier', en: 'Locker' },
  'onglet.titre': { fr: 'Titre', en: 'Track' },
  'onglet.tri': { fr: 'Tri', en: 'Sort' },
  'onglet.reglages': { fr: 'Réglages', en: 'Settings' },
  'ecran.titre_unite': { fr: "Titre à l'unité", en: 'Single track' },
  'ecran.progression': { fr: 'Progression', en: 'Progress' },
  'ecran.connexion': { fr: 'Connexion', en: 'Sign in' },

  // --- Connexion ---
  'connexion.aide': {
    fr: "Le mot de passe est celui du panel web (WEB_PASSWORD). L'app le change une fois contre un jeton, conservé dans le stockage sécurisé du téléphone.",
    en: 'The password is the web panel one (WEB_PASSWORD). The app swaps it once for a token, kept in the phone’s secure storage.',
  },
  'connexion.serveur': { fr: 'Serveur', en: 'Server' },
  'connexion.mot_de_passe': { fr: 'Mot de passe', en: 'Password' },
  'connexion.valider': { fr: 'Se connecter', en: 'Sign in' },
  'connexion.en_cours': { fr: 'Connexion…', en: 'Signing in…' },

  // --- Accueil ---
  'accueil.titres_en_cache': { fr: 'Titres en cache', en: 'Cached tracks' },
  'accueil.casiers': { fr: 'Casiers', en: 'Lockers' },
  'accueil.compte_lie': { fr: 'Compte lié', en: 'Account linked' },
  'accueil.compte_non_lie': { fr: 'Compte non lié', en: 'Account not linked' },
  'accueil.cle_ok': { fr: 'Clé Claude OK', en: 'Claude key OK' },
  'accueil.cle_absente': { fr: 'Clé Claude absente', en: 'Claude key missing' },
  'accueil.avertissement_spotify': {
    fr: "Connecte ton compte Spotify depuis le panel web : la liaison OAuth passe par un navigateur.",
    en: 'Connect your Spotify account from the web panel: OAuth linking goes through a browser.',
  },
  'accueil.suivre_job': { fr: 'Suivre « {name} »', en: 'Follow “{name}”' },
  'accueil.trier': { fr: 'Trier', en: 'Sort' },
  'accueil.estimation': { fr: '{count} titres · {duree}', en: '{count} tracks · {duree}' },
  'accueil.rien_a_classer': { fr: 'rien à classer', en: 'nothing to sort' },
  'accueil.casiers_remplis': { fr: 'Casiers les plus remplis', en: 'Fullest lockers' },
  'accueil.autres_taches': { fr: 'Autres tâches', en: 'Other tasks' },
  'accueil.deconnexion': { fr: 'Déconnexion', en: 'Sign out' },
  'accueil.etat_illisible': {
    fr: "Impossible de lire l'état du serveur.",
    en: 'Could not read the server status.',
  },

  // --- Tâches secondaires ---
  'tache.fetch': { fr: 'Récupérer les likés', en: 'Fetch liked songs' },
  'tache.fetch.aide': { fr: 'Relit la bibliothèque Spotify.', en: 'Re-reads the Spotify library.' },
  'tache.import': { fr: 'Importer', en: 'Import' },
  'tache.import.aide': {
    fr: 'Crée les playlists sur le compte.',
    en: 'Creates the playlists on the account.',
  },
  'tache.sync-likes': { fr: 'Rattraper les likes', en: 'Catch up likes' },
  'tache.sync-likes.aide': {
    fr: 'Like les titres des playlists.',
    en: 'Likes the tracks found in playlists.',
  },
  'tache.reference': { fr: 'Playlists de référence', en: 'Reference playlists' },
  'tache.reference.aide': { fr: 'Relit tes exemples.', en: 'Re-reads your examples.' },
  'tache.doctor': { fr: 'Diagnostic', en: 'Diagnostics' },
  'tache.doctor.aide': {
    fr: 'Vérifie scopes et endpoints.',
    en: 'Checks scopes and endpoints.',
  },

  // --- Tri ---
  'tri.titre': { fr: 'Tri', en: 'Sort' },
  'tri.comptes': {
    fr: '{casiers} casiers · {titres} titres',
    en: '{casiers} lockers · {titres} tracks',
  },
  'tri.aide': {
    fr: "Appui long sur un titre pour le retirer. Le retrait ne touche que le classement local — relance un import pour le répercuter sur Spotify.",
    en: 'Long-press a track to remove it. Removal only affects the local sort — run an import to push it to Spotify.',
  },
  'tri.vide': {
    fr: "Aucun classement enregistré. Lance un tri depuis l'onglet Casier.",
    en: 'No sort saved yet. Run one from the Locker tab.',
  },
  'tri.n_titres': { fr: '{n} titres', en: '{n} tracks' },
  'tri.retirer_titre': { fr: 'Retirer ce titre ?', en: 'Remove this track?' },
  'tri.retirer': { fr: 'Retirer', en: 'Remove' },

  // --- Titre à l'unité ---
  'titre.classer': { fr: 'Classer un titre', en: 'Sort a track' },
  'titre.aide': {
    fr: 'Colle un lien, ou partage un titre depuis Spotify vers Casier',
    en: 'Paste a link, or share a track from Spotify to Casier',
  },
  'titre.ajouter': { fr: 'Ajouter réellement', en: 'Actually add' },
  'titre.ajouter_aide': {
    fr: "Range le titre dans les playlists existantes et l'ajoute aux likés.",
    en: 'Files the track into existing playlists and adds it to your liked songs.',
  },
  'titre.valider': { fr: 'Classer', en: 'Sort' },
  'titre.en_cours': { fr: 'Classement…', en: 'Sorting…' },
  'titre.analyse': {
    fr: 'Claude analyse le titre — jusqu’à une minute.',
    en: 'Claude is analysing the track — up to a minute.',
  },
  'titre.n_casiers': { fr: '{n} casiers', en: '{n} lockers' },
  'titre.rien_modifie': {
    fr: "Rien n'a été modifié — active « Ajouter réellement » pour appliquer.",
    en: 'Nothing was changed — turn on “Actually add” to apply.',
  },

  // --- Verdicts (clés reçues du serveur) ---
  'verdict.proposed': { fr: 'proposé', en: 'proposed' },
  'verdict.added': { fr: 'ajouté', en: 'added' },
  'verdict.already_present': { fr: 'déjà présent', en: 'already there' },
  'verdict.playlist_missing': {
    fr: 'playlist absente du compte',
    en: 'playlist not on account',
  },
  'verdict.failed': { fr: 'échec — {detail}', en: 'failed — {detail}' },
  'verdict.liked_songs': { fr: 'Titres likés', en: 'Liked Songs' },

  // --- Réglages ---
  'reglages.tolerance': { fr: 'Tolérance', en: 'Tolerance' },
  'reglages.tolerance_aide': {
    fr: "« Large » remplit davantage les playlists en acceptant les correspondances raisonnables. « Stricte » ne retient que l'évident.",
    en: '“Large” fills the playlists more by accepting reasonable matches. “Stricte” keeps only the obvious ones.',
  },
  'reglages.large': { fr: 'Large', en: 'Large' },
  'reglages.stricte': { fr: 'Stricte', en: 'Strict' },
  'reglages.playlists': { fr: 'Playlists créées', en: 'Created playlists' },
  'reglages.prefixe': { fr: 'Préfixe', en: 'Prefix' },
  'reglages.prefixe_exemple': { fr: 'ex. « 🎵 »', en: 'e.g. “🎵”' },
  'reglages.publiques': { fr: 'Publiques', en: 'Public' },
  'reglages.publiques_aide': { fr: 'Privées par défaut.', en: 'Private by default.' },
  'reglages.moods': { fr: 'Moods', en: 'Moods' },
  'reglages.genres': { fr: 'Genres', en: 'Genres' },
  'reglages.specials': { fr: 'Catégories spéciales', en: 'Special categories' },
  'reglages.groupe_aide': {
    fr: 'Appui long pour supprimer · création et descriptions depuis le panel web',
    en: 'Long-press to delete · create and edit descriptions from the web panel',
  },
  'reglages.supprimer_categorie': {
    fr: 'Supprimer cette catégorie ?',
    en: 'Delete this category?',
  },
  'reglages.ne_sera_plus_proposee': {
    fr: '« {name} » ne sera plus proposée.',
    en: '“{name}” will no longer be suggested.',
  },
  'reglages.supprimer': { fr: 'Supprimer', en: 'Delete' },
  'reglages.langue': { fr: 'Langue', en: 'Language' },
  'reglages.langue_aide': {
    fr: "« Automatique » suit la langue du téléphone. Les noms de playlists ne changent pas : ce sont ceux de ton compte Spotify.",
    en: '“Automatic” follows the phone’s language. Playlist names never change: they are the ones on your Spotify account.',
  },
  'reglages.langue.auto': { fr: 'Automatique', en: 'Automatic' },
  'reglages.langue.fr': { fr: 'Français', en: 'French' },
  'reglages.langue.en': { fr: 'Anglais', en: 'English' },

  // --- Journal d'un job ---
  'job.ouverture': { fr: 'Ouverture du journal…', en: 'Opening the log…' },
  'job.running': { fr: 'en cours…', en: 'running…' },
  'job.done': { fr: 'terminé', en: 'done' },
  'job.error': { fr: 'échec', en: 'failed' },
  'job.pas_de_sortie': { fr: 'Pas encore de sortie.', en: 'No output yet.' },
};

/**
 * Langue du téléphone.
 *
 * Lue via `Intl` plutôt qu'avec `expo-localization` : pas de module natif à
 * ajouter, donc pas de reconstruction du projet natif. Le try/catch n'est pas
 * décoratif — si le moteur JS ne fournissait pas `Intl`, une exception ici
 * planterait l'app au démarrage, et ni le typecheck ni les tests ne le verraient.
 */
export function detectLang(): Lang {
  try {
    const etiquette = Intl.DateTimeFormat().resolvedOptions().locale ?? '';
    return etiquette.toLowerCase().startsWith('en') ? 'en' : 'fr';
  } catch {
    return 'fr';
  }
}

export function translate(cle: string, langue: Lang, params?: Record<string, string | number>) {
  const entree = MESSAGES[cle];
  // Une clé inconnue est rendue telle quelle : un message manquant doit
  // dégrader l'affichage, jamais faire disparaître l'écran.
  if (!entree) return cle;
  const texte = entree[langue] ?? entree.fr ?? cle;
  if (!params) return texte;
  return texte.replace(/\{(\w+)\}/g, (brut, nom) =>
    nom in params ? String(params[nom]) : brut
  );
}
