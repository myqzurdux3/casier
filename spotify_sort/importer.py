"""Import du classement vers Spotify : création des playlists et ajout des titres."""

import json
from pathlib import Path

from . import config
from .export import plural
from .spotify import Spotify, SpotifyError, ensure_liked


def load(path: Path) -> dict:
    document = json.loads(path.read_text())
    if document.get("version") != 1:
        raise ValueError(f"Format de fichier inattendu : {path}")
    return document


def run(
    path: Path,
    only: list[str] | None = None,
    public: bool | None = None,
    dry_run: bool = False,
) -> None:
    document = load(path)
    playlists = document["playlists"]
    if only:
        wanted = set(only)
        playlists = [p for p in playlists if p["key"] in wanted]
        missing = wanted - {p["key"] for p in playlists}
        if missing:
            raise ValueError(f"Playlists inconnues dans le fichier : {sorted(missing)}")
    if not playlists:
        print("Rien à importer.")
        return

    is_public = config.PLAYLIST_PUBLIC if public is None else public
    tracks = document["tracks"]

    if dry_run:
        print("Simulation — aucune playlist ne sera créée :\n")
        for playlist in playlists:
            print(f"  {playlist['name']} — {plural(len(playlist['track_ids']))}")
        return

    spotify = Spotify()
    existing = spotify.existing_playlists()

    # Tout titre qu'on range dans une playlist doit aussi figurer dans les likés.
    to_like = [tid for p in playlists for tid in p["track_ids"] if tid in tracks]
    liked = ensure_liked(spotify, to_like)
    if liked:
        print(f"{plural(liked)} ajouté(s) aux Titres likés.\n")

    created, skipped, failed = 0, 0, []
    consecutive_failures = 0

    for playlist in playlists:
        name = playlist["name"]
        uris = [
            tracks[tid]["uri"] for tid in playlist["track_ids"] if tid in tracks
        ]
        if not uris:
            continue

        if name in existing:
            print(f"  « {name} » existe déjà — ignorée (renomme-la pour recréer).")
            skipped += 1
            continue

        try:
            playlist_id = spotify.create_playlist(name, playlist["description"], is_public)
            spotify.add_tracks(playlist_id, uris)
        except SpotifyError as exc:
            # Une playlist qui échoue ne doit pas condamner les suivantes…
            print(f"  « {name} » échouée — {exc}")
            failed.append(name)
            consecutive_failures += 1
            if consecutive_failures >= 3:
                print("\n  Trois échecs d'affilée — problème global, arrêt.")
                print("  Lance `python main.py doctor` pour localiser le blocage.")
                break
            continue

        consecutive_failures = 0
        created += 1
        print(f"  « {name} » créée — {plural(len(uris))}.")

    print(f"\nImport terminé : {created} créées, {skipped} déjà présentes, {len(failed)} en échec.")
    if failed:
        print("Playlists en échec : " + ", ".join(failed))
        print("Rien n'est perdu — corrige le problème et relance la même commande.")
