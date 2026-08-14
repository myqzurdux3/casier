"""Exécution de tâches longues en arrière-plan, avec journal consultable.

Le cœur de l'outil communique sa progression par `print`. Plutôt que de le
réécrire, on remplace `sys.stdout` par un routeur : chaque écriture part vers le
journal du job dont c'est le thread, et vers la sortie standard sinon.
"""

import io
import sys
import threading
import traceback
import uuid

_LOCK = threading.Lock()
_JOBS: dict[str, "Job"] = {}
_BY_THREAD: dict[int, "Job"] = {}
_MAX_JOBS = 40


class _Router(io.TextIOBase):
    """Aiguille les écritures vers le journal du job courant."""

    def __init__(self, real):
        self.real = real

    def write(self, text):
        # Le classement parallélise ses lots : les threads fils ne sont pas
        # enregistrés. En mono-utilisateur un seul job tourne à la fois, donc on
        # rattache les écritures orphelines à celui-là plutôt que de les perdre.
        job = _BY_THREAD.get(threading.get_ident()) or _sole_running()
        if job is None:
            return self.real.write(text)
        job.append(text)
        return len(text)

    def flush(self):
        self.real.flush()


def install() -> None:
    """À appeler une fois au démarrage du serveur."""
    if not isinstance(sys.stdout, _Router):
        sys.stdout = _Router(sys.stdout)


class Job:
    def __init__(self, name: str):
        self.id = uuid.uuid4().hex[:12]
        self.name = name
        self.status = "running"  # running | done | error
        self.result = None
        self.error = None
        self._lines: list[str] = []
        self._buffer = ""
        self._lock = threading.Lock()

    def append(self, text: str) -> None:
        with self._lock:
            self._buffer += text
            while "\n" in self._buffer:
                line, self._buffer = self._buffer.split("\n", 1)
                self._lines.append(line)

    def log(self, since: int = 0) -> list[str]:
        with self._lock:
            pending = [self._buffer] if self._buffer else []
            return (self._lines + pending)[since:]

    def snapshot(self, since: int = 0) -> dict:
        with self._lock:
            total = len(self._lines)
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status,
            "error": self.error,
            "lines": self.log(since),
            "next": total,
        }


def start(name: str, fn, *args, **kwargs) -> Job:
    job = Job(name)

    def wrapper():
        _BY_THREAD[threading.get_ident()] = job
        try:
            job.result = fn(*args, **kwargs)
            outcome = "done"
        except Exception as exc:
            job.error = str(exc) or exc.__class__.__name__
            job.append(f"\nERREUR : {job.error}\n")
            job.append(traceback.format_exc())
            outcome = "error"
        finally:
            _BY_THREAD.pop(threading.get_ident(), None)
        # Statut en dernier : le client cesse de poller dès qu'il n'est plus
        # « running », il doit donc déjà voir le journal complet.
        job.status = outcome

    with _LOCK:
        _JOBS[job.id] = job
        # Purge des jobs terminés les plus anciens.
        if len(_JOBS) > _MAX_JOBS:
            for jid, old in list(_JOBS.items())[: len(_JOBS) - _MAX_JOBS]:
                if old.status != "running":
                    _JOBS.pop(jid, None)

    threading.Thread(target=wrapper, name=f"job-{job.id}", daemon=True).start()
    return job


def _sole_running() -> "Job | None":
    active = [j for j in _JOBS.values() if j.status == "running"]
    return active[0] if len(active) == 1 else None


def get(job_id: str) -> Job | None:
    return _JOBS.get(job_id)


def running(name: str | None = None) -> Job | None:
    """Job en cours, éventuellement filtré par nom — évite les doublons."""
    for job in _JOBS.values():
        if job.status == "running" and (name is None or job.name == name):
            return job
    return None
