"""Traduction : catalogue complet, négociation de langue, réponses de l'API."""

import pytest

from spotify_sort import i18n, service


@pytest.mark.parametrize("cle", sorted(i18n.MESSAGES))
def test_chaque_cle_existe_dans_toutes_les_langues(cle):
    """Une traduction oubliée doit tomber ici, pas sous les yeux du lecteur."""
    for langue in i18n.LANGUES:
        assert i18n.MESSAGES[cle].get(langue), f"{cle} manque en {langue}"


@pytest.mark.parametrize("cle", sorted(i18n.MESSAGES))
def test_les_champs_a_substituer_sont_les_memes(cle):
    """Un `{name}` présent d'un côté et pas de l'autre lèverait au formatage."""
    import string

    champs = {
        langue: {
            nom for _, nom, _, _ in string.Formatter().parse(texte) if nom
        }
        for langue, texte in i18n.MESSAGES[cle].items()
    }
    attendus = champs[i18n.DEFAUT]
    for langue, presents in champs.items():
        assert presents == attendus, f"{cle} : {langue} attend {presents}, fr attend {attendus}"


def test_toute_action_a_son_libelle():
    for action in service.JOB_ACTIONS:
        assert f"tache.{action}" in i18n.MESSAGES, action


@pytest.mark.parametrize(
    ("entete", "attendu"),
    [
        ("en-US,en;q=0.9,fr;q=0.8", "en"),
        ("fr-FR,fr;q=0.9,en;q=0.8", "fr"),
        # Langue inconnue en tête : on descend jusqu'à la première connue.
        ("de-DE,de;q=0.9,en;q=0.5", "en"),
        # Aucune langue connue : repli sur la langue d'origine du projet.
        ("de-DE,de;q=0.9", "fr"),
        ("", "fr"),
        (None, "fr"),
        # q malformé : traité comme un poids nul, sans lever.
        ("en;q=zzz,fr", "fr"),
    ],
)
def test_negociation(entete, attendu):
    assert i18n.resolve(entete) == attendu


def test_une_cle_inconnue_est_rendue_telle_quelle():
    """Un message manquant dégrade l'affichage ; il ne doit pas lever."""
    assert i18n.t("rien.du.tout", "en") == "rien.du.tout"


def test_substitution():
    assert i18n.t("verdict.failed", "en", detail="403") == "failed — 403"


# --- Bout en bout, à travers l'API -----------------------------------------


def test_l_erreur_est_traduite_selon_l_entete(client):
    anglais = client.get("/api/v1/status", headers={"Accept-Language": "en-GB,en;q=0.9"})
    assert anglais.status_code == 401
    assert anglais.get_json()["error"]["message"] == i18n.MESSAGES["erreur.bad_token"]["en"]

    francais = client.get("/api/v1/status", headers={"Accept-Language": "fr"})
    assert francais.get_json()["error"]["message"] == i18n.MESSAGES["erreur.bad_token"]["fr"]


def test_le_code_derreur_ne_depend_pas_de_la_langue(client):
    """Le client teste le code, jamais le message : il doit rester stable."""
    for entete in ("en", "fr", "de"):
        reponse = client.get("/api/v1/status", headers={"Accept-Language": entete})
        assert reponse.get_json()["error"]["code"] == "bad_token"


def test_sans_entete_la_reponse_reste_en_francais(client):
    reponse = client.get("/api/v1/status")
    assert reponse.get_json()["error"]["message"] == i18n.MESSAGES["erreur.bad_token"]["fr"]


def test_les_libelles_de_taches_suivent_la_langue(client, headers):
    anglais = client.get(
        "/api/v1/status", headers={**headers, "Accept-Language": "en"}
    ).get_json()
    assert anglais["actions"]["sort"] == "Sorting"

    francais = client.get(
        "/api/v1/status", headers={**headers, "Accept-Language": "fr"}
    ).get_json()
    assert francais["actions"]["sort"] == "Classement"
