"""Authentification de l'API : jetons, révocation, limite de tentatives."""

import pytest

from spotify_sort import apitokens, throttle
from tests.conftest import PASSWORD

PROTECTED = [
    ("get", "/api/v1/status"),
    ("get", "/api/v1/result"),
    ("get", "/api/v1/settings"),
    ("post", "/api/v1/jobs/fetch"),
    ("post", "/api/v1/tracks/classify"),
    ("delete", "/api/v1/result/chill/abc"),
]


def test_login_donne_un_jeton(client):
    response = client.post("/api/v1/auth/login", json={"password": PASSWORD})
    assert response.status_code == 200
    assert len(response.get_json()["token"]) > 30


def test_mauvais_mot_de_passe(client):
    response = client.post("/api/v1/auth/login", json={"password": "faux"})
    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "bad_password"


def test_mot_de_passe_absent(client):
    assert client.post("/api/v1/auth/login", json={}).status_code == 401


@pytest.mark.parametrize("method,path", PROTECTED)
def test_sans_jeton(client, method, path):
    response = getattr(client, method)(path)
    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "bad_token"


@pytest.mark.parametrize("method,path", PROTECTED)
def test_jeton_revoque(client, token, method, path):
    apitokens.revoke(token)
    response = getattr(client, method)(
        path, headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 401


def test_jeton_mal_formate(client, token):
    for header in (token, f"Basic {token}", "Bearer", f"bearer {token}x"):
        response = client.get("/api/v1/status", headers={"Authorization": header})
        assert response.status_code == 401, header


def test_bearer_insensible_a_la_casse(client, token):
    response = client.get("/api/v1/status", headers={"Authorization": f"BEARER {token}"})
    assert response.status_code == 200


def test_limite_de_tentatives(client):
    for _ in range(throttle.MAX_ATTEMPTS):
        assert client.post("/api/v1/auth/login", json={"password": "faux"}).status_code == 401

    response = client.post("/api/v1/auth/login", json={"password": "faux"})
    assert response.status_code == 429
    assert response.get_json()["error"]["code"] == "too_many_attempts"

    # Le bon mot de passe est refusé lui aussi : c'est le but d'un blocage par IP.
    assert client.post("/api/v1/auth/login", json={"password": PASSWORD}).status_code == 429


def test_limite_partagee_avec_le_panel(client):
    """Sinon l'API doublerait le nombre d'essais accordés au mot de passe."""
    client.get("/login")  # pose le jeton CSRF en session
    with client.session_transaction() as session:
        csrf = session["csrf"]

    for _ in range(throttle.MAX_ATTEMPTS):
        client.post("/api/v1/auth/login", json={"password": "faux"})

    response = client.post("/login", data={"password": PASSWORD, "csrf": csrf})
    assert response.status_code == 429


def test_logout_revoque_le_jeton(client, token):
    headers = {"Authorization": f"Bearer {token}"}
    assert client.post("/api/v1/auth/logout", headers=headers).status_code == 200
    assert client.get("/api/v1/status", headers=headers).status_code == 401


def test_jetons_stockes_haches(client, token):
    """Lire le fichier ne doit pas suffire à se connecter."""
    contenu = apitokens.TOKENS_PATH.read_text()
    assert token not in contenu
    assert apitokens.verify(token)


def test_deux_appareils_independants(client):
    a = client.post("/api/v1/auth/login", json={"password": PASSWORD}).get_json()["token"]
    b = client.post("/api/v1/auth/login", json={"password": PASSWORD}).get_json()["token"]
    assert a != b

    apitokens.revoke(a)
    assert not apitokens.verify(a)
    assert apitokens.verify(b)
