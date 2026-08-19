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
