"""Isolation des tests.

`SPOTIFY_SORT_HOME` doit être posé AVANT le premier import de `config`, qui
calcule ses chemins au chargement. D'où la mise en place au niveau du module
plutôt que dans une fixture : sans cela, les tests écriraient dans le vrai
dossier `secrets/` et écraseraient le token Spotify de l'utilisateur.
"""

import os
import tempfile
from pathlib import Path

_HOME = Path(tempfile.mkdtemp(prefix="spotify-sort-tests-"))
os.environ["SPOTIFY_SORT_HOME"] = str(_HOME)
os.environ["SPOTIFY_SORT_OUT"] = str(_HOME / "out")
os.environ["SPOTIFY_SORT_SETTINGS"] = str(_HOME / "out" / "settings.json")
os.environ["SPOTIFY_SORT_HEADLESS"] = "1"
os.environ["WEB_PASSWORD"] = "mot-de-passe-de-test-long"
os.environ["ALLOW_INSECURE"] = "1"
os.environ.pop("BASE_URL", None)

import pytest  # noqa: E402

from spotify_sort import apitokens, config, jobs, throttle  # noqa: E402

# `secret_file()` récupère les secrets de l'ancien emplacement `~/.spotify-sort`.
# Pratique en production, indésirable ici : les tests copieraient le vrai token
# Spotify de l'utilisateur dans un dossier temporaire.
config.LEGACY_SECRETS_DIR = _HOME / "aucun-ancien-emplacement"

PASSWORD = os.environ["WEB_PASSWORD"]


@pytest.fixture
def app():
    import webapp

    application = webapp.create_app()
    application.config["TESTING"] = True
    return application


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture(autouse=True)
def clean_state():
    """Chaque test part d'un état vierge : jetons, jobs, compteur de tentatives."""
    apitokens.revoke_all()
    throttle.reset()
    jobs._JOBS.clear()
    jobs._BY_THREAD.clear()
    yield
    apitokens.revoke_all()
    throttle.reset()
    jobs._JOBS.clear()


@pytest.fixture
def token(client):
    response = client.post("/api/v1/auth/login", json={"password": PASSWORD})
    assert response.status_code == 200, response.data
    return response.get_json()["token"]


@pytest.fixture
def headers(token):
    return {"Authorization": f"Bearer {token}"}


class FakeSpotify:
    """Client Spotify de substitution — aucun appel réseau.

    Enregistre ce qu'on lui demande pour que les tests vérifient les effets et
    non seulement les valeurs de retour.
    """

    def __init__(self, liked=(), playlists=None, items=None):
        self.saved = set(liked)
        self.playlists = playlists or {}
        self.items = items or {}
        self.added: list[tuple[str, list[str]]] = []
        self.created: list[str] = []

    def liked_tracks(self):
        return [
            {
                "id": tid,
                "uri": f"spotify:track:{tid}",
                "title": f"Titre {tid}",
                "artists": ["Artiste"],
                "artist_ids": [],
                "album": "Album",
                "release_date": "2001-01-01",
                "popularity": 50,
                "added_at": "",
                "genres": [],
            }
            for tid in sorted(self.saved)
        ]

    def saved_track_ids(self):
        return set(self.saved)

    def attach_artist_genres(self, tracks):
        return False

    def existing_playlists(self):
        return dict(self.playlists)

    def playlist_items(self, playlist_id):
        return [{"id": tid, "title": "", "artists": [], "release_date": ""}
                for tid in self.items.get(playlist_id, [])]

    def playlist_track_ids(self, playlist_id):
        return set(self.items.get(playlist_id, []))

    def save_tracks(self, track_ids):
        self.saved.update(track_ids)
        return len(track_ids)

    def saved_contains(self, track_ids):
        return {tid: tid in self.saved for tid in track_ids}

    def add_tracks(self, playlist_id, uris):
        self.added.append((playlist_id, list(uris)))
        self.items.setdefault(playlist_id, []).extend(
            uri.rsplit(":", 1)[-1] for uri in uris
        )

    def track(self, track_id):
        return {
            "id": track_id,
            "uri": f"spotify:track:{track_id}",
            "title": "Titre de test",
            "artists": ["Artiste"],
            "artist_ids": [],
            "album": "Album",
            "release_date": "1994-05-01",
            "popularity": 42,
            "added_at": "",
            "genres": [],
        }

    def find_playlist(self, name):
        pid = self.playlists.get(name)
        return {"id": pid, "name": name} if pid else None

    def create_playlist(self, name, description, public):
        self.created.append(name)
        self.playlists[name] = f"pl-{len(self.created)}"
        return self.playlists[name]

    def unfollow_playlist(self, playlist_id):
        self.playlists = {k: v for k, v in self.playlists.items() if v != playlist_id}


@pytest.fixture
def fake_spotify(monkeypatch):
    """Remplace le client Spotify partout où le service l'instancie."""
    instance = FakeSpotify()
    from spotify_sort import service

    monkeypatch.setattr(service, "Spotify", lambda: instance)
    monkeypatch.setattr(service.auth, "has_token", lambda: True)
    import spotify_sort.auth as auth_module

    monkeypatch.setattr(auth_module, "has_token", lambda: True)
    return instance
