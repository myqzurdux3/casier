"""Export du classement en JSON (format d'import) et CSV (lecture humaine)."""

import csv
import json
from pathlib import Path

from . import config


def build_document(tracks: list[dict], assignments: dict[str, list[str]]) -> dict:
    """Document canonique : la source de vérité pour l'import."""
    by_id = {t["id"]: t for t in tracks}
    playlists: dict[str, list[str]] = {}
    for track_id, keys in assignments.items():
        for key in keys:
            playlists.setdefault(key, []).append(track_id)

    def sort_key(track_id: str) -> tuple:
        track = by_id.get(track_id, {})
        return (track.get("release_date", ""), track.get("title", ""))

    return {
        "version": 1,
        "track_count": len(tracks),
        "tracks": {
            t["id"]: {
                "uri": t["uri"],
                "title": t["title"],
                "artists": t["artists"],
                "album": t["album"],
                "release_date": t["release_date"],
                "popularity": t["popularity"],
                "added_at": t["added_at"],
                "genres": t["genres"],
            }
            for t in tracks
        },
        "playlists": [
            {
                "key": key,
                "name": config.display_name(key),
                "description": config.LLM_CATEGORIES.get(
                    key, f"Titres likés — {config.display_name(key)}"
                ),
                "track_ids": sorted(set(track_ids), key=sort_key),
            }
            for key, track_ids in sorted(
                playlists.items(), key=lambda kv: (-len(kv[1]), kv[0])
            )
        ],
    }


def write(document: dict, outdir: Path) -> tuple[Path, Path]:
    outdir.mkdir(parents=True, exist_ok=True)

    json_path = outdir / "playlists.json"
    json_path.write_text(json.dumps(document, ensure_ascii=False, indent=2))

    csv_path = outdir / "tracks.csv"
    by_track: dict[str, list[str]] = {}
    for playlist in document["playlists"]:
        for track_id in playlist["track_ids"]:
            by_track.setdefault(track_id, []).append(playlist["name"])

    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            ["titre", "artistes", "album", "sortie", "popularité", "playlists"]
        )
        for track_id, track in document["tracks"].items():
            writer.writerow(
                [
                    track["title"],
                    ", ".join(track["artists"]),
                    track["album"],
                    track["release_date"],
                    track["popularity"],
                    " | ".join(by_track.get(track_id, [])),
                ]
            )

    return json_path, csv_path


def plural(count: int) -> str:
    return f"{count} titre" + ("s" if count > 1 else "")


def summary(document: dict) -> str:
    lines = [f"{plural(document['track_count'])} → {len(document['playlists'])} playlists\n"]
    width = max((len(p["name"]) for p in document["playlists"]), default=0)
    for playlist in document["playlists"]:
        count = len(playlist["track_ids"])
        lines.append(f"  {playlist['name']:<{width}}  {count:>4} titre" + ("s" if count > 1 else ""))
    return "\n".join(lines)
