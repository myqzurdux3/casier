"""Interface web de spotify-sort — mono-utilisateur, destinée à être exposée
derrière un reverse proxy HTTPS.

Lancement :
    export WEB_PASSWORD='...'            # obligatoire
    export BASE_URL='https://exemple.fr' # obligatoire (callback OAuth)
    export SPOTIFY_CLIENT_ID='...'
    export ANTHROPIC_API_KEY='sk-ant-...'
    export TRUST_PROXY=1                 # si derrière un reverse proxy
    gunicorn -w 1 -b 127.0.0.1:8000 webapp:app

Exposition directe sur le réseau (sans proxy), LAN ou VPN de confiance :
    export HOST=0.0.0.0 ALLOW_INSECURE=1
    gunicorn -w 1 -b 0.0.0.0:8000 webapp:app
"""

import functools
import json
import os
import secrets
import time
import traceback
from pathlib import Path

from flask import (
    Flask,
    abort,
    flash,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.exceptions import HTTPException
from werkzeug.middleware.proxy_fix import ProxyFix

import spotify_sort
from spotify_sort import auth, classify, config, export, jobs
from spotify_sort import importer as import_module
from spotify_sort.spotify import Spotify, SpotifyError, ensure_liked, parse_track_id

OUT = Path(os.environ.get("SPOTIFY_SORT_OUT", config.STATE_DIR / "out"))
LIKED = OUT / "liked.json"
PLAYLISTS = OUT / "playlists.json"
REFERENCES = OUT / "references.json"

# Le serveur n'a pas de navigateur : la CLI ne doit pas tenter d'en ouvrir un.
os.environ.setdefault("SPOTIFY_SORT_HEADLESS", "1")
config.HEADLESS = True


# --- Fabrique ---------------------------------------------------------------


def _secret_key() -> bytes:
    """Clé de session stable entre redémarrages, sinon tout le monde est déconnecté."""
    env = os.environ.get("FLASK_SECRET_KEY")
    if env:
        return env.encode()
    path = config.secret_file("secret")
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.parent.chmod(0o700)
        path.write_text(secrets.token_hex(32))
        path.chmod(0o600)
    return path.read_text().strip().encode()


def create_app() -> Flask:
    app = Flask(__name__)
    jobs.install()

    password = os.environ.get("WEB_PASSWORD", "")
    if not password:
        raise RuntimeError(
            "WEB_PASSWORD n'est pas défini. L'interface serait accessible à tous.\n"
            "  export WEB_PASSWORD='une phrase de passe longue'"
        )
    if len(password) < 12:
        raise RuntimeError(
            "WEB_PASSWORD fait moins de 12 caractères. Sur une instance exposée "
            "à Internet, c'est cassable par force brute — allonge-le."
        )
    app.config["PASSWORD"] = password

    app.secret_key = _secret_key()
    # ALLOW_INSECURE=1 uniquement pour un test local en HTTP.
    secure = os.environ.get("ALLOW_INSECURE") != "1"
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=secure,
        PERMANENT_SESSION_LIFETIME=60 * 60 * 24 * 14,
        MAX_CONTENT_LENGTH=1024 * 1024,
    )
    # Derrière un reverse proxy : respecter X-Forwarded-Proto pour générer des
    # URL https (sinon le redirect_uri OAuth serait en http et Spotify refuse).
    #
    # Uniquement si TRUST_PROXY=1. Exposé en direct, faire confiance à
    # X-Forwarded-For laisserait n'importe qui forger son IP et contourner la
    # limite de tentatives de connexion.
    if os.environ.get("TRUST_PROXY") == "1":
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    _warn_about_exposure(secure)
    _warn_about_oauth()
    _register(app)
    return app


def _warn_about_oauth() -> None:
    """Le redirect_uri doit correspondre au caractère près à Spotify."""
    if config.BASE_URL:
        uri = f"{config.BASE_URL}/spotify/callback"
        print(f"\n  Redirect URI OAuth : {uri}")
        print("  Cette URL EXACTE doit figurer dans les Redirect URIs de l'app Spotify.")
        loopback = "127.0.0.1" in config.BASE_URL or "[::1]" in config.BASE_URL
        if not config.BASE_URL.startswith("https://") and not loopback:
            print(
                "\n  Spotify REFUSERA cette URL. HTTP n'est autorisé que pour une\n"
                "  adresse de bouclage littérale (127.0.0.1 ou [::1]) ; « localhost »\n"
                "  est interdit et une IP publique en HTTP aussi.\n"
                "  Deux issues :\n"
                "    - un domaine avec HTTPS (Caddy fait le certificat tout seul) ;\n"
                "    - BASE_URL=http://127.0.0.1:8000 et un tunnel\n"
                "      ssh -L 8000:127.0.0.1:8000 user@vps depuis ta machine.\n"
                "  Détails dans deploy/README.md.\n"
            )
    else:
        print(
            "\n  BASE_URL non défini : le redirect_uri sera déduit de la requête,\n"
            "  ce qui donne « redirect_uri: Not matching configuration » dès que\n"
            "  l'URL vue par le serveur diffère de celle enregistrée chez Spotify.\n"
            "  Définis BASE_URL, ex. export BASE_URL=https://sort.mondomaine.fr\n"
        )


def _warn_about_exposure(secure: bool) -> None:
    host = os.environ.get("HOST", "127.0.0.1")
    exposed = host not in {"127.0.0.1", "localhost", "::1"}
    trusted_proxy = os.environ.get("TRUST_PROXY") == "1"

    if exposed and not secure and not trusted_proxy:
        print(
            "\n  ATTENTION — écoute sur "
            f"{host} en HTTP sans reverse proxy.\n"
            "  Mot de passe et cookie de session circulent en clair sur le réseau.\n"
            "  Quiconque écoute le trafic peut prendre la main sur ton compte Spotify.\n"
            "  Acceptable sur un LAN de confiance ou un VPN ; jamais sur Internet.\n"
        )
    elif exposed and not trusted_proxy:
        print(
            f"\n  Écoute sur {host} sans TRUST_PROXY : les cookies exigent HTTPS.\n"
            "  Derrière un reverse proxy, mets TRUST_PROXY=1.\n"
        )


# --- Authentification -------------------------------------------------------

_ATTEMPTS: dict[str, list[float]] = {}
_MAX_ATTEMPTS = 8
_WINDOW = 300.0


def _throttled(ip: str) -> bool:
    now = time.time()
    hits = [t for t in _ATTEMPTS.get(ip, []) if now - t < _WINDOW]
    _ATTEMPTS[ip] = hits
    return len(hits) >= _MAX_ATTEMPTS


def _record_attempt(ip: str) -> None:
    _ATTEMPTS.setdefault(ip, []).append(time.time())


def login_required(view):
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("auth"):
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


def _csrf_token() -> str:
    if "csrf" not in session:
        session["csrf"] = secrets.token_urlsafe(32)
    return session["csrf"]


# --- Aides ------------------------------------------------------------------


def _load(path: Path):
    return json.loads(path.read_text()) if path.exists() else None


def _error_text(exc: BaseException) -> str:
    """Message lisible pour une exception quelconque.

    `str(exc)` seul est souvent vide (ConnectionError, KeyError…) : sans le nom
    de la classe, l'utilisateur n'a rien pour diagnostiquer.
    """
    message = str(exc).strip()
    if isinstance(exc, SpotifyError):
        return message
    return f"{exc.__class__.__name__} : {message}" if message else exc.__class__.__name__


def _redirect_uri() -> str:
    base = config.BASE_URL or request.url_root.rstrip("/")
    return f"{base}/spotify/callback"


def _start(name: str, fn, *args, **kwargs):
    """Démarre un job, ou renvoie celui déjà en cours (un seul à la fois)."""
    busy = jobs.running()
    if busy:
        flash(f"« {busy.name} » est déjà en cours.", "warn")
        return redirect(url_for("job_page", job_id=busy.id))
    job = jobs.start(name, fn, *args, **kwargs)
    return redirect(url_for("job_page", job_id=job.id))


# --- Tâches de fond ---------------------------------------------------------


def _task_fetch():
    spotify = Spotify()
    print("Récupération des titres likés…")
    tracks = spotify.liked_tracks()
    OUT.mkdir(parents=True, exist_ok=True)
    LIKED.write_text(json.dumps(tracks, ensure_ascii=False, indent=2))
    print(f"{len(tracks)} titres récupérés.")
    print("Récupération des genres des artistes…")
    if spotify.attach_artist_genres(tracks):
        LIKED.write_text(json.dumps(tracks, ensure_ascii=False, indent=2))
        print("Genres ajoutés.")
    return len(tracks)


def _task_reference():
    spotify = Spotify()
    references: dict[str, list[dict]] = {}
    for name, key in config.REFERENCE_PLAYLISTS.items():
        playlist = spotify.find_playlist(name)
        if not playlist:
            print(f"  ✗ « {name} » introuvable sur le compte — ignorée.")
            continue
        items = spotify.playlist_items(playlist["id"])
        references.setdefault(key, []).extend(items)
        print(f"  ✓ « {name} » → `{key}` : {len(items)} titres")
    OUT.mkdir(parents=True, exist_ok=True)
    REFERENCES.write_text(json.dumps(references, ensure_ascii=False, indent=2))
    return {k: len(v) for k, v in references.items()}


def _task_sort(limit: int | None):
    if not LIKED.exists():
        _task_fetch()
    tracks = _load(LIKED) or []
    if limit:
        tracks = tracks[:limit]
        print(f"Limité à {len(tracks)} titres.")

    if config.REFERENCE_PLAYLISTS and not REFERENCES.exists():
        print("Récupération des playlists de référence…")
        _task_reference()

    assignments = classify.classify(tracks, _load(REFERENCES) or {})
    document = export.build_document(tracks, assignments)
    export.write(document, OUT)
    print("\n" + export.summary(document))
    return {"playlists": len(document["playlists"]), "tracks": document["track_count"]}


def _task_import(only: list[str] | None, public: bool | None):
    import_module.run(PLAYLISTS, only=only, public=public)
    return True


def _task_sync_likes():
    """Like tout titre présent dans une playlist mais absent des Titres likés."""
    spotify = Spotify()
    print("Lecture des Titres likés…")
    saved = spotify.saved_track_ids()
    print(f"{len(saved)} déjà likés.")

    playlists = spotify.existing_playlists()
    print(f"Analyse de {len(playlists)} playlists…")

    missing = []
    for name, playlist_id in playlists.items():
        absent = [t["id"] for t in spotify.playlist_items(playlist_id) if t["id"] not in saved]
        if absent:
            missing.extend(absent)
            print(f"  {name} : {len(absent)} hors des likés")

    every = list(dict.fromkeys(missing))
    if not every:
        print("\nRien à faire — toutes les playlists sont couvertes par les likés.")
        return 0

    added = spotify.save_tracks(every)
    print(f"\n{added} titres ajoutés aux Titres likés.")
    return added


def _task_doctor():
    spotify = Spotify()
    print("Scopes accordés :")
    granted = auth.granted_scopes()
    for scope in config.SCOPES:
        print(f"  {'✓' if scope in granted else '✗'} {scope}")

    print("\nAccès API :")
    checks = [
        ("profil", lambda: spotify.me()["id"]),
        ("titres likés", lambda: f"{spotify._request('GET', '/me/tracks', params={'limit': 1})['total']} titres"),
        ("playlists", lambda: f"{spotify._request('GET', '/me/playlists', params={'limit': 1})['total']} playlists"),
        ("catalogue", lambda: spotify._request("GET", "/artists/0TnOYISbd1XYRBk9myaseg")["name"]),
    ]
    for label, fn in checks:
        try:
            print(f"  ✓ {label} — {fn()}")
        except Exception as exc:
            print(f"  ✗ {label} — {exc}")

    print("\nÉcriture :")
    try:
        pid = spotify.create_playlist("spotify-sort — test", "Test, supprimé aussitôt.", False)
        print("  ✓ création (POST /me/playlists)")
        spotify.unfollow_playlist(pid)
        print("  ✓ suppression de la playlist de test")
    except SpotifyError as exc:
        print(f"  ✗ {exc}")
    return True


# --- Routes -----------------------------------------------------------------


def _register(app: Flask) -> None:
    @app.errorhandler(Exception)
    def _unhandled(exc):
        """Remplace la page « Internal Server Error » de Flask, qui ne dit rien.

        La trace complète part sur stderr — donc dans `journalctl -u
        spotify-sort` — et le message est affiché à l'écran, sans quoi toute
        erreur imprévue est indébogable depuis l'interface.
        """
        if isinstance(exc, HTTPException):
            return exc
        app.logger.error(
            "Erreur non gérée sur %s %s\n%s",
            request.method,
            request.path,
            traceback.format_exc(),
        )
        return render_template("error.html", detail=_error_text(exc)), 500

    @app.before_request
    def _guard():
        if request.method == "POST":
            sent = request.form.get("csrf") or request.headers.get("X-CSRF-Token")
            if not sent or not secrets.compare_digest(sent, session.get("csrf", "")):
                abort(400, "Jeton CSRF invalide — recharge la page.")
        g.spotify_ready = auth.has_token()

    @app.context_processor
    def _inject():
        return {
            "version": spotify_sort.__version__,
            "csrf_token": _csrf_token,
            "spotify_ready": getattr(g, "spotify_ready", False),
            "running_job": jobs.running(),
            "has_liked": LIKED.exists(),
            "has_result": PLAYLISTS.exists(),
        }

    # --- session ---

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            ip = request.remote_addr or "?"
            if _throttled(ip):
                flash("Trop de tentatives. Réessaie dans 5 minutes.", "error")
                return render_template("login.html"), 429
            given = request.form.get("password", "")
            if secrets.compare_digest(given, app.config["PASSWORD"]):
                session.clear()
                session.permanent = True
                session["auth"] = True
                _csrf_token()
                target = request.args.get("next", "")
                return redirect(target if target.startswith("/") else url_for("index"))
            _record_attempt(ip)
            flash("Mot de passe incorrect.", "error")
        _csrf_token()  # jeton disponible dès le formulaire de connexion
        return render_template("login.html")

    @app.post("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))

    # --- Spotify OAuth ---

    @app.get("/spotify/login")
    @login_required
    def spotify_login():
        verifier, challenge = auth.pkce_pair()
        state = secrets.token_urlsafe(16)
        session["pkce"] = verifier
        session["state"] = state
        try:
            return redirect(auth.build_authorize_url(_redirect_uri(), state, challenge))
        except RuntimeError as exc:
            flash(str(exc), "error")
            return redirect(url_for("index"))

    @app.get("/spotify/callback")
    @login_required
    def spotify_callback():
        if request.args.get("error"):
            flash(f"Spotify a refusé : {request.args['error']}", "error")
            return redirect(url_for("index"))
        state = session.pop("state", None)
        verifier = session.pop("pkce", None)
        if not state or not verifier or request.args.get("state") != state:
            flash("State OAuth invalide — recommence la connexion.", "error")
            return redirect(url_for("index"))
        try:
            auth.exchange_code(request.args.get("code", ""), verifier, _redirect_uri())
            flash("Compte Spotify connecté.", "ok")
        except Exception as exc:
            flash(f"Échec de l'échange du code : {exc}", "error")
        return redirect(url_for("index"))

    @app.post("/spotify/logout")
    @login_required
    def spotify_logout():
        auth.forget_token()
        flash("Token Spotify oublié.", "ok")
        return redirect(url_for("index"))

    # --- pages ---

    @app.get("/")
    @login_required
    def index():
        document = _load(PLAYLISTS)
        liked = _load(LIKED) or []
        return render_template(
            "index.html",
            liked_count=len(liked),
            document=document,
            references=_load(REFERENCES) or {},
            base_url=config.BASE_URL,
            redirect_uri=_redirect_uri(),
            anthropic_ready=bool(
                os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")
            ),
        )

    @app.post("/run/<action>")
    @login_required
    def run(action):
        if action != "doctor" and not auth.has_token():
            flash("Connecte d'abord ton compte Spotify.", "error")
            return redirect(url_for("index"))

        if action == "fetch":
            return _start("Récupération des likés", _task_fetch)
        if action == "reference":
            return _start("Playlists de référence", _task_reference)
        if action == "doctor":
            return _start("Diagnostic", _task_doctor)
        if action == "sync-likes":
            return _start("Rattrapage des likes", _task_sync_likes)
        if action == "sort":
            raw = request.form.get("limit", "").strip()
            limit = int(raw) if raw.isdigit() and int(raw) > 0 else None
            return _start("Classement", _task_sort, limit)
        if action == "import":
            only = request.form.getlist("keys") or None
            public = request.form.get("public") == "1"
            return _start("Import vers Spotify", _task_import, only, public)
        abort(404)

    @app.get("/jobs/<job_id>")
    @login_required
    def job_page(job_id):
        job = jobs.get(job_id) or abort(404)
        return render_template("job.html", job=job)

    @app.get("/api/jobs/<job_id>")
    @login_required
    def job_api(job_id):
        job = jobs.get(job_id) or abort(404)
        return jsonify(job.snapshot(since=request.args.get("since", 0, type=int)))

    @app.get("/result")
    @login_required
    def result():
        document = _load(PLAYLISTS)
        if not document:
            flash("Aucun classement. Lance d'abord un classement.", "warn")
            return redirect(url_for("index"))
        return render_template("result.html", document=document)

    @app.post("/result/remove")
    @login_required
    def result_remove():
        document = _load(PLAYLISTS) or abort(404)
        key = request.form.get("key")
        track_id = request.form.get("track_id")
        for playlist in document["playlists"]:
            if playlist["key"] == key:
                playlist["track_ids"] = [t for t in playlist["track_ids"] if t != track_id]
        document["playlists"] = [p for p in document["playlists"] if p["track_ids"]]
        PLAYLISTS.write_text(json.dumps(document, ensure_ascii=False, indent=2))
        flash("Titre retiré de la playlist.", "ok")
        return redirect(url_for("result") + f"#{key}")

    @app.route("/track", methods=["GET", "POST"])
    @login_required
    def track_page():
        results = None
        if request.method == "POST":
            if not auth.has_token():
                flash("Connecte d'abord ton compte Spotify.", "error")
                return redirect(url_for("index"))
            link = request.form.get("link", "").strip()
            add = request.form.get("add") == "1"
            try:
                results = _classify_one(link, add)
            except Exception as exc:
                # Réseau coupé, Claude injoignable, réponse inattendue… : tout
                # doit revenir sur la page plutôt que de finir en 500 opaque.
                app.logger.error(
                    "Classement de « %s » échoué\n%s", link, traceback.format_exc()
                )
                flash(_error_text(exc), "error")
        return render_template("track.html", results=results)

    @app.route("/settings", methods=["GET", "POST"])
    @login_required
    def settings():
        if request.method == "POST":
            data = config.current_settings()
            data["tolerance"] = request.form.get("tolerance", data["tolerance"])
            data["playlist_prefix"] = request.form.get("playlist_prefix", "")
            data["playlist_public"] = request.form.get("playlist_public") == "1"

            refs = {}
            for name, key in zip(
                request.form.getlist("ref_name"), request.form.getlist("ref_key")
            ):
                if name.strip() and key.strip():
                    refs[name.strip()] = key.strip()
            data["reference_playlists"] = refs

            for group, entries in data["categories"].items():
                for key in list(entries):
                    name = request.form.get(f"name__{group}__{key}")
                    desc = request.form.get(f"desc__{group}__{key}")
                    if request.form.get(f"del__{group}__{key}") == "1":
                        entries.pop(key)
                        continue
                    if name:
                        entries[key]["name"] = name
                    if desc:
                        entries[key]["description"] = desc

            new_key = request.form.get("new_key", "").strip()
            new_group = request.form.get("new_group", "specials")
            if new_key and new_group in data["categories"]:
                data["categories"][new_group][new_key] = {
                    "name": request.form.get("new_name", "").strip() or new_key,
                    "description": request.form.get("new_desc", "").strip()
                    or "Catégorie personnalisée.",
                }

            config.save_settings(data)
            flash("Réglages enregistrés.", "ok")
            return redirect(url_for("settings"))

        return render_template("settings.html", settings=config.current_settings())


def _classify_one(link: str, add: bool) -> list[dict]:
    # Lien analysé avant d'ouvrir la session : un lien fautif ne doit pas coûter
    # un rafraîchissement de token ni masquer son erreur derrière une erreur d'auth.
    track_id = parse_track_id(link)
    spotify = Spotify()
    track = spotify.track(track_id)
    spotify.attach_artist_genres([track])
    assignments = classify.classify([track], _load(REFERENCES) or {})

    existing = spotify.existing_playlists() if add else {}
    rows = []

    if add:
        # Un titre rangé dans une playlist doit aussi être dans les Titres likés.
        try:
            liked = ensure_liked(spotify, [track["id"]])
            rows.append(
                {
                    "name": "Titres likés",
                    "status": "ajouté" if liked else "déjà présent",
                }
            )
        except SpotifyError as exc:
            rows.append({"name": "Titres likés", "status": f"échec — {exc.detail or exc.status}"})

    for key in assignments[track["id"]]:
        name = config.display_name(key)
        status = "proposé"
        if add:
            playlist_id = existing.get(name)
            if not playlist_id:
                status = "playlist absente du compte"
            elif track["id"] in spotify.playlist_track_ids(playlist_id):
                status = "déjà présent"
            else:
                spotify.add_tracks(playlist_id, [track["uri"]])
                status = "ajouté"
        rows.append({"name": name, "status": status})
    return [{"track": track, "rows": rows}]


app = create_app()

if __name__ == "__main__":
    app.run(
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "8000")),
        debug=False,
    )
