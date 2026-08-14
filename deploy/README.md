# Déploiement sur VPS

## 1. Installer

```bash
sudo useradd --system --no-create-home --shell /usr/sbin/nologin spotify-sort
sudo mkdir -p /opt/spotify-sort

# copier le code dans /opt/spotify-sort, puis :
sudo chown -R spotify-sort:spotify-sort /opt/spotify-sort
sudo -u spotify-sort python3 -m venv /opt/spotify-sort/.venv
sudo -u spotify-sort /opt/spotify-sort/.venv/bin/pip install -r /opt/spotify-sort/requirements.txt
sudo -u spotify-sort mkdir -p /opt/spotify-sort/out /opt/spotify-sort/secrets
sudo -u spotify-sort chmod 700 /opt/spotify-sort/secrets
```

> **Installe sous `/opt`, pas sous `/home`.** L'unité active `ProtectHome=true`,
> qui masque `/home` en entier au service. Un projet dans `/home/spotify-sort`
> serait invisible et le service ne démarrerait pas. Si tu tiens à `/home`,
> passe `ProtectHome=false` dans l'unité et ajuste `ReadWritePaths`.

Tout vit dans le dossier du projet :

| Chemin | Contenu |
|---|---|
| `secrets/token.json` | token Spotify (`chmod 600`) |
| `secrets/secret` | clé de session Flask |
| `out/` | `liked.json`, `playlists.json`, `tracks.csv`, `settings.json` |

`SPOTIFY_SORT_HOME` déplace l'ensemble ailleurs si besoin.

## 2. Secrets

```bash
sudo cp deploy/spotify-sort.env.example /etc/spotify-sort.env
sudo chown root:spotify-sort /etc/spotify-sort.env
sudo chmod 640 /etc/spotify-sort.env
sudo nano /etc/spotify-sort.env
```

Fichier séparé et non `Environment=` dans l'unité : `systemctl show` affiche les
`Environment=` à n'importe quel utilisateur.

## 3. Service

```bash
sudo cp deploy/spotify-sort.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now spotify-sort

systemctl status spotify-sort
journalctl -u spotify-sort -f
```

Le service survit à la fermeture du terminal et redémarre au boot.

## 4. TLS pour l'app Android

L'app Android n'accepte qu'une autorité : la tienne. Génère-la sur le serveur.

```bash
cd /opt/spotify-sort
sudo -u spotify-sort ./deploy/make-certs.sh 192.0.2.10
```

Produit dans `secrets/` :

| Fichier | Rôle |
|---|---|
| `ca.crt` | autorité — à copier dans `mobile/assets/ca.crt` |
| `ca.key` | **à mettre hors ligne puis supprimer du serveur** |
| `server.crt`, `server.key` | servis par gunicorn |

`ca.key` est la seule vraie clé sensible du dispositif : qui la détient peut
forger un certificat que ton app acceptera. Le serveur n'en a pas besoin une
fois `server.crt` émis — copie-la sur une clé USB et supprime-la du VPS.

Dans `/etc/spotify-sort.env` :

```
BIND=0.0.0.0:8443
BASE_URL=https://192.0.2.10:8443
```

L'unité systemd passe déjà `--certfile` et `--keyfile` à gunicorn. Redémarre :

```bash
sudo systemctl restart spotify-sort
curl --cacert /opt/spotify-sort/secrets/ca.crt https://192.0.2.10:8443/login
```

Puis côté app, voir `mobile/README.md`.

### Renouvellement

Les certificats durent dix ans. S'ils sont régénérés, ou si `ca.key` fuit,
il faut **reconstruire et réinstaller l'APK** : l'ancienne autorité y est
embarquée. L'app affiche alors un message explicite plutôt qu'une erreur réseau
générique.

## 5. HTTPS avec un domaine (alternative)

Si tu préfères un certificat reconnu par les navigateurs — utile pour consulter
le panel depuis n'importe où sans avertissement — retire `--certfile`/`--keyfile`
de l'unité, remets `BIND=127.0.0.1:8000`, et place Caddy devant.

Règle Spotify, citée de la documentation :

> Use HTTPS for your redirect URI, unless you are using a loopback address, when
> HTTP is permitted. […] `localhost` is not allowed as redirect URI.

Appliqué aux nouvelles apps depuis le 9 avril 2025. Concrètement :

| Redirect URI | Accepté |
|---|---|
| `https://sort.mondomaine.fr/spotify/callback` | oui |
| `http://127.0.0.1:8000/spotify/callback` | oui — bouclage |
| `http://[::1]:8000/spotify/callback` | oui — bouclage IPv6 |
| `http://192.0.2.10/spotify/callback` | **non** — HTTP hors bouclage |
| `http://localhost:8000/spotify/callback` | **non** — `localhost` interdit |

Une IP publique en HTTP est donc impossible. Soit un domaine avec HTTPS, soit le
tunnel SSH décrit plus bas.

Caddy fait les deux en une ligne — `/etc/caddy/Caddyfile` :

```
sort.mondomaine.fr {
    reverse_proxy 127.0.0.1:8000
}
```

Caddy pose `X-Forwarded-Proto` tout seul ; `TRUST_PROXY=1` dans l'env suffit.

Avec nginx :

```nginx
server {
    server_name sort.mondomaine.fr;
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

Puis `sudo certbot --nginx -d sort.mondomaine.fr`.

Enfin, dans le dashboard Spotify, ajoute **exactement** :

```
https://sort.mondomaine.fr/spotify/callback
```

Sans slash final, sans différence de casse ou de sous-domaine. Le tableau de bord
affiche la valeur que l'app envoie réellement — compare les deux caractère par
caractère.

## Se connecter sans domaine

Une IP publique en HTTP est refusée par Spotify. Mais l'adresse de bouclage est
acceptée en HTTP — et un tunnel SSH fait passer le panel du VPS pour du
`127.0.0.1` côté navigateur.

### Tunnel SSH vers le panel (recommandé sans domaine)

Le VPS n'écoute que sur `127.0.0.1:8000`, donc rien n'est exposé publiquement.

Dans `/etc/spotify-sort.env` :

```
BASE_URL=http://127.0.0.1:8000
```

et **retire** `TRUST_PROXY` (pas de proxy dans ce montage).

Chez Spotify, enregistre exactement :

```
http://127.0.0.1:8000/spotify/callback
```

Puis depuis ta machine :

```bash
ssh -L 8000:127.0.0.1:8000 user@ton-vps
```

Laisse la session ouverte et va sur <http://127.0.0.1:8000> dans ton navigateur.
Ton navigateur voit du `127.0.0.1`, Spotify aussi, le callback redescend par le
tunnel. Tout fonctionne, OAuth compris.

Limite : le panel n'est joignable que via le tunnel. Pour un accès depuis le
téléphone ou sans SSH, il faut un domaine et HTTPS.

### Copier un token obtenu en local

Le rafraîchissement d'un token n'utilise pas le `redirect_uri` : un token obtenu
sur ta machine fonctionne tel quel sur le VPS, sans domaine ni tunnel.

```bash
python main.py doctor                       # sur ta machine, navigateur local
scp secrets/token.json user@ton-vps:/tmp/
```

Sur le VPS :

```bash
sudo install -o spotify-sort -g spotify-sort -m 600 \
    /tmp/token.json /opt/spotify-sort/secrets/token.json
sudo rm /tmp/token.json
sudo systemctl restart spotify-sort
```

Le `SPOTIFY_CLIENT_ID` doit être le même des deux côtés — le token y est lié.

## Dépannage

**`redirect_uri: Not matching configuration`** — l'URL envoyée diffère de celle
enregistrée. Le tableau de bord et les logs de démarrage affichent la valeur
envoyée :

```bash
journalctl -u spotify-sort | grep -i "redirect"
```

Causes fréquentes : `BASE_URL` absent, slash final en trop, `http` au lieu de
`https`, `TRUST_PROXY` non défini derrière un proxy (l'app génère alors du
`http://`), ou `www.` d'un côté seulement.

**Token perdu à chaque redémarrage** — `ProtectHome=true` masque `/home`. L'unité
force `HOME=/var/lib/spotify-sort` ; si tu changes d'utilisateur, ajuste aussi
`ReadWritePaths`.
