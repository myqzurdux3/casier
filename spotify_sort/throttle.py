"""Limite de tentatives de connexion, partagée par le panel et l'API.

Sans mise en commun, l'API deviendrait un contournement de la limite du panel :
huit essais par façade au lieu de huit au total.
"""

import threading
import time

MAX_ATTEMPTS = 8
WINDOW = 300.0

_LOCK = threading.Lock()
_ATTEMPTS: dict[str, list[float]] = {}


def throttled(ip: str) -> bool:
    now = time.time()
    with _LOCK:
        hits = [t for t in _ATTEMPTS.get(ip, []) if now - t < WINDOW]
        _ATTEMPTS[ip] = hits
        return len(hits) >= MAX_ATTEMPTS


def record(ip: str) -> None:
    with _LOCK:
        _ATTEMPTS.setdefault(ip, []).append(time.time())


def reset() -> None:
    """Vide le compteur — pour les tests."""
    with _LOCK:
        _ATTEMPTS.clear()
