"""Jetons porteurs pour l'API mobile.

Le panel web utilise un cookie de session ; une app native ne peut pas s'en
servir commodément et n'en a pas besoin. Elle échange une fois le mot de passe
contre un jeton long, qu'elle garde dans le stockage sécurisé du téléphone.

Les jetons sont stockés hachés : quelqu'un qui lit le fichier ne peut pas s'en
servir pour se connecter. C'est le même raisonnement qu'un fichier de mots de
passe — sauf qu'ici le secret étant déjà 32 octets aléatoires, un simple SHA-256
suffit : il n'y a rien à deviner par force brute, donc pas besoin d'un KDF lent.
"""

import hashlib
import json
import secrets
from datetime import datetime, timezone

from . import config

TOKENS_PATH = config.SECRETS_DIR / "api-tokens.json"


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _read() -> list[dict]:
    if not TOKENS_PATH.exists():
        return []
    try:
        data = json.loads(TOKENS_PATH.read_text())
    except (ValueError, OSError):
        return []
    return data if isinstance(data, list) else []


def _write(entries: list[dict]) -> None:
    TOKENS_PATH.parent.mkdir(parents=True, exist_ok=True)
    TOKENS_PATH.parent.chmod(0o700)
    TOKENS_PATH.write_text(json.dumps(entries, ensure_ascii=False, indent=2))
    TOKENS_PATH.chmod(0o600)


def issue(label: str = "") -> str:
    """Crée un jeton et retourne sa valeur en clair — la seule fois où elle existe."""
    token = secrets.token_urlsafe(32)
    entries = _read()
    entries.append(
        {
            "hash": _hash(token),
            "label": label[:80],
            "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
    )
    _write(entries)
    return token


def verify(token: str) -> bool:
    """Vrai si le jeton est connu.

    La comparaison passe par `compare_digest` sur des empreintes de longueur
    fixe : le temps de réponse ne renseigne pas sur le nombre de caractères
    corrects.
    """
    if not token:
        return False
    candidate = _hash(token)
    return any(secrets.compare_digest(candidate, e.get("hash", "")) for e in _read())


def revoke(token: str) -> bool:
    """Retire un jeton précis. Vrai s'il existait."""
    entries = _read()
    candidate = _hash(token)
    remaining = [e for e in entries if e.get("hash") != candidate]
    if len(remaining) == len(entries):
        return False
    _write(remaining)
    return True


def revoke_all() -> int:
    """Déconnecte tous les appareils. Retourne le nombre de jetons supprimés."""
    count = len(_read())
    _write([])
    return count


def listing() -> list[dict]:
    """Jetons émis, sans leur empreinte — de quoi afficher « 2 appareils connectés »."""
    return [
        {"label": e.get("label", ""), "created": e.get("created", "")} for e in _read()
    ]
