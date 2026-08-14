"""Taxonomie des playlists et paramètres généraux."""

import json
import os
from pathlib import Path

# --- Spotify -----------------------------------------------------------------

# Client ID d'une app Spotify (https://developer.spotify.com/dashboard).
# Flow PKCE : aucun client secret nécessaire.
SPOTIFY_CLIENT_ID = os.environ.get("SPOTIFY_CLIENT_ID", "")
REDIRECT_URI = "http://127.0.0.1:8888/callback"

# URL publique de l'interface web, ex. https://sort.mondomaine.fr
# Le callback OAuth devient BASE_URL + /spotify/callback : cette URL exacte doit
# figurer dans les Redirect URIs de l'app Spotify.
BASE_URL = os.environ.get("BASE_URL", "").rstrip("/")

# En mode serveur, aucune ouverture de navigateur local n'est possible.
HEADLESS = os.environ.get("SPOTIFY_SORT_HEADLESS") == "1"

# --- Emplacement des données ------------------------------------------------
#
# Tout vit dans le dossier du projet : exports dans out/, secrets dans secrets/.
# SPOTIFY_SORT_HOME permet de déplacer l'ensemble ailleurs.

PROJECT_DIR = Path(__file__).resolve().parent.parent
STATE_DIR = Path(os.environ.get("SPOTIFY_SORT_HOME", PROJECT_DIR))
SECRETS_DIR = STATE_DIR / "secrets"

# Ancien emplacement, conservé le temps de migrer les installations existantes.
LEGACY_SECRETS_DIR = Path.home() / ".spotify-sort"


def secret_file(name: str) -> Path:
    """Chemin d'un secret, en récupérant l'ancien emplacement si besoin."""
    path = SECRETS_DIR / name
    if path.exists():
        return path

    legacy = LEGACY_SECRETS_DIR / {"token.json": "token.json"}.get(name, name)
    if legacy.exists():
        SECRETS_DIR.mkdir(parents=True, exist_ok=True)
        SECRETS_DIR.chmod(0o700)
        path.write_bytes(legacy.read_bytes())
        path.chmod(0o600)
        print(
            f"Secret repris depuis {legacy} vers {path}.\n"
            f"  Supprime l'ancien quand tu as vérifié :  rm {legacy}"
        )
    return path
SCOPES = [
    "user-library-read",
    "user-library-modify",  # ajouter aux Titres likés
    "playlist-modify-private",
    "playlist-modify-public",
    "playlist-read-private",
]

# --- Claude ------------------------------------------------------------------

CLAUDE_MODEL = "claude-opus-5"
CLAUDE_EFFORT = "medium"
BATCH_SIZE = 40          # titres envoyés par requête de classification
MAX_CONCURRENCY = 6      # requêtes Claude en parallèle

# Seuil d'inclusion : "large" remplit davantage les playlists en acceptant les
# titres qui correspondent raisonnablement ; "stricte" ne garde que les évidences.
TOLERANCE = "large"

# --- Playlists de référence --------------------------------------------------
#
# Playlists existantes sur ton compte qui servent d'exemples au classement :
#   "nom exact de la playlist Spotify" -> clé de catégorie
# Leurs titres sont injectés dans le prompt comme référence — c'est ton jugement
# qui définit la catégorie, pas celui du modèle.

REFERENCE_PLAYLISTS = {
    "white girl music vieux": "white-girl-music",
}

MAX_REFERENCE_EXAMPLES = 80  # par catégorie, pour garder le prompt raisonnable

# --- Playlists ---------------------------------------------------------------
#
# Chaque entrée : clé -> (nom de la playlist, description, méthode)
#   "rule" : déterminé par les métadonnées Spotify (date, genres de l'artiste)
#   "llm"  : jugement sémantique délégué à Claude
#
# Un titre peut appartenir à plusieurs playlists. La playlist décennie est
# toujours attribuée, ce qui garantit qu'aucun titre ne reste orphelin.

MOODS = {
    "chill": "Calme, posé, ambiance douce — écoute de fond, détente.",
    "vibe": "Groovy, cool, tête qui bouge — sans être festif ni calme.",
    "fete": "Fête, club, soirée — énergie haute, fait danser.",
    "melancolie": "Triste, mélancolique, nostalgique, introspectif.",
    "energie": "Énergie brute — sport, salle, motivation, adrénaline.",
    "romance": "Amour, sensualité, slow, chansons de couple.",
}

SPECIALS = {
    "classiques": (
        "Classiques intemporels, tubes universellement reconnus, toutes époques "
        "et tous genres confondus (Queen, Michael Jackson, Nirvana, Daft Punk…)."
    ),
    "classiques-francais": (
        "Classiques de la chanson française et du patrimoine musical francophone "
        "(Brel, Gainsbourg, Piaf, Balavoine, Goldman, Téléphone, IAM…)."
    ),
    "white-girl-music": (
        "Pop/indie pop anglophone émotionnelle et fédératrice, faite pour être "
        "chantée à tue-tête entre amis ou en voiture — le tube nostalgique qui "
        "fait crier tout le monde au refrain. Cœur de cible : les années 2000-2010 "
        "et la pop girly, la pop-rock indé, la country-pop et le folk US. "
        "Taylor Swift, Lana Del Rey, Olivia Rodrigo, Lorde, Hozier, Katy Perry, "
        "Miley Cyrus, Avril Lavigne, Kelly Clarkson, Britney Spears, Rihanna, "
        "Ariana Grande, Sia, P!nk, Dua Lipa, Sabrina Carpenter, Chappell Roan, "
        "Gracie Abrams, Noah Kahan, Zach Bryan, The Lumineers, Mumford & Sons, "
        "Florence + The Machine, Phoebe Bridgers, Fleetwood Mac, ABBA, "
        "The Killers « Mr. Brightside », Journey « Don't Stop Believin' », "
        "Whitney Houston, Cyndi Lauper, Bon Jovi « Livin' on a Prayer », "
        "Toto « Africa », Queen « Don't Stop Me Now », les tubes Disney/musicals. "
        "Ce n'est ni péjoratif ni réservé aux sorties récentes : un classique des "
        "années 80 repris en soirée en fait partie."
    ),
    "troll": (
        "Chansons troll : humour, mèmes internet, parodies, nanars assumés, "
        "morceaux qu'on met pour faire rire ou trigger les gens."
    ),
    "films-et-series": (
        "Musiques apparaissant dans un film ou une série (BO originale OU titre "
        "préexistant rendu célèbre par une scène), ou thème identifiable."
    ),
    "tres-vieux": "Très vieux morceaux — sortis avant 1980.",
}

GENRES = {
    "rap-us": "Rap et hip-hop américain.",
    "rap-uk": (
        "Rap britannique : UK drill, grime, UK hip-hop, road rap. "
        "Central Cee, Dave, Stormzy, Skepta, J Hus, Headie One, Digga D, ArrDee, "
        "Aitch, Little Simz, Slowthai, Giggs, Wiley, Kano. L'accent britannique, "
        "les prods drill (808 glissés, hi-hats) et le grime en sont les marqueurs."
    ),
    "rap-fr": "Rap et hip-hop francophone.",
    "pop": "Pop mainstream, variété internationale.",
    "rock": "Rock, punk, indie rock, alternatif.",
    "metal": "Metal, hard rock, hardcore.",
    "electro": "Électro, house, techno, EDM, drum and bass.",
    "rnb-soul": "R&B, soul, funk, disco.",
    "jazz-blues": "Jazz, blues, swing.",
    "reggae-afro": "Reggae, dancehall, afrobeats, afropop.",
    "latino": "Reggaeton, salsa, latin pop.",
    "country-folk": "Country, folk, americana.",
    "classique-instrumental": "Musique classique, orchestrale, instrumentale, BO.",
    "chanson-francaise": "Chanson française et variété francophone (hors rap).",
}

DECADES = ["1950s", "1960s", "1970s", "1980s", "1990s", "2000s", "2010s", "2020s"]

# Playlists décidées par Claude (mood + spécial + genre)
LLM_CATEGORIES = {**MOODS, **SPECIALS, **GENRES}

# Nom affiché sur Spotify pour chaque clé
DISPLAY_NAMES = {
    "chill": "Chill",
    "vibe": "Vibe",
    "fete": "Fête",
    "melancolie": "Mélancolie",
    "energie": "Énergie",
    "romance": "Romance",
    "classiques": "Classiques",
    "classiques-francais": "Classiques français",
    "white-girl-music": "White girl music",
    "troll": "Troll",
    "films-et-series": "Films et séries",
    "tres-vieux": "Très vieux",
    "rap-us": "Rap US",
    "rap-uk": "Rap UK",
    "rap-fr": "Rap FR",
    "pop": "Pop",
    "rock": "Rock",
    "metal": "Metal",
    "electro": "Électro",
    "rnb-soul": "R&B / Soul",
    "jazz-blues": "Jazz / Blues",
    "reggae-afro": "Reggae / Afro",
    "latino": "Latino",
    "country-folk": "Country / Folk",
    "classique-instrumental": "Classique / Instrumental",
    "chanson-francaise": "Chanson française",
    "divers": "Divers",
}

PLAYLIST_PREFIX = ""     # ex. "🎵 " pour préfixer tous les noms créés
PLAYLIST_PUBLIC = False  # les playlists créées sont privées par défaut


def display_name(key: str) -> str:
    """Nom lisible d'une playlist à partir de sa clé."""
    return PLAYLIST_PREFIX + DISPLAY_NAMES.get(key, key)


# --- Overrides persistés (édités depuis l'interface web) ---------------------
#
# Les valeurs ci-dessus sont les défauts du code. settings.json, s'il existe, les
# surcharge à chaud sans réécrire ce fichier.

SETTINGS_PATH = Path(
    os.environ.get("SPOTIFY_SORT_SETTINGS", STATE_DIR / "out" / "settings.json")
)

_GROUPS = {"moods": MOODS, "genres": GENRES, "specials": SPECIALS}


def current_settings() -> dict:
    """État courant, sous la forme sérialisable utilisée par settings.json."""
    return {
        "tolerance": TOLERANCE,
        "playlist_public": PLAYLIST_PUBLIC,
        "playlist_prefix": PLAYLIST_PREFIX,
        "reference_playlists": dict(REFERENCE_PLAYLISTS),
        "categories": {
            group: {
                key: {"name": DISPLAY_NAMES.get(key, key), "description": desc}
                for key, desc in mapping.items()
            }
            for group, mapping in _GROUPS.items()
        },
    }


def apply_settings(data: dict) -> None:
    """Applique des overrides en mémoire. Les clés absentes gardent leur défaut."""
    global TOLERANCE, PLAYLIST_PUBLIC, PLAYLIST_PREFIX, REFERENCE_PLAYLISTS, LLM_CATEGORIES

    if data.get("tolerance") in {"large", "stricte"}:
        TOLERANCE = data["tolerance"]
    if isinstance(data.get("playlist_public"), bool):
        PLAYLIST_PUBLIC = data["playlist_public"]
    if isinstance(data.get("playlist_prefix"), str):
        PLAYLIST_PREFIX = data["playlist_prefix"]
    if isinstance(data.get("reference_playlists"), dict):
        REFERENCE_PLAYLISTS = {
            str(k): str(v) for k, v in data["reference_playlists"].items()
        }

    for group, entries in (data.get("categories") or {}).items():
        mapping = _GROUPS.get(group)
        if mapping is None or not isinstance(entries, dict):
            continue
        mapping.clear()
        for key, spec in entries.items():
            if not isinstance(spec, dict) or not spec.get("description"):
                continue
            mapping[key] = spec["description"]
            DISPLAY_NAMES[key] = spec.get("name") or key

    LLM_CATEGORIES = {**MOODS, **SPECIALS, **GENRES}


def save_settings(data: dict) -> None:
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    apply_settings(data)


def load_settings() -> None:
    if SETTINGS_PATH.exists():
        try:
            apply_settings(json.loads(SETTINGS_PATH.read_text()))
        except (ValueError, OSError) as exc:
            print(f"settings.json ignoré ({exc}) — défauts du code utilisés.")


load_settings()
