"""Authentification Spotify (OAuth 2.0 + PKCE, sans client secret)."""

import base64
import hashlib
import http.server
import json
import os
import secrets
import threading
import time
import urllib.parse
import webbrowser
from pathlib import Path

import requests

from . import config

TOKEN_PATH = config.secret_file("token.json")
AUTH_URL = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"


def pkce_pair() -> tuple[str, str]:
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(64)).rstrip(b"=").decode()
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return verifier, challenge


class _CallbackHandler(http.server.BaseHTTPRequestHandler):
    result: dict = {}

    def do_GET(self):  # noqa: N802
        query = urllib.parse.urlparse(self.path).query
        _CallbackHandler.result = dict(urllib.parse.parse_qsl(query))
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(
            "<html><body style='font-family:sans-serif;text-align:center;"
            "padding-top:4rem'><h2>Connexion réussie</h2>"
            "<p>Tu peux fermer cet onglet et revenir au terminal.</p>"
            "</body></html>".encode()
        )

    def log_message(self, *_args):
        pass  # silence


def _wait_for_code(state: str) -> str:
    server = http.server.HTTPServer(("127.0.0.1", 8888), _CallbackHandler)
    thread = threading.Thread(target=server.handle_request, daemon=True)
    thread.start()
    thread.join(timeout=300)
    server.server_close()

    result = _CallbackHandler.result
    if not result:
        raise RuntimeError("Aucune réponse de Spotify (timeout de 5 minutes).")
    if "error" in result:
        raise RuntimeError(f"Spotify a refusé l'autorisation : {result['error']}")
    if result.get("state") != state:
        raise RuntimeError("State OAuth invalide — tentative de CSRF ?")
    return result["code"]


def require_client_id() -> str:
    client_id = config.SPOTIFY_CLIENT_ID
    if not client_id:
        raise RuntimeError(
            "SPOTIFY_CLIENT_ID n'est pas défini.\n"
            "Crée une app sur https://developer.spotify.com/dashboard, ajoute\n"
            f"  {config.REDIRECT_URI}\n"
            "dans les Redirect URIs, puis :  export SPOTIFY_CLIENT_ID=xxxx"
        )
    return client_id


def build_authorize_url(redirect_uri: str, state: str, challenge: str) -> str:
    """URL d'autorisation Spotify. Partagée par la CLI et l'interface web."""
    params = {
        "client_id": require_client_id(),
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "state": state,
        "scope": " ".join(config.SCOPES),
        "code_challenge_method": "S256",
        "code_challenge": challenge,
    }
    return f"{AUTH_URL}?{urllib.parse.urlencode(params)}"


def exchange_code(code: str, verifier: str, redirect_uri: str) -> dict:
    """Échange le code d'autorisation contre un token, et le met en cache."""
    response = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": require_client_id(),
            "code_verifier": verifier,
        },
        timeout=30,
    )
    response.raise_for_status()
    return _save(response.json())


def has_token() -> bool:
    return TOKEN_PATH.exists() and not missing_scopes()


def forget_token() -> None:
    TOKEN_PATH.unlink(missing_ok=True)


def _save(tokens: dict) -> dict:
    tokens["expires_at"] = time.time() + tokens.get("expires_in", 3600) - 60
    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(TOKEN_PATH.parent, 0o700)
    TOKEN_PATH.write_text(json.dumps(tokens, indent=2))
    os.chmod(TOKEN_PATH, 0o600)
    return tokens


def _login() -> dict:
    """Flow interactif de la CLI : navigateur local + serveur de callback."""
    if config.HEADLESS:
        raise RuntimeError(
            "Aucun token Spotify valide et mode headless actif.\n"
            "Connecte-toi via l'interface web, ou lance une commande CLI "
            "sur une machine avec navigateur."
        )

    verifier, challenge = pkce_pair()
    state = secrets.token_urlsafe(16)
    url = build_authorize_url(config.REDIRECT_URI, state, challenge)

    print("Ouverture du navigateur pour autoriser l'accès à ton compte Spotify…")
    print(f"Si rien ne s'ouvre, colle cette URL :\n  {url}\n")
    webbrowser.open(url)

    code = _wait_for_code(state)
    return exchange_code(code, verifier, config.REDIRECT_URI)


def _refresh(tokens: dict) -> dict:
    response = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "refresh_token",
            "refresh_token": tokens["refresh_token"],
            "client_id": config.SPOTIFY_CLIENT_ID,
        },
        timeout=30,
    )
    if response.status_code >= 400:
        return _login()  # refresh token révoqué ou expiré
    new_tokens = response.json()
    new_tokens.setdefault("refresh_token", tokens["refresh_token"])
    return _save(new_tokens)


def granted_scopes(tokens: dict | None = None) -> set[str]:
    """Scopes réellement accordés par Spotify au token en cache."""
    if tokens is None:
        if not TOKEN_PATH.exists():
            return set()
        tokens = json.loads(TOKEN_PATH.read_text())
    return set((tokens.get("scope") or "").split())


def missing_scopes(tokens: dict | None = None) -> set[str]:
    return set(config.SCOPES) - granted_scopes(tokens)


def get_access_token() -> str:
    """Retourne un access token valide, en relançant le login si nécessaire."""
    if not TOKEN_PATH.exists():
        return _login()["access_token"]

    tokens = json.loads(TOKEN_PATH.read_text())

    # Un token mis en cache avant un changement de scopes reste techniquement
    # valide mais provoque des 403 opaques à l'écriture : on réautorise.
    absent = missing_scopes(tokens)
    if absent:
        print(f"Scopes manquants sur le token en cache : {', '.join(sorted(absent))}")
        print("Nouvelle autorisation nécessaire.\n")
        return _login()["access_token"]

    if tokens.get("expires_at", 0) > time.time():
        return tokens["access_token"]
    return _refresh(tokens)["access_token"]
