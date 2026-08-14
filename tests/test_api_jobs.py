"""Jobs pilotés par l'API : démarrage, journal incrémental, exclusion mutuelle."""

import threading
import time

import pytest

from spotify_sort import jobs, service


def _install_router():
    """Réinstalle le routeur de sortie dans la phase d'exécution du test.

    `jobs.install()` mémorise `sys.stdout` au moment de l'appel. Pytest remplace
    `sys.stdout` entre la phase de fixture et le corps du test : le routeur posé
    par `create_app()` n'est alors plus en place, et les journaux partiraient sur
    la sortie de pytest au lieu du job. Sous gunicorn le problème n'existe pas —
    personne ne remplace `sys.stdout` après le démarrage.
    """
    jobs.install()


def _wait(job_id, timeout=5.0):
    """Attend la fin d'un job. Évite les tests qui passent par hasard."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        job = jobs.get(job_id)
        if job and job.status != "running":
            return job
        time.sleep(0.01)
    raise AssertionError(f"Job {job_id} toujours en cours après {timeout}s")


@pytest.fixture
def controllable(monkeypatch):
    """Tâche dont le test décide quand elle se termine."""
    gate = threading.Event()

    def task():
        print("étape 1")
        gate.wait(timeout=5)
        print("étape 2")
        return "fini"

    monkeypatch.setattr(service, "task_fetch", task)
    monkeypatch.setattr(service.auth, "has_token", lambda: True)
    return gate


def test_action_inconnue(client, headers):
    response = client.post("/api/v1/jobs/nimportequoi", headers=headers)
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "bad_request"


def test_sans_compte_spotify(client, headers, monkeypatch):
    monkeypatch.setattr(service.auth, "has_token", lambda: False)
    import spotify_sort.auth as auth_module

    monkeypatch.setattr(auth_module, "has_token", lambda: False)

    response = client.post("/api/v1/jobs/fetch", headers=headers)
    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "spotify_disconnected"


def test_doctor_ne_demande_pas_de_compte(client, headers, monkeypatch):
    """`doctor` sert justement à diagnostiquer une connexion qui ne va pas."""
    monkeypatch.setattr(service, "task_doctor", lambda: True)
    import spotify_sort.auth as auth_module

    monkeypatch.setattr(auth_module, "has_token", lambda: False)

    response = client.post("/api/v1/jobs/doctor", headers=headers)
    assert response.status_code == 202


def test_demarrage_et_fin(client, headers, controllable):
    _install_router()
    response = client.post("/api/v1/jobs/fetch", headers=headers)
    assert response.status_code == 202
    job_id = response.get_json()["job_id"]
    assert response.get_json()["name"] == "Récupération des likés"

    controllable.set()
    job = _wait(job_id)
    assert job.status == "done"
    assert job.result == "fini"


def test_un_seul_job_a_la_fois(client, headers, controllable):
    first = client.post("/api/v1/jobs/fetch", headers=headers).get_json()["job_id"]

    second = client.post("/api/v1/jobs/fetch", headers=headers)
    assert second.status_code == 409
    body = second.get_json()["error"]
    assert body["code"] == "job_busy"
    # Le client doit pouvoir suivre le job en cours plutôt que d'échouer sec.
    assert body["job_id"] == first

    controllable.set()
    _wait(first)


def test_curseur_since_sans_doublon(client, headers, controllable):
    _install_router()
    job_id = client.post("/api/v1/jobs/fetch", headers=headers).get_json()["job_id"]

    # Attente active de la première ligne, écrite avant le blocage de la tâche.
    for _ in range(200):
        first = client.get(f"/api/v1/jobs/{job_id}?since=0", headers=headers).get_json()
        if first["lines"]:
            break
        time.sleep(0.01)
    assert "étape 1" in first["lines"][0]

    controllable.set()
    _wait(job_id)

    suite = client.get(
        f"/api/v1/jobs/{job_id}?since={first['next']}", headers=headers
    ).get_json()
    assert "étape 1" not in "".join(suite["lines"])
    assert any("étape 2" in ligne for ligne in suite["lines"])
    assert suite["status"] == "done"


def test_job_en_erreur_reste_consultable(client, headers, monkeypatch):
    _install_router()
    def boom():
        print("avant l'erreur")
        raise RuntimeError("ça casse")

    monkeypatch.setattr(service, "task_fetch", boom)
    monkeypatch.setattr(service.auth, "has_token", lambda: True)

    job_id = client.post("/api/v1/jobs/fetch", headers=headers).get_json()["job_id"]
    _wait(job_id)

    body = client.get(f"/api/v1/jobs/{job_id}", headers=headers).get_json()
    assert body["status"] == "error"
    assert "ça casse" in body["error"]
    assert any("avant l'erreur" in ligne for ligne in body["lines"])


def test_statut_termine_implique_journal_complet(client, headers, monkeypatch):
    """Le client cesse de poller dès que le statut n'est plus « running ».

    Si le statut basculait avant l'écriture du journal, la dernière ligne
    serait perdue pour un client rapide.
    """
    _install_router()
    monkeypatch.setattr(service, "task_doctor", lambda: print("dernière ligne"))
    import spotify_sort.auth as auth_module

    monkeypatch.setattr(auth_module, "has_token", lambda: True)

    job_id = client.post("/api/v1/jobs/doctor", headers=headers).get_json()["job_id"]

    for _ in range(500):
        body = client.get(f"/api/v1/jobs/{job_id}", headers=headers).get_json()
        if body["status"] != "running":
            assert any("dernière ligne" in ligne for ligne in body["lines"])
            return
        time.sleep(0.002)
    raise AssertionError("job jamais terminé")


def test_job_inconnu(client, headers):
    response = client.get("/api/v1/jobs/inexistant", headers=headers)
    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "not_found"


def test_limite_invalide(client, headers, monkeypatch):
    monkeypatch.setattr(service.auth, "has_token", lambda: True)
    import spotify_sort.auth as auth_module

    monkeypatch.setattr(auth_module, "has_token", lambda: True)

    for mauvaise in (-1, 0, "dix"):
        response = client.post(
            "/api/v1/jobs/sort", headers=headers, json={"limit": mauvaise}
        )
        assert response.status_code == 400, mauvaise


def test_status_expose_le_job_en_cours(client, headers, controllable):
    job_id = client.post("/api/v1/jobs/fetch", headers=headers).get_json()["job_id"]

    body = client.get("/api/v1/status", headers=headers).get_json()
    assert body["job"]["id"] == job_id
    assert body["job"]["status"] == "running"
    assert "fetch" in body["actions"]

    controllable.set()
    _wait(job_id)
