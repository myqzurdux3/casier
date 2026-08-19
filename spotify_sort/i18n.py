"""Messages traduits, partagés par l'API et le panel.

Ne couvre que ce que l'utilisateur lit dans une interface : erreurs de l'API,
libellés de tâches, verdicts de classement. Les journaux de progression restent
en français — ils sortent de `print()` disséminés dans tout le cœur métier, et
les traduire demanderait de réécrire chaque appel.

Deux choses n'ont volontairement pas de traduction :

- Les **noms de playlists** (`config.DISPLAY_NAMES`) sont les noms réels sur le
  compte Spotify, et l'import les retrouve par leur nom. Les traduire créerait
  des doublons et laisserait les anciennes orphelines.
- Les **descriptions de catégories** sont le prompt envoyé à Claude. Les
  traduire changerait le classement, pas seulement son affichage.
"""

LANGUES = ("fr", "en")
DEFAUT = "fr"

# Clé -> traduction par langue. Les clés sont stables et testables ; c'est elles
# que l'app mobile reçoit pour les verdicts, afin de traduire côté client sans
# aller-retour réseau.
MESSAGES: dict[str, dict[str, str]] = {
    # --- Erreurs de l'API ---
    "erreur.bad_token": {
        "fr": "Jeton absent, invalide ou révoqué. Reconnecte-toi.",
        "en": "Missing, invalid or revoked token. Sign in again.",
    },
    "erreur.spotify_disconnected": {
        "fr": "Aucun compte Spotify lié. Connecte-le depuis le panel web.",
        "en": "No Spotify account linked. Connect it from the web panel.",
    },
    "erreur.json_attendu": {
        "fr": "Le corps de la requête doit être un objet JSON.",
        "en": "The request body must be a JSON object.",
    },
    "erreur.too_many_attempts": {
        "fr": "Trop de tentatives. Réessaie dans 5 minutes.",
        "en": "Too many attempts. Try again in 5 minutes.",
    },
    "erreur.bad_password": {
        "fr": "Mot de passe incorrect.",
        "en": "Incorrect password.",
    },
    "erreur.action_inconnue": {
        "fr": "Action inconnue : {action}",
        "en": "Unknown action: {action}",
    },
    "erreur.job_busy": {
        "fr": "« {name} » est déjà en cours.",
        "en": "“{name}” is already running.",
    },
    "erreur.limite_invalide": {
        "fr": "`limit` doit être un entier positif.",
        "en": "`limit` must be a positive integer.",
    },
    "erreur.job_inconnu": {
        "fr": "Job inconnu — il a peut-être été purgé.",
        "en": "Unknown job — it may have been purged.",
    },
    "erreur.lien_manquant": {
        "fr": "Champ `link` manquant.",
        "en": "Missing `link` field.",
    },
    "erreur.no_result": {
        "fr": "Aucun classement enregistré. Lance un tri.",
        "en": "No sort saved yet. Run a sort first.",
    },
    "erreur.reglages_vides": {
        "fr": "Aucun réglage fourni.",
        "en": "No setting provided.",
    },
    "erreur.tolerance_invalide": {
        "fr": "`tolerance` vaut « large » ou « stricte ».",
        "en": "`tolerance` must be “large” or “stricte”.",
    },
    # --- Libellés de tâches ---
    "tache.fetch": {"fr": "Récupération des likés", "en": "Fetching liked songs"},
    "tache.reference": {"fr": "Playlists de référence", "en": "Reference playlists"},
    "tache.sort": {"fr": "Classement", "en": "Sorting"},
    "tache.import": {"fr": "Import vers Spotify", "en": "Import to Spotify"},
    "tache.sync-likes": {"fr": "Rattrapage des likes", "en": "Catching up likes"},
    "tache.doctor": {"fr": "Diagnostic", "en": "Diagnostics"},
    # --- Panel web : navigation et pages communes ---
    "panel.tableau_de_bord": {"fr": "Tableau de bord", "en": "Dashboard"},
    "panel.resultat": {"fr": "Résultat", "en": "Result"},
    "panel.titre_unite": {"fr": "Titre à l'unité", "en": "Single track"},
    "panel.reglages": {"fr": "Réglages", "en": "Settings"},
    "panel.deconnexion": {"fr": "Déconnexion", "en": "Sign out"},
    "panel.version_titre": {
        "fr": "Version déployée — comparer avec le dépôt local",
        "en": "Deployed version — compare with the local repository",
    },
    "panel.job_en_cours": {"fr": "« {name} » en cours", "en": "“{name}” running"},
    "panel.voir_progression": {"fr": "voir la progression", "en": "see progress"},
    "panel.connexion": {"fr": "Connexion", "en": "Sign in"},
    "panel.mot_de_passe": {"fr": "Mot de passe", "en": "Password"},
    "panel.se_connecter": {"fr": "Se connecter", "en": "Sign in"},
    "panel.erreur": {"fr": "Erreur", "en": "Error"},
    "panel.erreur_serveur": {"fr": "Erreur serveur", "en": "Server error"},
    "panel.trace_journal": {
        "fr": "La trace complète est dans le journal du service :",
        "en": "The full traceback is in the service log:",
    },
    "panel.retour_tableau": {"fr": "Retour au tableau de bord", "en": "Back to the dashboard"},
    # --- Panel web : tableau de bord ---
    "panel.etat": {"fr": "État", "en": "Status"},
    "panel.compte_spotify": {"fr": "Compte Spotify", "en": "Spotify account"},
    "panel.connecte": {"fr": "connecté", "en": "connected"},
    "panel.non_connecte": {"fr": "non connecté", "en": "not connected"},
    "panel.oublier_token": {"fr": "oublier le token", "en": "forget the token"},
    "panel.connecter": {"fr": "Connecter", "en": "Connect"},
    "panel.cle_claude": {"fr": "Clé API Claude", "en": "Claude API key"},
    "panel.cle_absente": {
        "fr": "— export ANTHROPIC_API_KEY, sinon le classement échoue",
        "en": "— export ANTHROPIC_API_KEY, otherwise sorting fails",
    },
    "panel.likes_en_cache": {"fr": "Titres likés en cache :", "en": "Cached liked songs:"},
    "panel.classement": {"fr": "Classement :", "en": "Sort:"},
    "panel.n_titres_n_playlists": {
        "fr": "{titres} titres, {playlists} playlists",
        "en": "{titres} tracks, {playlists} playlists",
    },
    "panel.aucun": {"fr": "aucun", "en": "none"},
    "panel.aucune": {"fr": "aucune", "en": "none"},
    "panel.references": {"fr": "Références :", "en": "References:"},
    "panel.redirect_uri": {
        "fr": "Redirect URI envoyé à Spotify :",
        "en": "Redirect URI sent to Spotify:",
    },
    "panel.redirect_uri_aide": {
        "fr": "Cette URL exacte doit figurer dans les Redirect URIs de ton app Spotify — la moindre différence donne",
        "en": "This exact URL must be listed in your Spotify app’s Redirect URIs — any difference yields",
    },
    "panel.base_url_absente": {
        "fr": "BASE_URL non défini",
        "en": "BASE_URL not set",
    },
    "panel.base_url_absente_aide": {
        "fr": ": cette valeur est déduite de la requête et changera selon l'adresse utilisée.",
        "en": ": this value is inferred from the request and will change with the address used.",
    },
    "panel.https_requis": {
        "fr": "Spotify refusera cette URL",
        "en": "Spotify will reject this URL",
    },
    "panel.https_requis_aide": {
        "fr": ": seul le HTTPS est accepté, à l'exception de",
        "en": ": only HTTPS is accepted, except for",
    },
    "panel.actions": {"fr": "Actions", "en": "Actions"},
    "panel.action_fetch": {"fr": "1. Récupérer les likés", "en": "1. Fetch liked songs"},
    "panel.action_reference": {"fr": "Relire les références", "en": "Re-read references"},
    "panel.action_sort": {"fr": "2. Classer", "en": "2. Sort"},
    "panel.limite_test": {"fr": "limite (test)", "en": "limit (test)"},
    "panel.action_sync": {"fr": "Rattraper les likes", "en": "Catch up likes"},
    "panel.action_doctor": {"fr": "Diagnostic", "en": "Diagnostics"},
    "panel.sync_aide": {
        "fr": "« Rattraper les likes » parcourt tes playlists et ajoute aux Titres likés tout morceau qui n'y figure pas encore.",
        "en": "“Catch up likes” walks your playlists and adds to Liked Songs any track not already there.",
    },
    "panel.import_aide": {
        "fr": "Le classement n'écrit que des fichiers. Rien n'est créé sur ton compte tant que tu ne lances pas l'import depuis la page Résultat.",
        "en": "Sorting only writes files. Nothing is created on your account until you run the import from the Result page.",
    },
    "panel.dernier_classement": {"fr": "Dernier classement", "en": "Latest sort"},
    "panel.playlist": {"fr": "Playlist", "en": "Playlist"},
    "panel.titres": {"fr": "Titres", "en": "Tracks"},
    "panel.voir_importer": {"fr": "Voir et importer", "en": "View and import"},
    # --- Panel web : résultat ---
    "panel.resume_resultat": {
        "fr": "{titres} titres → {playlists} playlists",
        "en": "{titres} tracks → {playlists} playlists",
    },
    "panel.import_selection_aide": {
        "fr": "Coche les playlists à créer sur ton compte. Celles dont le nom existe déjà sont ignorées — renomme-les sur Spotify pour les régénérer.",
        "en": "Tick the playlists to create on your account. Those whose name already exists are skipped — rename them on Spotify to regenerate them.",
    },
    "panel.creer_public": {"fr": "Créer en public", "en": "Create as public"},
    "panel.importer_selection": {"fr": "Importer la sélection", "en": "Import selection"},
    "panel.tout_cocher": {"fr": "Tout cocher", "en": "Select all"},
    "panel.tout_decocher": {"fr": "Tout décocher", "en": "Deselect all"},
    "panel.n_titres": {"fr": "{n} titres", "en": "{n} tracks"},
    "panel.retirer": {"fr": "retirer", "en": "remove"},
    "panel.retirer_titre": {
        "fr": "Retirer de cette playlist",
        "en": "Remove from this playlist",
    },
    # --- Panel web : titre à l'unité ---
    "panel.classer_titre": {"fr": "Classer un titre", "en": "Sort a track"},
    "panel.lien_spotify": {"fr": "Lien Spotify", "en": "Spotify link"},
    "panel.ajouter_reellement": {
        "fr": "Ajouter réellement aux playlists existantes",
        "en": "Actually add to existing playlists",
    },
    "panel.classer": {"fr": "Classer", "en": "Sort"},
    "panel.lien_aide": {
        "fr": "Accepte un lien {a}, une URI {b} ou un ID brut. Sans la case cochée, rien n'est modifié.",
        "en": "Accepts an {a} link, a {b} URI or a raw ID. Without the box ticked, nothing is changed.",
    },
    # --- Panel web : réglages ---
    "panel.general": {"fr": "Général", "en": "General"},
    "panel.tolerance": {"fr": "Tolérance", "en": "Tolerance"},
    "panel.prefixe": {"fr": "Préfixe des noms créés", "en": "Prefix for created names"},
    "panel.playlists_reference": {"fr": "Playlists de référence", "en": "Reference playlists"},
    "panel.reference_aide": {
        "fr": "Une playlist existante de ton compte qui sert d'exemple pour une catégorie. Ses titres sont injectés dans le prompt comme référence faisant autorité.",
        "en": "An existing playlist on your account, used as an example for a category. Its tracks are injected into the prompt as an authoritative reference.",
    },
    "panel.nom_exact": {"fr": "Nom exact sur Spotify", "en": "Exact name on Spotify"},
    "panel.cle_categorie": {"fr": "Clé de catégorie", "en": "Category key"},
    "panel.reference_vider": {
        "fr": "Vider le nom supprime la référence. Après modification, relance « Relire les références » sur le tableau de bord.",
        "en": "Clearing the name deletes the reference. After changing it, run “Re-read references” from the dashboard.",
    },
    "panel.moods": {"fr": "Moods", "en": "Moods"},
    "panel.genres": {"fr": "Genres", "en": "Genres"},
    "panel.specials": {"fr": "Catégories spéciales", "en": "Special categories"},
    "panel.supprimer": {"fr": "supprimer", "en": "delete"},
    "panel.nouvelle_categorie": {"fr": "Nouvelle catégorie", "en": "New category"},
    "panel.categorie_speciale": {"fr": "Catégorie spéciale", "en": "Special category"},
    "panel.mood": {"fr": "Mood", "en": "Mood"},
    "panel.genre": {"fr": "Genre", "en": "Genre"},
    "panel.enregistrer": {"fr": "Enregistrer", "en": "Save"},
    # --- Messages flash ---
    "flash.spotify_connecte": {"fr": "Compte Spotify connecté.", "en": "Spotify account connected."},
    "flash.token_oublie": {"fr": "Token Spotify oublié.", "en": "Spotify token forgotten."},
    "flash.connecte_spotify": {
        "fr": "Connecte d'abord ton compte Spotify.",
        "en": "Connect your Spotify account first.",
    },
    "flash.aucun_classement": {
        "fr": "Aucun classement. Lance d'abord un classement.",
        "en": "No sort yet. Run a sort first.",
    },
    "flash.titre_retire": {
        "fr": "Titre retiré de la playlist.",
        "en": "Track removed from the playlist.",
    },
    "flash.reglages_enregistres": {"fr": "Réglages enregistrés.", "en": "Settings saved."},
    "flash.state_invalide": {
        "fr": "State OAuth invalide — recommence la connexion.",
        "en": "Invalid OAuth state — start the sign-in again.",
    },
    "flash.spotify_refuse": {"fr": "Spotify a refusé : {detail}", "en": "Spotify refused: {detail}"},
    "flash.echange_echoue": {
        "fr": "Échec de l'échange du code : {detail}",
        "en": "Code exchange failed: {detail}",
    },
    # --- Verdicts de classement d'un titre ---
    "verdict.proposed": {"fr": "proposé", "en": "proposed"},
    "verdict.added": {"fr": "ajouté", "en": "added"},
    "verdict.already_present": {"fr": "déjà présent", "en": "already there"},
    "verdict.playlist_missing": {
        "fr": "playlist absente du compte",
        "en": "playlist not on account",
    },
    "verdict.failed": {"fr": "échec — {detail}", "en": "failed — {detail}"},
    "verdict.liked_songs": {"fr": "Titres likés", "en": "Liked Songs"},
}


def resolve(accept_language: str | None) -> str:
    """Langue à employer, d'après l'en-tête HTTP `Accept-Language`.

    Format : `en-US,en;q=0.9,fr;q=0.8`. On trie par `q` décroissant et on
    retient la première langue connue. Tout ce qui n'est pas reconnu retombe
    sur le français, langue d'origine du projet.
    """
    if not accept_language:
        return DEFAUT

    candidats: list[tuple[float, int, str]] = []
    for index, morceau in enumerate(accept_language.split(",")):
        etiquette, _, parametres = morceau.strip().partition(";")
        etiquette = etiquette.strip().lower()
        if not etiquette:
            continue
        poids = 1.0
        if parametres.strip().startswith("q="):
            try:
                poids = float(parametres.strip()[2:])
            except ValueError:
                poids = 0.0
        # `index` départage à poids égal : l'ordre d'écriture fait foi.
        candidats.append((-poids, index, etiquette))

    for _, _, etiquette in sorted(candidats):
        base = etiquette.split("-")[0]
        if base in LANGUES:
            return base
    return DEFAUT


def t(cle: str, langue: str = DEFAUT, **params) -> str:
    """Traduit `cle`. Une clé inconnue est retournée telle quelle.

    Ne pas lever sur une clé absente : un message manquant doit dégrader
    l'affichage, jamais renvoyer une 500 à la place de l'erreur d'origine.
    """
    entree = MESSAGES.get(cle)
    if entree is None:
        return cle
    texte = entree.get(langue) or entree.get(DEFAUT, cle)
    return texte.format(**params) if params else texte
