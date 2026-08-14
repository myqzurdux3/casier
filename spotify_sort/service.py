"""Tâches métier de spotify-sort, indépendantes de toute façade.

Le panel web (`webapp.py`) et l'API mobile (`api.py`) appellent ces fonctions.
Aucune n'importe Flask : elles impriment leur progression — captée par
`jobs.py` quand elles tournent en arrière-plan — et retournent des données.
"""

import json
import os
from pathlib import Path

from . import auth, classify, config, export
from . import importer as import_module
from .spotify import Spotify, SpotifyError, ensure_liked, parse_track_id

OUT = Path(os.environ.get("SPOTIFY_SORT_OUT", config.STATE_DIR / "out"))
LIKED = OUT / "liked.json"
PLAYLISTS = OUT / "playlists.json"
REFERENCES = OUT / "references.json"

# Actions déclenchables en arrière-plan : clé -> libellé affiché.
JOB_ACTIONS = {
    "fetch": "Récupération des likés",
    "reference": "Playlists de référence",
    "sort": "Classement",
    "import": "Import vers Spotify",
    "sync-likes": "Rattrapage des likes",
    "doctor": "Diagnostic",
}

# Seul `doctor` a un sens sans compte Spotify connecté : il sert justement à
# diagnostiquer pourquoi la connexion ne va pas.
NEEDS_SPOTIFY = set(JOB_ACTIONS) - {"doctor"}


def load(path: Path):
    return json.loads(path.read_text()) if path.exists() else None


def error_text(exc: BaseException) -> str:
    """Message lisible pour une exception quelconque.

    `str(exc)` seul est souvent vide (ConnectionError, KeyError…) : sans le nom
    de la classe, l'utilisateur n'a rien pour diagnostiquer.
    """
    message = str(exc).strip()
    if isinstance(exc, SpotifyError):
        return message
    return f"{exc.__class__.__name__} : {message}" if message else exc.__class__.__name__


def anthropic_ready() -> bool:
    return bool(
        os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")
    )


def status() -> dict:
    """Instantané de l'état, sans appel réseau."""
    document = load(PLAYLISTS)
    return {
        "liked_count": len(load(LIKED) or []),
        "spotify_ready": auth.has_token(),
        "anthropic_ready": anthropic_ready(),
        "has_result": document is not None,
        "playlist_count": len(document["playlists"]) if document else 0,
        "references": {k: len(v) for k, v in (load(REFERENCES) or {}).items()},
    }


# --- Tâches longues ---------------------------------------------------------


def task_fetch():
    spotify = Spotify()
    print("Récupération des titres likés…")
    tracks = spotify.liked_tracks()
    OUT.mkdir(parents=True, exist_ok=True)
    LIKED.write_text(json.dumps(tracks, ensure_ascii=False, indent=2))
    print(f"{len(tracks)} titres récupérés.")
    print("Récupération des genres des artistes…")
    if spotify.attach_artist_genres(tracks):
        LIKED.write_text(json.dumps(tracks, ensure_ascii=False, indent=2))
        print("Genres ajoutés.")
    return len(tracks)


def task_reference():
    spotify = Spotify()
    references: dict[str, list[dict]] = {}
    for name, key in config.REFERENCE_PLAYLISTS.items():
        playlist = spotify.find_playlist(name)
        if not playlist:
            print(f"  ✗ « {name} » introuvable sur le compte — ignorée.")
            continue
        items = spotify.playlist_items(playlist["id"])
        references.setdefault(key, []).extend(items)
        print(f"  ✓ « {name} » → `{key}` : {len(items)} titres")
    OUT.mkdir(parents=True, exist_ok=True)
    REFERENCES.write_text(json.dumps(references, ensure_ascii=False, indent=2))
    return {k: len(v) for k, v in references.items()}


def task_sort(limit: int | None = None):
    if not LIKED.exists():
        task_fetch()
    tracks = load(LIKED) or []
    if limit:
        tracks = tracks[:limit]
        print(f"Limité à {len(tracks)} titres.")

    if config.REFERENCE_PLAYLISTS and not REFERENCES.exists():
        print("Récupération des playlists de référence…")
        task_reference()

    assignments = classify.classify(tracks, load(REFERENCES) or {})
    document = export.build_document(tracks, assignments)
    export.write(document, OUT)
    print("\n" + export.summary(document))
    return {"playlists": len(document["playlists"]), "tracks": document["track_count"]}


def task_import(only: list[str] | None = None, public: bool | None = None):
    import_module.run(PLAYLISTS, only=only, public=public)
    return True


def task_sync_likes():
    """Like tout titre présent dans une playlist mais absent des Titres likés."""
    spotify = Spotify()
    print("Lecture des Titres likés…")
    saved = spotify.saved_track_ids()
    print(f"{len(saved)} déjà likés.")

    playlists = spotify.existing_playlists()
    print(f"Analyse de {len(playlists)} playlists…")

    missing = []
    for name, playlist_id in playlists.items():
        absent = [t["id"] for t in spotify.playlist_items(playlist_id) if t["id"] not in saved]
        if absent:
            missing.extend(absent)
            print(f"  {name} : {len(absent)} hors des likés")

    every = list(dict.fromkeys(missing))
    if not every:
        print("\nRien à faire — toutes les playlists sont couvertes par les likés.")
        return 0

    added = spotify.save_tracks(every)
    print(f"\n{added} titres ajoutés aux Titres likés.")
    return added


def task_doctor():
    spotify = Spotify()
    print("Scopes accordés :")
    granted = auth.granted_scopes()
    for scope in config.SCOPES:
        print(f"  {'✓' if scope in granted else '✗'} {scope}")

    print("\nAccès API :")
    checks = [
        ("profil", lambda: spotify.me()["id"]),
        ("titres likés", lambda: f"{spotify._request('GET', '/me/tracks', params={'limit': 1})['total']} titres"),
        ("playlists", lambda: f"{spotify._request('GET', '/me/playlists', params={'limit': 1})['total']} playlists"),
        ("catalogue", lambda: spotify._request("GET", "/artists/0TnOYISbd1XYRBk9myaseg")["name"]),
    ]
    for label, fn in checks:
        try:
            print(f"  ✓ {label} — {fn()}")
        except Exception as exc:
            print(f"  ✗ {label} — {exc}")

    print("\nÉcriture :")
    try:
        pid = spotify.create_playlist("spotify-sort — test", "Test, supprimé aussitôt.", False)
        print("  ✓ création (POST /me/playlists)")
        spotify.unfollow_playlist(pid)
        print("  ✓ suppression de la playlist de test")
    except Exception as exc:
        # Pas seulement SpotifyError : une coupure réseau ne doit pas faire
        # échouer le diagnostic, dont le rôle est justement de la rapporter.
        print(f"  ✗ {error_text(exc)}")
    return True


def job_for(action: str, params: dict | None = None):
    """Callable et libellé du job correspondant à une action.

    Centralise la traduction action -> fonction pour que les deux façades ne
    puissent pas diverger sur les noms ou les arguments.
    """
    params = params or {}
    if action not in JOB_ACTIONS:
        raise ValueError(f"Action inconnue : {action}")
    if action == "sort":
        return JOB_ACTIONS[action], task_sort, (params.get("limit"),)
    if action == "import":
        return JOB_ACTIONS[action], task_import, (params.get("only"), params.get("public"))
    return JOB_ACTIONS[action], globals()[f"task_{action.replace('-', '_')}"], ()


# --- Actions immédiates -----------------------------------------------------


def classify_one(link: str, add: bool) -> dict:
    """Classe un titre unique. Retourne {track, rows}.

    Avec `add`, le titre est ajouté aux playlists existantes ET aux Titres
    likés — une chanson rangée quelque part doit être dans la bibliothèque.
    """
    # Lien analysé avant d'ouvrir la session : un lien fautif ne doit pas coûter
    # un rafraîchissement de token ni voir son erreur masquée par l'auth.
    track_id = parse_track_id(link)
    spotify = Spotify()
    track = spotify.track(track_id)
    spotify.attach_artist_genres([track])
    assignments = classify.classify([track], load(REFERENCES) or {})

    existing = spotify.existing_playlists() if add else {}
    rows = []

    if add:
        try:
            liked = ensure_liked(spotify, [track["id"]])
            rows.append(
                {"name": "Titres likés", "status": "ajouté" if liked else "déjà présent"}
            )
        except SpotifyError as exc:
            rows.append(
                {"name": "Titres likés", "status": f"échec — {exc.detail or exc.status}"}
            )

    for key in assignments[track["id"]]:
        name = config.display_name(key)
        status_text = "proposé"
        if add:
            playlist_id = existing.get(name)
            if not playlist_id:
                status_text = "playlist absente du compte"
            elif track["id"] in spotify.playlist_track_ids(playlist_id):
                status_text = "déjà présent"
            else:
                spotify.add_tracks(playlist_id, [track["uri"]])
                status_text = "ajouté"
        rows.append({"name": name, "status": status_text})

    return {"track": track, "rows": rows}


def remove_from_result(key: str, track_id: str) -> dict:
    """Retire un titre d'une playlist du document de résultat. Retourne le document."""
    document = load(PLAYLISTS)
    if not document:
        raise FileNotFoundError("Aucun classement enregistré.")
    for playlist in document["playlists"]:
        if playlist["key"] == key:
            playlist["track_ids"] = [t for t in playlist["track_ids"] if t != track_id]
    document["playlists"] = [p for p in document["playlists"] if p["track_ids"]]
    PLAYLISTS.write_text(json.dumps(document, ensure_ascii=False, indent=2))
    return document


# --- Réglages ---------------------------------------------------------------


def update_settings(data: dict) -> dict:
    """Enregistre les réglages fournis, en conservant ce qui n'est pas transmis."""
    current = config.current_settings()
    for field in ("tolerance", "playlist_prefix", "playlist_public",
                  "reference_playlists", "categories"):
        if field in data:
            current[field] = data[field]
    config.save_settings(current)
    return config.current_settings()
