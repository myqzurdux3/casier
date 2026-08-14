#!/usr/bin/env bash
# Installation du service spotify-sort. À lancer en root sur le VPS, depuis
# le dossier du projet déjà copié :
#
#   cd /opt/spotify-sort && sudo bash deploy/install.sh
#
# Idempotent : relançable sans casser une installation existante.

set -euo pipefail

APP_DIR=${APP_DIR:-/opt/spotify-sort}
APP_USER=${APP_USER:-spotify-sort}
ENV_FILE=${ENV_FILE:-/etc/spotify-sort.env}

[[ $EUID -eq 0 ]] || { echo "À lancer en root : sudo bash deploy/install.sh" >&2; exit 1; }
[[ -f "$APP_DIR/webapp.py" ]] || { echo "webapp.py introuvable dans $APP_DIR" >&2; exit 1; }

echo "==> Utilisateur système $APP_USER"
id -u "$APP_USER" &>/dev/null || \
    useradd --system --no-create-home --shell /usr/sbin/nologin "$APP_USER"

echo "==> Environnement Python"
if [[ ! -x "$APP_DIR/.venv/bin/gunicorn" ]]; then
    python3 -m venv "$APP_DIR/.venv"
fi
"$APP_DIR/.venv/bin/pip" install --quiet --upgrade pip
"$APP_DIR/.venv/bin/pip" install --quiet -r "$APP_DIR/requirements.txt"

echo "==> Dossiers"
mkdir -p "$APP_DIR/out" "$APP_DIR/secrets"
chown -R "$APP_USER:$APP_USER" "$APP_DIR"
chmod 700 "$APP_DIR/secrets"

echo "==> Fichier d'environnement"
if [[ ! -f "$ENV_FILE" ]]; then
    cp "$APP_DIR/deploy/spotify-sort.env.example" "$ENV_FILE"
    chown root:"$APP_USER" "$ENV_FILE"
    chmod 640 "$ENV_FILE"
    echo "    créé : $ENV_FILE  — À ÉDITER avant de démarrer"
    NEEDS_EDIT=1
else
    echo "    déjà présent, laissé tel quel : $ENV_FILE"
    NEEDS_EDIT=0
fi

echo "==> Unité systemd"
sed "s#/opt/spotify-sort#$APP_DIR#g" "$APP_DIR/deploy/spotify-sort.service" \
    > /etc/systemd/system/spotify-sort.service
systemctl daemon-reload
systemctl enable spotify-sort >/dev/null

echo
echo "Installation terminée."
echo
if [[ $NEEDS_EDIT -eq 1 ]]; then
    echo "  1. Édite les secrets :   sudo nano $ENV_FILE"
    echo "     (WEB_PASSWORD, SPOTIFY_CLIENT_ID, ANTHROPIC_API_KEY)"
    echo "  2. Copie le token depuis ta machine :"
    echo "       scp secrets/token.json USER@CE_SERVEUR:/tmp/"
    echo "     puis ici :"
    echo "       sudo install -o $APP_USER -g $APP_USER -m 600 \\"
    echo "           /tmp/token.json $APP_DIR/secrets/token.json && sudo rm /tmp/token.json"
    echo "  3. Démarre :             sudo systemctl start spotify-sort"
else
    echo "  Redémarre :   sudo systemctl restart spotify-sort"
fi
echo "  Journal :     journalctl -u spotify-sort -f"
