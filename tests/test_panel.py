"""Non-régression du panel web après l'extraction de service.py.

L'API ne doit pas avoir été gagnée au prix du panel : mêmes routes, même
protection CSRF, mêmes redirections.
"""

import pytest

from tests.conftest import PASSWORD

PAGES = ["/", "/track", "/settings"]


@pytest.fixture
def connecte(client):
    client.get("/login")
    with client.session_transaction() as session:
        session["auth"] = True
    return client


def test_pages_exigent_la_connexion(client):
    for page in PAGES + ["/result"]:
        response = client.get(page)
        assert response.status_code == 302, page
        assert "/login" in response.headers["Location"]


def test_pages_accessibles_une_fois_connecte(connecte):
    for page in PAGES:
        assert connecte.get(page).status_code == 200, page


def test_connexion_par_mot_de_passe(client):
    client.get("/login")
    with client.session_transaction() as session:
        csrf = session["csrf"]

    response = client.post("/login", data={"password": PASSWORD, "csrf": csrf})
    assert response.status_code == 302
    assert client.get("/").status_code == 200


def test_csrf_exige_sur_le_panel(connecte):
    response = connecte.post("/run/fetch", data={})
    assert response.status_code == 400


def test_csrf_non_exige_sur_lapi(client):
    """L'API n'a pas de cookie, donc rien à falsifier — le garde ne s'y applique pas."""
    response = client.post("/api/v1/auth/login", json={"password": PASSWORD})
    assert response.status_code == 200


def test_action_inconnue_donne_404(connecte):
    with connecte.session_transaction() as session:
        csrf = session["csrf"]
    response = connecte.post("/run/nimportequoi", data={"csrf": csrf})
    assert response.status_code == 404


def test_page_erreur_remplace_le_500_muet(app):
    """La route est ajoutée avant toute requête : Flask fige ensuite le routage."""

    @app.route("/boum-test")
    def boum():
        raise KeyError("absente")

    client = app.test_client()
    with client.session_transaction() as session:
        session["auth"] = True

    response = client.get("/boum-test")
    assert response.status_code == 500
    corps = response.get_data(as_text=True)
    assert "Erreur serveur" in corps and "KeyError" in corps
    assert "The server encountered an internal error" not in corps


def test_le_resultat_affiche_les_carres_de_couleur(connecte, monkeypatch):
    """Le filtre `category_color` n'est exercé qu'au rendu.

    Une faute dans le gabarit ne se verrait qu'en production, sur la page
    ouverte par l'utilisateur — d'où ce rendu réel plutôt qu'un test du filtre.
    """
    import webapp

    from spotify_sort.colors import category_color

    document = {
        "track_count": 1,
        "playlists": [{"key": "rap-uk", "name": "Rap UK", "track_ids": ["t1"]}],
        "tracks": {"t1": {"title": "Titre", "artists": ["A"], "release_date": "2019-01-01"}},
    }
    # `webapp._load` et non `service.load` : l'alias est figé à l'import du
    # module, patcher la source ne l'atteindrait pas.
    monkeypatch.setattr(webapp, "_load", lambda path: document)

    html = connecte.get("/result").get_data(as_text=True)
    assert 'class="swatch"' in html
    assert category_color("rap-uk") in html
