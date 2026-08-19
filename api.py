"""API JSON de spotify-sort, consommée par l'app Android.

Montée sous `/api/v1` par `webapp.create_app()`. Elle partage `service.py` et
`jobs.py` avec le panel : les deux façades voient le même job en cours et les
mêmes fichiers de sortie.

Authentification par jeton porteur plutôt que par cookie de session. Sans
cookie, aucun site tiers ne peut faire émettre de requête authentifiée par le
navigateur : il n'y a donc pas de CSRF à protéger ici.
"""

import functools
import secrets
import traceback

from flask import Blueprint, current_app, jsonify, request

import spotify_sort
from spotify_sort import apitokens, auth, classify, config, i18n, jobs, service, throttle
from spotify_sort.spotify import SpotifyError

api = Blueprint("api", __name__, url_prefix="/api/v1")


def _lang() -> str:
    """Langue de la requête courante, d'après `Accept-Language`.

    En-tête standard plutôt qu'un paramètre propre : le client l'envoie déjà
    sur chaque appel, et rien dans le contrat de l'API ne change.
    """
    return i18n.resolve(request.headers.get("Accept-Language"))


# --- Erreurs ----------------------------------------------------------------


class ApiError(Exception):
    """Erreur destinée au client, avec un code stable qu'il peut tester."""

    def __init__(self, code: str, message: str, status: int, **extra):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status
        self.extra = extra


def _fail(exc: ApiError):
    payload = {"error": {"code": exc.code, "message": exc.message, **exc.extra}}
    return jsonify(payload), exc.status


@api.errorhandler(ApiError)
def _handle_api_error(exc: ApiError):
    return _fail(exc)


@api.errorhandler(Exception)
def _handle_unexpected(exc: Exception):
    """Filet de sécurité : un client JSON ne doit jamais recevoir de HTML.

    Le gestionnaire global de `webapp` rend une page ; sur le blueprint il est
    remplacé par celui-ci, qui répond dans le format attendu.
    """
    if isinstance(exc, ApiError):
        return _fail(exc)

    current_app.logger.error(
        "Erreur non gérée sur %s %s\n%s",
        request.method,
        request.path,
        traceback.format_exc(),
    )
    if isinstance(exc, SpotifyError):
        return _fail(ApiError("spotify_denied", service.error_text(exc), 502))
    if isinstance(exc, classify.ClassificationError):
        return _fail(ApiError("classification_failed", str(exc), 502))
    return _fail(ApiError("internal", service.error_text(exc), 500))


# --- Authentification -------------------------------------------------------


def _bearer() -> str:
    header = request.headers.get("Authorization", "")
    scheme, _, value = header.partition(" ")
    return value.strip() if scheme.lower() == "bearer" else ""


def token_required(view):
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if not apitokens.verify(_bearer()):
            raise ApiError(
                "bad_token", i18n.t("erreur.bad_token", _lang()), 401
            )
        return view(*args, **kwargs)

    return wrapped


def spotify_required(view):
    """Refuse tôt et explicitement quand aucun compte Spotify n'est lié."""

    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if not auth.has_token():
            raise ApiError(
                "spotify_disconnected",
                i18n.t("erreur.spotify_disconnected", _lang()),
                409,
            )
        return view(*args, **kwargs)

    return wrapped


def _body() -> dict:
    data = request.get_json(silent=True)
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ApiError("bad_request", i18n.t("erreur.json_attendu", _lang()), 400)
    return data


@api.post("/auth/login")
def login():
    ip = request.remote_addr or "?"
    if throttle.throttled(ip):
        raise ApiError("too_many_attempts", i18n.t("erreur.too_many_attempts", _lang()), 429)

    given = _body().get("password", "")
    if not isinstance(given, str) or not secrets.compare_digest(
        given, current_app.config["PASSWORD"]
    ):
        throttle.record(ip)
        raise ApiError("bad_password", i18n.t("erreur.bad_password", _lang()), 401)

    label = _body().get("device", "")
    return jsonify({"token": apitokens.issue(label if isinstance(label, str) else "")})


@api.post("/auth/logout")
@token_required
def logout():
    apitokens.revoke(_bearer())
    return jsonify({"ok": True})


# --- État -------------------------------------------------------------------


@api.get("/status")
@token_required
def status():
    running = jobs.running()
    return jsonify(
        {
            **service.status(),
            "version": spotify_sort.__version__,
            "job": running.snapshot(since=10**9) if running else None,
            "actions": service.job_labels(_lang()),
        }
    )


# --- Jobs -------------------------------------------------------------------


@api.post("/jobs/<action>")
@token_required
def start_job(action):
    if action not in service.JOB_ACTIONS:
        raise ApiError("bad_request", i18n.t("erreur.action_inconnue", _lang(), action=action), 400)
    if action in service.NEEDS_SPOTIFY and not auth.has_token():
        raise ApiError(
            "spotify_disconnected",
            i18n.t("erreur.spotify_disconnected", _lang()),
            409,
        )

    busy = jobs.running()
    if busy:
        raise ApiError(
            "job_busy",
            i18n.t("erreur.job_busy", _lang(), name=busy.name),
            409,
            job_id=busy.id,
        )

    body = _body()
    limit = body.get("limit")
    if limit is not None and (not isinstance(limit, int) or limit <= 0):
        raise ApiError("bad_request", i18n.t("erreur.limite_invalide", _lang()), 400)

    name, fn, args = service.job_for(
        action,
        {"limit": limit, "only": body.get("keys") or None, "public": bool(body.get("public"))},
        _lang(),
    )
    job = jobs.start(name, fn, *args)
    return jsonify({"job_id": job.id, "name": job.name}), 202


@api.get("/jobs/<job_id>")
@token_required
def job_state(job_id):
    job = jobs.get(job_id)
    if not job:
        raise ApiError("not_found", i18n.t("erreur.job_inconnu", _lang()), 404)
    return jsonify(job.snapshot(since=request.args.get("since", 0, type=int)))


# --- Titre à l'unité --------------------------------------------------------


@api.post("/tracks/classify")
@token_required
@spotify_required
def classify_track():
    body = _body()
    link = body.get("link", "")
    if not isinstance(link, str) or not link.strip():
        raise ApiError("bad_request", i18n.t("erreur.lien_manquant", _lang()), 400)

    try:
        return jsonify(service.classify_one(link.strip(), bool(body.get("add"))))
    except ValueError as exc:
        # Lien non reconnu : faute du client, pas du serveur.
        raise ApiError("bad_request", str(exc), 400) from exc


# --- Résultat ---------------------------------------------------------------


@api.get("/result")
@token_required
def result():
    document = service.load(service.PLAYLISTS)
    if not document:
        raise ApiError("no_result", i18n.t("erreur.no_result", _lang()), 404)
    return jsonify(document)


@api.delete("/result/<key>/<track_id>")
@token_required
def result_remove(key, track_id):
    try:
        document = service.remove_from_result(key, track_id)
    except FileNotFoundError as exc:
        raise ApiError("no_result", str(exc), 404) from exc
    return jsonify(document)


# --- Réglages ---------------------------------------------------------------


@api.get("/settings")
@token_required
def get_settings():
    return jsonify(config.current_settings())


@api.put("/settings")
@token_required
def put_settings():
    body = _body()
    if not body:
        raise ApiError("bad_request", i18n.t("erreur.reglages_vides", _lang()), 400)

    tolerance = body.get("tolerance")
    if tolerance is not None and tolerance not in {"large", "stricte"}:
        raise ApiError("bad_request", i18n.t("erreur.tolerance_invalide", _lang()), 400)

    return jsonify(service.update_settings(body))
