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
import os
import secrets
import traceback

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
from spotify_sort import auth, colors, config, i18n, jobs, service, throttle
from spotify_sort.service import LIKED, PLAYLISTS, REFERENCES

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

    # Le panel et l'app doivent donner la même teinte au même casier : les deux
    # dérivent la couleur de la clé de catégorie, jamais du nom affiché.
    app.jinja_env.filters["category_color"] = colors.category_color

    def _traduire(cle, **params):
        """Traduit dans la langue du navigateur qui demande la page.

        Lit `request` à l'appel et non à l'enregistrement : un gabarit n'est
        rendu que dans un contexte de requête, la langue y est donc connue.
        """
        return i18n.t(cle, i18n.resolve(request.headers.get("Accept-Language")), **params)

    def _nom_de_ligne(row):
        """Nom affiché d'une ligne de verdict.

        Les casiers portent le nom réel de leur playlist, qui ne se traduit
        pas. Seuls les Titres likés sont un libellé d'interface.
        """
        return _traduire("verdict.liked_songs") if row["name"] == service.LIKED_SONGS else row["name"]

    def _verdict(row):
        return _traduire(f"verdict.{row['status']}", detail=row.get("detail") or "")

    app.jinja_env.globals.update(t=_traduire, nom_de_ligne=_nom_de_ligne, verdict=_verdict)

    _warn_about_exposure(secure)
    _warn_about_oauth()
    _register(app)

    # Importé ici et non en tête de fichier : api.py n'a pas besoin de webapp,
    # mais l'inverse serait un cycle si l'import se faisait au chargement.
    from api import api as api_blueprint

    app.register_blueprint(api_blueprint)
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
#
# La limite de tentatives vit dans `throttle` : le panel et l'API partagent le
# même compteur, sinon l'un contourne la limite de l'autre.

_throttled = throttle.throttled
_record_attempt = throttle.record


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


_load = service.load
_error_text = service.error_text


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
        # L'API s'authentifie par jeton porteur, sans cookie : aucun site tiers
        # ne peut lui faire émettre de requête authentifiée, donc pas de CSRF à
        # protéger. Lui imposer le jeton du panel la rendrait inutilisable.
        if request.blueprint == "api":
            return None
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
            anthropic_ready=service.anthropic_ready(),
        )

    @app.post("/run/<action>")
    @login_required
    def run(action):
        if action in service.NEEDS_SPOTIFY and not auth.has_token():
            flash("Connecte d'abord ton compte Spotify.", "error")
            return redirect(url_for("index"))

        raw = request.form.get("limit", "").strip()
        params = {
            "limit": int(raw) if raw.isdigit() and int(raw) > 0 else None,
            "only": request.form.getlist("keys") or None,
            "public": request.form.get("public") == "1",
        }
        try:
            name, fn, args = service.job_for(action, params)
        except ValueError:
            abort(404)
        return _start(name, fn, *args)

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
        key = request.form.get("key", "")
        try:
            service.remove_from_result(key, request.form.get("track_id", ""))
        except FileNotFoundError:
            abort(404)
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
                results = [service.classify_one(link, add)]
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

            service.update_settings(data)
            flash("Réglages enregistrés.", "ok")
            return redirect(url_for("settings"))

        return render_template("settings.html", settings=config.current_settings())


app = create_app()

if __name__ == "__main__":
    app.run(
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "8000")),
        debug=False,
    )
