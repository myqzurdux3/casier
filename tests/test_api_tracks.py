"""Classement à l'unité, résultat et réglages via l'API."""

import json

import pytest
import requests

from spotify_sort import classify, service
from spotify_sort.spotify import SpotifyError

TRACK_ID = "4cOdK2wGLETKBW3PvgPWqT"
LIEN = f"https://open.spotify.com/track/{TRACK_ID}"


class _Response:
    """Réponse HTTP minimale, de quoi construire un vrai SpotifyError."""

    def __init__(self, status, payload):
        self.status_code = status
        self.text = json.dumps(payload)
        self.headers = {"content-type": "application/json"}
        self._payload = payload

    def json(self):
        return self._payload


def _spotify_error(status=403, message="Insufficient client scope"):
    return SpotifyError(_Response(status, {"error": {"message": message}}), "/me/library")


@pytest.fixture
def sans_claude(monkeypatch):
    """Classification déterministe : les tests portent sur la façade, pas sur Claude."""
    monkeypatch.setattr(
        classify, "classify", lambda tracks, refs=None: {t["id"]: ["chill"] for t in tracks}
    )


def test_lien_invalide_donne_400(client, headers, fake_spotify, sans_claude):
    """Une faute de saisie est une erreur du client, pas une panne du serveur."""
    response = client.post(
        "/api/v1/tracks/classify", headers=headers, json={"link": "nimportequoi"}
    )
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "bad_request"
    assert "non reconnu" in response.get_json()["error"]["message"]


def test_lien_manquant(client, headers, fake_spotify):
    for corps in ({}, {"link": ""}, {"link": "   "}):
        response = client.post("/api/v1/tracks/classify", headers=headers, json=corps)
        assert response.status_code == 400, corps


def test_sans_compte_spotify(client, headers, monkeypatch):
    import spotify_sort.auth as auth_module

    monkeypatch.setattr(auth_module, "has_token", lambda: False)
    response = client.post("/api/v1/tracks/classify", headers=headers, json={"link": LIEN})
    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "spotify_disconnected"


def test_classement_sans_ajout(client, headers, fake_spotify, sans_claude):
    response = client.post(
        "/api/v1/tracks/classify", headers=headers, json={"link": LIEN, "add": False}
    )
    assert response.status_code == 200
    body = response.get_json()
    assert body["track"]["id"] == TRACK_ID
    assert [r["status"] for r in body["rows"]] == ["proposé"]
    # Rien ne doit avoir été écrit sur le compte.
    assert fake_spotify.added == []
    assert fake_spotify.saved == set()


def test_ajout_like_le_titre(client, headers, fake_spotify, sans_claude):
    """Exigence explicite : un titre rangé dans une playlist est aussi liké."""
    fake_spotify.playlists = {"Chill": "pl-chill"}
    response = client.post(
        "/api/v1/tracks/classify", headers=headers, json={"link": LIEN, "add": True}
    )
    assert response.status_code == 200

    rows = {r["name"]: r["status"] for r in response.get_json()["rows"]}
    assert rows["Titres likés"] == "ajouté"
    assert TRACK_ID in fake_spotify.saved
    assert fake_spotify.added == [("pl-chill", [f"spotify:track:{TRACK_ID}"])]


def test_ajout_titre_deja_like(client, headers, fake_spotify, sans_claude):
    fake_spotify.saved = {TRACK_ID}
    fake_spotify.playlists = {"Chill": "pl-chill"}
    response = client.post(
        "/api/v1/tracks/classify", headers=headers, json={"link": LIEN, "add": True}
    )
    rows = {r["name"]: r["status"] for r in response.get_json()["rows"]}
    assert rows["Titres likés"] == "déjà présent"


def test_playlist_absente_du_compte(client, headers, fake_spotify, sans_claude):
    response = client.post(
        "/api/v1/tracks/classify", headers=headers, json={"link": LIEN, "add": True}
    )
    rows = {r["name"]: r["status"] for r in response.get_json()["rows"]}
    assert rows["Chill"] == "playlist absente du compte"
    assert fake_spotify.added == []


def test_echec_du_like_nempeche_pas_le_reste(client, headers, fake_spotify, sans_claude):
    """Un refus sur les likés ne doit pas faire échouer le rangement en playlist."""
    fake_spotify.playlists = {"Chill": "pl-chill"}

    def refuse(track_ids):
        raise _spotify_error()

    fake_spotify.save_tracks = refuse

    response = client.post(
        "/api/v1/tracks/classify", headers=headers, json={"link": LIEN, "add": True}
    )
    assert response.status_code == 200
    rows = {r["name"]: r["status"] for r in response.get_json()["rows"]}
    assert "échec" in rows["Titres likés"]
    assert rows["Chill"] == "ajouté"


def test_spotify_en_panne_donne_502(client, headers, fake_spotify, sans_claude):
    def boom(track_id):
        raise _spotify_error(503, "Service unavailable")

    fake_spotify.track = boom

    response = client.post("/api/v1/tracks/classify", headers=headers, json={"link": LIEN})
    assert response.status_code == 502
    assert response.get_json()["error"]["code"] == "spotify_denied"


def test_claude_indisponible_donne_502(client, headers, fake_spotify, monkeypatch):
    def boom(tracks, refs=None):
        raise classify.ClassificationError("Aucune clé API Claude trouvée.")

    monkeypatch.setattr(classify, "classify", boom)

    response = client.post("/api/v1/tracks/classify", headers=headers, json={"link": LIEN})
    assert response.status_code == 502
    assert response.get_json()["error"]["code"] == "classification_failed"


def test_erreur_imprevue_reste_du_json(client, headers, fake_spotify, monkeypatch):
    """Un client JSON ne doit jamais recevoir la page HTML d'erreur du panel."""

    def boom(tracks, refs=None):
        raise requests.ConnectionError()

    monkeypatch.setattr(classify, "classify", boom)

    response = client.post("/api/v1/tracks/classify", headers=headers, json={"link": LIEN})
    assert response.status_code == 500
    assert response.is_json
    erreur = response.get_json()["error"]
    assert erreur["code"] == "internal"
    # str(ConnectionError()) est vide : sans le nom de la classe, message inutile.
    assert "ConnectionError" in erreur["message"]


def test_corps_non_objet(client, headers, fake_spotify):
    response = client.post(
        "/api/v1/tracks/classify",
        headers={**headers, "Content-Type": "application/json"},
        data="[1, 2, 3]",
    )
    assert response.status_code == 400


# --- Résultat ---------------------------------------------------------------


@pytest.fixture
def document():
    service.OUT.mkdir(parents=True, exist_ok=True)
    contenu = {
        "track_count": 2,
        "playlists": [
            {"key": "chill", "name": "Chill", "track_ids": ["aaa", "bbb"]},
            {"key": "fete", "name": "Fête", "track_ids": ["bbb"]},
        ],
        "tracks": {},
    }
    service.PLAYLISTS.write_text(json.dumps(contenu))
    yield contenu
    service.PLAYLISTS.unlink(missing_ok=True)


def test_result_sans_classement(client, headers):
    service.PLAYLISTS.unlink(missing_ok=True)
    response = client.get("/api/v1/result", headers=headers)
    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "no_result"


def test_result(client, headers, document):
    body = client.get("/api/v1/result", headers=headers).get_json()
    assert len(body["playlists"]) == 2


def test_retrait_dun_titre(client, headers, document):
    response = client.delete("/api/v1/result/chill/aaa", headers=headers)
    assert response.status_code == 200

    playlists = {p["key"]: p["track_ids"] for p in response.get_json()["playlists"]}
    assert playlists["chill"] == ["bbb"]
    assert playlists["fete"] == ["bbb"]
    # Le retrait est persisté, pas seulement renvoyé.
    sur_disque = json.loads(service.PLAYLISTS.read_text())
    assert sur_disque["playlists"][0]["track_ids"] == ["bbb"]


def test_playlist_videe_disparait(client, headers, document):
    client.delete("/api/v1/result/fete/bbb", headers=headers)
    body = client.get("/api/v1/result", headers=headers).get_json()
    assert [p["key"] for p in body["playlists"]] == ["chill"]


# --- Réglages ---------------------------------------------------------------


def test_lecture_des_reglages(client, headers):
    body = client.get("/api/v1/settings", headers=headers).get_json()
    assert body["tolerance"] in {"large", "stricte"}
    assert "moods" in body["categories"]


def test_ecriture_des_reglages(client, headers):
    response = client.put(
        "/api/v1/settings", headers=headers, json={"tolerance": "stricte"}
    )
    assert response.status_code == 200
    assert response.get_json()["tolerance"] == "stricte"
    assert client.get("/api/v1/settings", headers=headers).get_json()["tolerance"] == "stricte"

    client.put("/api/v1/settings", headers=headers, json={"tolerance": "large"})


def test_tolerance_invalide(client, headers):
    response = client.put(
        "/api/v1/settings", headers=headers, json={"tolerance": "moyenne"}
    )
    assert response.status_code == 400


def test_reglages_vides(client, headers):
    assert client.put("/api/v1/settings", headers=headers, json={}).status_code == 400


def test_ecriture_partielle_preserve_le_reste(client, headers):
    """Envoyer un seul champ ne doit pas effacer la taxonomie."""
    avant = client.get("/api/v1/settings", headers=headers).get_json()
    client.put("/api/v1/settings", headers=headers, json={"playlist_prefix": "🎵 "})
    apres = client.get("/api/v1/settings", headers=headers).get_json()

    assert apres["playlist_prefix"] == "🎵 "
    assert apres["categories"] == avant["categories"]

    client.put("/api/v1/settings", headers=headers, json={"playlist_prefix": ""})


def test_chaque_ligne_porte_la_cle_du_casier(client, headers, fake_spotify, sans_claude):
    """La teinte d'un casier vient de sa clé, jamais du nom affiché.

    Le nom porte le préfixe de playlist et peut être renommé dans les réglages ;
    la clé, elle, est stable. Sans elle, l'app ne peut pas colorer la ligne.
    """
    fake_spotify.playlists = {"Chill": "pl-chill"}
    response = client.post(
        "/api/v1/tracks/classify", headers=headers, json={"link": LIEN, "add": True}
    )
    assert response.status_code == 200
    rows = response.get_json()["rows"]

    # « Titres likés » n'est pas un casier : pas de clé, donc pas de couleur.
    likes = next(r for r in rows if r["name"] == "Titres likés")
    assert likes["key"] is None

    casiers = [r for r in rows if r["key"] is not None]
    assert [r["key"] for r in casiers] == ["chill"]


def test_la_cle_est_presente_meme_sans_ajout(client, headers, fake_spotify, sans_claude):
    response = client.post(
        "/api/v1/tracks/classify", headers=headers, json={"link": LIEN, "add": False}
    )
    assert [r["key"] for r in response.get_json()["rows"]] == ["chill"]
