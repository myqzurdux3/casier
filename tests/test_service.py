"""Tâches métier, avec un faux client Spotify — aucun réseau, aucune clé Claude."""

import json

import pytest

from spotify_sort import classify, service


@pytest.fixture(autouse=True)
def sans_claude(monkeypatch):
    monkeypatch.setattr(
        classify, "classify", lambda tracks, refs=None: {t["id"]: ["chill"] for t in tracks}
    )


def test_fetch_ecrit_avant_denrichir(fake_spotify, monkeypatch):
    """Les titres doivent être sur disque avant l'étape des genres.

    Une panne pendant la récupération des genres a déjà fait perdre 250 titres :
    le fichier n'était écrit qu'à la toute fin.
    """
    fake_spotify.saved = {"a", "b", "c"}
    ecrits = []

    def genres_qui_echouent(tracks):
        ecrits.append(json.loads(service.LIKED.read_text()))
        raise RuntimeError("panne réseau")

    fake_spotify.attach_artist_genres = genres_qui_echouent

    with pytest.raises(RuntimeError):
        service.task_fetch()

    assert len(ecrits) == 1 and len(ecrits[0]) == 3
    service.LIKED.unlink(missing_ok=True)


def test_sync_likes_ajoute_les_manquants(fake_spotify):
    fake_spotify.saved = {"a"}
    fake_spotify.playlists = {"Chill": "pl1", "Fête": "pl2"}
    fake_spotify.items = {"pl1": ["a", "b"], "pl2": ["c", "a"]}

    ajoutes = service.task_sync_likes()

    assert ajoutes == 2
    assert fake_spotify.saved == {"a", "b", "c"}


def test_sync_likes_sans_manquant(fake_spotify):
    fake_spotify.saved = {"a", "b"}
    fake_spotify.playlists = {"Chill": "pl1"}
    fake_spotify.items = {"pl1": ["a", "b"]}

    assert service.task_sync_likes() == 0


def test_sync_likes_dedoublonne(fake_spotify):
    """Un titre présent dans trois playlists ne doit être liké qu'une fois."""
    fake_spotify.saved = set()
    fake_spotify.playlists = {"A": "p1", "B": "p2", "C": "p3"}
    fake_spotify.items = {"p1": ["x"], "p2": ["x"], "p3": ["x"]}

    assert service.task_sync_likes() == 1


def test_reference_playlist_absente(fake_spotify, monkeypatch):
    """Une playlist de référence introuvable est ignorée, pas fatale."""
    monkeypatch.setattr(
        service.config, "REFERENCE_PLAYLISTS", {"inexistante": "white-girl-music"}
    )
    resultat = service.task_reference()
    assert resultat == {}
    assert json.loads(service.REFERENCES.read_text()) == {}
    service.REFERENCES.unlink(missing_ok=True)


def test_reference_lit_la_playlist(fake_spotify, monkeypatch):
    monkeypatch.setattr(
        service.config, "REFERENCE_PLAYLISTS", {"white girl music vieux": "white-girl-music"}
    )
    fake_spotify.playlists = {"white girl music vieux": "wgm"}
    fake_spotify.items = {"wgm": ["t1", "t2", "t3"]}

    assert service.task_reference() == {"white-girl-music": 3}
    service.REFERENCES.unlink(missing_ok=True)


def test_job_for_traduit_les_actions():
    for action in service.JOB_ACTIONS:
        nom, fonction, args = service.job_for(action)
        assert callable(fonction), action
        assert nom == service.JOB_ACTIONS[action]


def test_job_for_passe_les_parametres():
    _, fonction, args = service.job_for("sort", {"limit": 12})
    assert fonction is service.task_sort and args == (12,)

    _, fonction, args = service.job_for("import", {"only": ["chill"], "public": True})
    assert fonction is service.task_import and args == (["chill"], True)


def test_job_for_action_inconnue():
    with pytest.raises(ValueError):
        service.job_for("nimportequoi")


def test_doctor_survit_a_toutes_les_pannes(fake_spotify, monkeypatch):
    """Le diagnostic ne doit jamais lever : c'est lui qui rapporte les pannes."""

    def boom(*args, **kwargs):
        raise RuntimeError("cassé")

    fake_spotify.me = boom
    fake_spotify._request = boom
    fake_spotify.create_playlist = boom
    monkeypatch.setattr(service.auth, "granted_scopes", lambda: set())

    assert service.task_doctor() is True


def test_error_text_nomme_les_exceptions_muettes():
    assert service.error_text(KeyError()) == "KeyError"
    assert "ValueError" in service.error_text(ValueError("détail"))


def test_status_sans_donnees(fake_spotify):
    service.LIKED.unlink(missing_ok=True)
    service.PLAYLISTS.unlink(missing_ok=True)

    etat = service.status()
    assert etat["liked_count"] == 0
    assert etat["has_result"] is False
    assert etat["playlist_count"] == 0
