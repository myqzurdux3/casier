"""Client HTTP minimal pour l'API Web Spotify."""

import re
import time

import requests

from .auth import get_access_token

API = "https://api.spotify.com/v1"

# spotify:track:ID · https://open.spotify.com/track/ID?si=… · .../intl-fr/track/ID
_TRACK_ID = re.compile(r"track[/:]([A-Za-z0-9]{22})")
_BARE_ID = re.compile(r"^[A-Za-z0-9]{22}$")


def parse_track_id(value: str) -> str:
    """Extrait l'identifiant d'un lien, d'une URI ou d'un ID brut."""
    value = value.strip()
    match = _TRACK_ID.search(value)
    if match:
        return match.group(1)
    if _BARE_ID.match(value):
        return value
    raise ValueError(
        f"Lien Spotify non reconnu : {value}\n"
        "Attendu : https://open.spotify.com/track/…, spotify:track:… ou un ID."
    )


def normalize_track(track: dict, added_at: str = "") -> dict:
    """Met un objet track de l'API au format utilisé dans tout l'outil."""
    return {
        "id": track["id"],
        "uri": track["uri"],
        "title": track.get("name", ""),
        "artists": [a["name"] for a in track.get("artists", [])],
        "artist_ids": [a["id"] for a in track.get("artists", []) if a.get("id")],
        "album": (track.get("album") or {}).get("name", ""),
        "release_date": (track.get("album") or {}).get("release_date", ""),
        "popularity": track.get("popularity", 0),
        "added_at": added_at,
        "genres": [],
    }


def ensure_liked(spotify, track_ids, saved: set[str] | None = None) -> int:
    """Ajoute aux Titres likés ceux qui n'y sont pas encore.

    `saved` évite de re-télécharger la bibliothèque quand l'appelant l'a déjà.
    Il est mis à jour au passage.
    """
    wanted = [t for t in dict.fromkeys(track_ids) if t]
    if not wanted:
        return 0

    if saved is None:
        # Test ciblé d'abord : lire toute la bibliothèque pour un seul titre
        # coûterait une dizaine de requêtes.
        contains = spotify.saved_contains(wanted)
        if contains is None:
            saved = spotify.saved_track_ids()
        else:
            saved = {tid for tid, present in contains.items() if present}

    missing = [t for t in wanted if t not in saved]
    if not missing:
        return 0
    added = spotify.save_tracks(missing)
    saved.update(missing)
    return added


class SpotifyError(RuntimeError):
    """Erreur API Spotify, avec le message renvoyé par Spotify."""

    def __init__(self, response, url: str):
        self.status = response.status_code
        self.url = url
        self.body = (response.text or "")[:500]
        self.headers = {
            k: v
            for k, v in dict(response.headers).items()
            if k.lower()
            in {"retry-after", "www-authenticate", "x-robots-tag", "content-type"}
        }
        try:
            self.detail = (response.json().get("error") or {}).get("message", "")
        except ValueError:
            self.detail = self.body[:200]
        super().__init__(f"{self.status} sur {url}" + (f" — {self.detail}" if self.detail else ""))


class Spotify:
    def __init__(self):
        self.session = requests.Session()
        self._token = get_access_token()

    # --- bas niveau ----------------------------------------------------------

    def _request(self, method: str, path: str, **kwargs) -> dict:
        url = path if path.startswith("http") else f"{API}{path}"
        for attempt in range(6):
            headers = {"Authorization": f"Bearer {self._token}"}
            headers.update(kwargs.pop("headers", {}))
            response = self.session.request(
                method, url, headers=headers, timeout=30, **kwargs
            )

            if response.status_code == 429:
                wait = int(response.headers.get("Retry-After", "2")) + 1
                print(f"  rate limit, pause de {wait}s…")
                time.sleep(wait)
                continue
            if response.status_code == 401 and attempt == 0:
                self._token = get_access_token()
                continue
            if response.status_code >= 500:
                time.sleep(2**attempt)
                continue

            if response.status_code >= 400:
                raise SpotifyError(response, url)
            return response.json() if response.content else {}

        raise RuntimeError(f"Spotify injoignable après plusieurs tentatives : {url}")

    def _paginate(self, path: str, **params):
        page = self._request("GET", path, params=params)
        while page:
            yield from page.get("items", [])
            nxt = page.get("next")
            page = self._request("GET", nxt) if nxt else None

    # --- lecture -------------------------------------------------------------

    def me(self) -> dict:
        return self._request("GET", "/me")

    def liked_tracks(self) -> list[dict]:
        """Tous les titres de la playlist « Titres likés », normalisés."""
        tracks, seen = [], set()
        for item in self._paginate("/me/tracks", limit=50):
            track = item.get("track") or {}
            track_id = track.get("id")
            if not track_id or track_id in seen:
                continue  # titres locaux ou doublons
            seen.add(track_id)
            tracks.append(normalize_track(track, item.get("added_at", "")))
            if len(tracks) % 200 == 0:
                print(f"  {len(tracks)} titres récupérés…")
        return tracks

    def attach_artist_genres(self, tracks: list[dict]) -> bool:
        """Complète chaque titre avec les genres Spotify de ses artistes.

        Les genres ne sont qu'un indice pour la classification : si l'endpoint
        est indisponible, on continue sans plutôt que de faire échouer le run.
        Retourne True si au moins un genre a été récupéré.
        """
        artist_ids = sorted({aid for t in tracks for aid in t["artist_ids"]})
        genres_by_artist: dict[str, list[str]] = {}

        def store(payload: dict) -> None:
            for artist in payload.get("artists", []) or []:
                if artist and artist.get("id"):
                    genres_by_artist[artist["id"]] = artist.get("genres", [])

        # `GET /artists?ids=` a été supprimé par la migration de mars 2026, comme
        # tous les endpoints groupés par `ids` : une requête par artiste.
        for i in range(0, len(artist_ids), 50):
            chunk = artist_ids[i : i + 50]

            # Un ID invalide ou restreint ne doit pas condamner toute la tranche.
            failures = 0
            for artist_id in chunk:
                try:
                    store({"artists": [self._request("GET", f"/artists/{artist_id}")]})
                except SpotifyError as exc:
                    failures += 1
                    if failures == 1 and i == 0:
                        print(f"  genres indisponibles : {exc}")
                    if failures >= 5 and not genres_by_artist:
                        print(
                            "  Genres abandonnés — la classification se fera sur\n"
                            "  titre / artiste / album / année uniquement."
                        )
                        return False

        for track in tracks:
            genres = []
            for aid in track["artist_ids"]:
                for genre in genres_by_artist.get(aid, []):
                    if genre not in genres:
                        genres.append(genre)
            track["genres"] = genres

        return bool(genres_by_artist)

    def track(self, track_id: str) -> dict:
        return normalize_track(self._request("GET", f"/tracks/{track_id}"))

    def playlist_track_ids(self, playlist_id: str) -> set[str]:
        return {t["id"] for t in self.playlist_items(playlist_id)}

    def find_playlist(self, name: str) -> dict | None:
        """Cherche une playlist par nom, insensible à la casse et aux espaces."""
        target = name.strip().casefold()
        for playlist in self._paginate("/me/playlists", limit=50):
            if playlist and playlist.get("name", "").strip().casefold() == target:
                return playlist
        return None

    def playlist_items(self, playlist_id: str) -> list[dict]:
        """Titres d'une playlist.

        La migration de mars 2026 renomme `/tracks` en `/items` et le champ
        `track` en `item` : on lit les deux pour rester compatible.
        """
        tracks = []
        for entry in self._paginate(f"/playlists/{playlist_id}/items", limit=100):
            track = entry.get("item") or entry.get("track") or {}
            if not track.get("id"):
                continue  # titres locaux ou indisponibles
            tracks.append(
                {
                    "id": track["id"],
                    "title": track.get("name", ""),
                    "artists": [a["name"] for a in track.get("artists", [])],
                    "release_date": (track.get("album") or {}).get("release_date", ""),
                }
            )
        return tracks

    def existing_playlists(self) -> dict[str, str]:
        """Playlists possédées par l'utilisateur : nom -> id."""
        user_id = self.me()["id"]
        return {
            p["name"]: p["id"]
            for p in self._paginate("/me/playlists", limit=50)
            if p and (p.get("owner") or {}).get("id") == user_id
        }

    # --- écriture ------------------------------------------------------------

    def create_playlist(self, name: str, description: str, public: bool) -> str:
        # POST /users/{id}/playlists a été supprimé par la migration Web API du
        # 9 mars 2026 (403 pour tous les appelants) : /me/playlists le remplace.
        data = self._request(
            "POST",
            "/me/playlists",
            json={
                "name": name,
                "description": description[:300],
                "public": public,
            },
        )
        return data["id"]

    def saved_track_ids(self) -> set[str]:
        """Identifiants des Titres likés.

        Déduits de /me/tracks plutôt que de /me/tracks/contains : ce dernier est
        un endpoint groupé par `ids`, la même forme que /artists?ids= qui est
        refusée sur les apps en Development Mode.
        """
        return {t["id"] for t in self.liked_tracks()}

    def saved_contains(self, track_ids: list[str]) -> dict[str, bool] | None:
        """Teste l'appartenance aux Titres likés sans lire toute la bibliothèque.

        `GET /me/library/contains` remplace `/me/tracks/contains`. Retourne None
        si l'endpoint est indisponible ou répond dans un format inattendu :
        l'appelant retombe alors sur la lecture complète.
        """
        found: dict[str, bool] = {}
        for i in range(0, len(track_ids), 40):
            chunk = track_ids[i : i + 40]
            uris = ",".join(f"spotify:track:{tid}" for tid in chunk)
            try:
                data = self._request("GET", "/me/library/contains", params={"uris": uris})
            except SpotifyError:
                return None

            flags = data if isinstance(data, list) else (data or {}).get("contains")
            if not isinstance(flags, list) or len(flags) != len(chunk):
                return None
            found.update(zip(chunk, (bool(f) for f in flags)))
        return found

    def save_tracks(self, track_ids: list[str]) -> int:
        """Ajoute aux Titres likés. Retourne le nombre effectivement ajouté.

        `PUT /me/tracks` a été supprimé par la migration de mars 2026 :
        `PUT /me/library` le remplace, avec des URI complets passés en paramètre
        de requête plutôt que des identifiants nus, et 40 par appel au maximum.
        """
        added = 0
        for i in range(0, len(track_ids), 40):
            chunk = track_ids[i : i + 40]
            uris = ",".join(f"spotify:track:{tid}" for tid in chunk)
            try:
                self._request("PUT", "/me/library", params={"uris": uris})
                added += len(chunk)
                continue
            except SpotifyError as exc:
                print(f"  lot refusé ({exc.status}) — repli un par un.")

            for track_id in chunk:
                try:
                    self._request(
                        "PUT", "/me/library", params={"uris": f"spotify:track:{track_id}"}
                    )
                    added += 1
                except SpotifyError as exc:
                    print(f"  like impossible pour {track_id} — {exc}")
        return added

    def unfollow_playlist(self, playlist_id: str) -> None:
        """Retire la playlist de la bibliothèque — l'équivalent Spotify d'une suppression."""
        self._request("DELETE", f"/playlists/{playlist_id}/followers")

    def add_tracks(self, playlist_id: str, uris: list[str]) -> None:
        # Idem : /playlists/{id}/tracks a été renommé en /playlists/{id}/items.
        for i in range(0, len(uris), 100):
            chunk = uris[i : i + 100]
            try:
                self._request(
                    "POST", f"/playlists/{playlist_id}/items", json={"uris": chunk}
                )
            except SpotifyError as exc:
                if exc.status != 400:
                    raise
                # La migration renomme aussi les champs `tracks`/`track` en
                # `items`/`item` : on tente cette forme si `uris` est rejeté.
                self._request(
                    "POST",
                    f"/playlists/{playlist_id}/items",
                    json={"items": [{"uri": uri} for uri in chunk]},
                )
