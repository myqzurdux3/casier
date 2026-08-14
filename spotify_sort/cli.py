"""Interface en ligne de commande."""

import argparse
import json
import sys
from pathlib import Path

from . import auth, classify, config, export
from . import importer as import_module
from .export import plural
from .spotify import Spotify, SpotifyError, ensure_liked, parse_track_id

DEFAULT_OUT = config.STATE_DIR / "out"


def cmd_doctor(_args) -> None:
    """Teste chaque droit d'accès un par un pour localiser un 403."""
    # Instancier le client d'abord : c'est lui qui déclenche l'autorisation.
    # Lire les scopes avant afficherait l'état du token périmé.
    spotify = Spotify()

    print("=== Token ===")
    granted = auth.granted_scopes()
    for scope in config.SCOPES:
        print(f"  {'✓' if scope in granted else '✗'} {scope}")
    extra = granted - set(config.SCOPES)
    if extra:
        print(f"  (scopes supplémentaires : {', '.join(sorted(extra))})")

    print("\n=== Accès API ===")

    def probe(label: str, fn):
        try:
            print(f"  ✓ {label} — {fn()}")
            return True
        except SpotifyError as exc:
            print(f"  ✗ {label} — {exc}")
        except Exception as exc:
            print(f"  ✗ {label} — {exc}")
        return False

    user, sample = {}, {}

    def read_profile():
        user.update(spotify.me())
        return user["id"]

    def read_library():
        page = spotify._request("GET", "/me/tracks", params={"limit": 1})
        items = page.get("items") or []
        if items:
            sample["uri"] = (items[0].get("track") or {}).get("uri")
        return f"{page['total']} titres"

    probe("profil (GET /me)", read_profile)
    probe("titres likés (GET /me/tracks)", read_library)
    probe(
        "playlists (GET /me/playlists)",
        lambda: f"{spotify._request('GET', '/me/playlists', params={'limit': 1})['total']} playlists",
    )
    probe(
        "catalogue (GET /artists/{id})",
        lambda: spotify._request("GET", "/artists/0TnOYISbd1XYRBk9myaseg")["name"],
    )

    # --- écriture : plusieurs variantes pour isoler ce qui est refusé ---------
    user_id = user.get("id")
    if not user_id:
        print("\nProfil illisible — impossible de tester l'écriture.")
        return

    print("\n=== Écriture (endpoints migrés mars 2026) ===")

    # 1. Création — POST /me/playlists (remplace /users/{id}/playlists)
    try:
        playlist_id = spotify.create_playlist(
            "spotify-sort — test", "Test temporaire, supprimé aussitôt.", False
        )
        print("  ✓ création (POST /me/playlists)")
    except SpotifyError as exc:
        print(f"  ✗ création (POST /me/playlists) — {exc.status} {exc.detail or '(sans message)'}")
        print(f"\n  corps    : {exc.body or '(vide)'}")
        print(f"  en-têtes : {exc.headers or '(aucun pertinent)'}")
        print(
            "\n  Si l'ancien endpoint /users/{id}/playlists était encore utilisé,\n"
            "  ce 403 serait attendu — ce n'est plus le cas ici. Vérifie alors :\n"
            "  1. Dashboard Spotify → ton app → User Management : ton compte y est-il ?\n"
            "  2. Peux-tu créer une playlist à la main sur open.spotify.com ?\n"
            "  3. Reproduis hors de l'outil :\n\n"
            f"     curl -i -X POST 'https://api.spotify.com/v1/me/playlists' \\\n"
            f"       -H 'Authorization: Bearer {spotify._token}' \\\n"
            f"       -H 'Content-Type: application/json' \\\n"
            f"       -d '{{\"name\":\"test curl\"}}'\n"
        )
        return

    # 2. Ajout de titres — POST /playlists/{id}/items (remplace /tracks)
    if sample.get("uri"):
        try:
            spotify.add_tracks(playlist_id, [sample["uri"]])
            print("  ✓ ajout de titres (POST /playlists/{id}/items)")
        except SpotifyError as exc:
            print(f"  ✗ ajout de titres — {exc.status} {exc.detail or '(sans message)'}")
            print(f"    corps : {exc.body or '(vide)'}")
    else:
        print("  — ajout de titres non testé (aucun titre liké lisible)")

    # 2b. Bibliothèque — PUT /me/library remplace PUT /me/tracks
    if sample.get("uri"):
        try:
            spotify._request("PUT", "/me/library", params={"uris": sample["uri"]})
            print("  ✓ ajout aux Titres likés (PUT /me/library)")
        except SpotifyError as exc:
            print(
                f"  ✗ ajout aux Titres likés — {exc.status} "
                f"{exc.detail or '(sans message)'}"
            )

    # 3. Nettoyage
    try:
        spotify.unfollow_playlist(playlist_id)
        print("  ✓ suppression de la playlist de test")
    except SpotifyError as exc:
        print(f"  ✗ suppression — {exc}")
        print(f"    Supprime « spotify-sort — test » à la main dans Spotify.")

    print("\n  L'écriture fonctionne. Relance : python main.py import out/playlists.json")


def cmd_fetch(args) -> None:
    spotify = Spotify()
    args.out.mkdir(parents=True, exist_ok=True)
    path = args.out / "liked.json"

    def save(tracks: list[dict]) -> None:
        path.write_text(json.dumps(tracks, ensure_ascii=False, indent=2))

    print("Récupération des titres likés…")
    tracks = spotify.liked_tracks()
    save(tracks)  # sauvegardé avant l'enrichissement : rien n'est perdu en cas d'échec
    print(f"{len(tracks)} titres récupérés → {path}")

    print("Récupération des genres des artistes…")
    if spotify.attach_artist_genres(tracks):
        save(tracks)
        print("Genres ajoutés.")


def cmd_reference(args) -> None:
    """Lit les playlists de référence du compte et les met en cache."""
    if not config.REFERENCE_PLAYLISTS:
        print("Aucune playlist de référence configurée (config.REFERENCE_PLAYLISTS).")
        return

    spotify = Spotify()
    references: dict[str, list[dict]] = {}

    for name, key in config.REFERENCE_PLAYLISTS.items():
        playlist = spotify.find_playlist(name)
        if not playlist:
            print(f"  ✗ « {name} » introuvable sur ton compte — ignorée.")
            print("    Vérifie le nom exact, ou que tu en es bien le propriétaire.")
            continue
        items = spotify.playlist_items(playlist["id"])
        references.setdefault(key, []).extend(items)
        print(f"  ✓ « {name} » → `{key}` : {len(items)} titres")

    args.out.mkdir(parents=True, exist_ok=True)
    path = args.out / "references.json"
    path.write_text(json.dumps(references, ensure_ascii=False, indent=2))
    print(f"Écrit dans {path}")


def _load_references(args) -> dict[str, list[dict]]:
    path = args.out / "references.json"
    if not path.exists() and config.REFERENCE_PLAYLISTS:
        print("Récupération des playlists de référence…")
        cmd_reference(args)
    return json.loads(path.read_text()) if path.exists() else {}


def cmd_sort(args) -> None:
    cache = args.out / "liked.json"
    if cache.exists() and not args.refresh:
        tracks = json.loads(cache.read_text())
        print(f"{len(tracks)} titres chargés depuis {cache} (--refresh pour recharger).")
    else:
        cmd_fetch(args)
        tracks = json.loads(cache.read_text())

    if args.limit:
        tracks = tracks[: args.limit]
        print(f"Limité à {len(tracks)} titres (--limit).")

    assignments = classify.classify(tracks, _load_references(args))
    document = export.build_document(tracks, assignments)
    json_path, csv_path = export.write(document, args.out)

    print("\n" + export.summary(document))
    print(f"\nExporté :\n  {json_path}\n  {csv_path}")
    print(f"\nPour créer ces playlists sur ton compte :\n  python main.py import {json_path}")


def cmd_track(args) -> None:
    """Classe un ou plusieurs titres donnés par lien, et les ajoute si demandé."""
    track_ids = [parse_track_id(value) for value in args.links]

    spotify = Spotify()
    tracks = [spotify.track(tid) for tid in track_ids]
    spotify.attach_artist_genres(tracks)

    assignments = classify.classify(tracks, _load_references(args))

    existing = spotify.existing_playlists() if args.add else {}
    absent: set[str] = set()

    if args.add:
        # Un titre qu'on range dans une playlist doit aussi être dans les likés.
        liked = ensure_liked(spotify, [t["id"] for t in tracks])
        if liked:
            print(f"\n{plural(liked)} ajouté(s) aux Titres likés.")

    for track in tracks:
        keys = assignments[track["id"]]
        print(f"\n« {track['title']} » — {', '.join(track['artists'])}")

        for key in keys:
            name = config.display_name(key)
            if not args.add:
                print(f"  → {name}")
                continue

            playlist_id = existing.get(name)
            if not playlist_id:
                print(f"  → {name} (playlist absente du compte — non ajouté)")
                absent.add(name)
                continue
            if track["id"] in spotify.playlist_track_ids(playlist_id):
                print(f"  → {name} (déjà présent)")
                continue
            spotify.add_tracks(playlist_id, [track["uri"]])
            print(f"  ✓ {name} — ajouté")

    if not args.add:
        print("\nAjoute --add pour les insérer dans ces playlists.")
    elif absent:
        print(
            "\nPlaylists absentes du compte : " + ", ".join(sorted(absent)) + "\n"
            "Crée-les via `import`, ou à la main avec ce nom exact."
        )


def cmd_sync_likes(args) -> None:
    """Like tout titre présent dans une de tes playlists mais absent des likés."""
    spotify = Spotify()
    print("Lecture des Titres likés…")
    saved = spotify.saved_track_ids()
    print(f"{plural(len(saved))} déjà liké(s).")

    playlists = spotify.existing_playlists()
    print(f"Analyse de {len(playlists)} playlists t'appartenant…")

    missing: dict[str, list[str]] = {}
    for name, playlist_id in playlists.items():
        absent = [t["id"] for t in spotify.playlist_items(playlist_id) if t["id"] not in saved]
        if absent:
            missing[name] = absent
            print(f"  {name} : {plural(len(absent))} hors des likés")

    every = list(dict.fromkeys(tid for ids in missing.values() for tid in ids))
    if not every:
        print("\nRien à faire — toutes tes playlists sont couvertes par les likés.")
        return

    print(f"\n{plural(len(every))} à ajouter aux Titres likés.")
    if args.dry_run:
        print("Simulation — rien n'a été ajouté. Relance sans --dry-run.")
        return

    added = spotify.save_tracks(every)
    print(f"{plural(added)} ajouté(s) aux Titres likés.")


def cmd_import(args) -> None:
    import_module.run(
        args.file,
        only=args.only,
        public=True if args.public else None,
        dry_run=args.dry_run,
    )


def main(argv=None) -> int:
    # --out est accepté avant comme après la sous-commande.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--out", type=Path, default=DEFAULT_OUT, help="Dossier de sortie (défaut: out/)"
    )

    parser = argparse.ArgumentParser(
        prog="spotify-sort",
        parents=[common],
        description="Trie tes titres likés Spotify en playlists thématiques.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_doctor = sub.add_parser(
        "doctor", parents=[common], help="Diagnostiquer les droits d'accès Spotify"
    )
    p_doctor.set_defaults(func=cmd_doctor)

    p_fetch = sub.add_parser(
        "fetch", parents=[common], help="Récupérer les titres likés depuis Spotify"
    )
    p_fetch.set_defaults(func=cmd_fetch)

    p_reference = sub.add_parser(
        "reference", parents=[common], help="Relire les playlists de référence"
    )
    p_reference.set_defaults(func=cmd_reference)

    p_sort = sub.add_parser(
        "sort", parents=[common], help="Classer les titres et exporter JSON + CSV"
    )
    p_sort.add_argument("--refresh", action="store_true", help="Recharger depuis Spotify")
    p_sort.add_argument("--limit", type=int, help="Ne traiter que les N premiers titres")
    p_sort.set_defaults(func=cmd_sort)

    p_track = sub.add_parser(
        "track", parents=[common], help="Classer un titre depuis son lien Spotify"
    )
    p_track.add_argument("links", nargs="+", metavar="LIEN", help="Lien, URI ou ID Spotify")
    p_track.add_argument(
        "--add", action="store_true", help="Ajouter réellement aux playlists existantes"
    )
    p_track.set_defaults(func=cmd_track)

    p_sync = sub.add_parser(
        "sync-likes",
        parents=[common],
        help="Liker les titres présents dans tes playlists mais absents des likés",
    )
    p_sync.add_argument("--dry-run", action="store_true", help="Lister sans rien ajouter")
    p_sync.set_defaults(func=cmd_sync_likes)

    p_import = sub.add_parser(
        "import", parents=[common], help="Créer les playlists sur ton compte Spotify"
    )
    p_import.add_argument("file", type=Path, help="Chemin vers playlists.json")
    p_import.add_argument("--only", nargs="+", metavar="CLÉ", help="N'importer que ces playlists")
    p_import.add_argument("--public", action="store_true", help="Créer des playlists publiques")
    p_import.add_argument("--dry-run", action="store_true", help="Afficher sans rien créer")
    p_import.set_defaults(func=cmd_import)

    args = parser.parse_args(argv)
    try:
        args.func(args)
    except KeyboardInterrupt:
        print("\nInterrompu.")
        return 130
    except Exception as exc:
        print(f"\nErreur : {exc}", file=sys.stderr)
        return 1
    return 0
