#!/usr/bin/env bash
# Génère l'autorité de certification et le certificat serveur de spotify-sort.
#
# L'app Android n'embarque QUE cette autorité et refuse les autorités système
# pour cet hôte : un certificat émis par n'importe quelle autorité publique ne
# permet donc pas de se faire passer pour ce serveur.
#
#   ./make-certs.sh 192.0.2.10
#
# Produit dans secrets/ :
#   ca.crt      à copier dans l'app (mobile/assets/ca.crt)
#   ca.key      À GARDER HORS LIGNE — qui l'a peut forger un certificat accepté
#   server.crt  servi par gunicorn
#   server.key  clé privée du serveur
set -euo pipefail

HOST="${1:-}"
if [[ -z "$HOST" ]]; then
    echo "Usage : $0 <ip-ou-domaine>" >&2
    echo "Exemple : $0 192.0.2.10" >&2
    exit 1
fi

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/secrets"
DAYS_CA=3650
DAYS_LEAF=3650

mkdir -p "$DIR"
chmod 700 "$DIR"
cd "$DIR"

if [[ -e ca.crt || -e server.crt ]]; then
    echo "Des certificats existent déjà dans $DIR." >&2
    echo "Les régénérer invalidera l'APK installé — il faudra le reconstruire." >&2
    read -rp "Continuer ? [y/N] " reponse
    [[ "$reponse" == "y" || "$reponse" == "Y" ]] || exit 1
fi

# Une adresse IP va dans un SAN de type IP, un nom de domaine dans un SAN DNS.
# Se tromper produit un certificat que le téléphone rejettera sans expliquer
# pourquoi.
if [[ "$HOST" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    SAN="IP:$HOST"
else
    SAN="DNS:$HOST"
fi

echo "Autorité…"
openssl req -x509 -newkey rsa:4096 -sha256 -days "$DAYS_CA" -nodes \
    -keyout ca.key -out ca.crt \
    -subj "/CN=spotify-sort CA/O=spotify-sort" \
    -addext "basicConstraints=critical,CA:TRUE,pathlen:0" \
    -addext "keyUsage=critical,keyCertSign,cRLSign" 2>/dev/null

echo "Certificat serveur pour $HOST ($SAN)…"
openssl req -newkey rsa:2048 -sha256 -nodes \
    -keyout server.key -out server.csr \
    -subj "/CN=$HOST/O=spotify-sort" 2>/dev/null

openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
    -days "$DAYS_LEAF" -sha256 -out server.crt \
    -extfile <(printf 'subjectAltName=%s\nbasicConstraints=CA:FALSE\nkeyUsage=critical,digitalSignature,keyEncipherment\nextendedKeyUsage=serverAuth\n' "$SAN") 2>/dev/null

rm -f server.csr ca.srl
chmod 600 ca.key server.key
chmod 644 ca.crt server.crt

echo
echo "Fait. Dans $DIR :"
openssl x509 -in server.crt -noout -subject -dates -ext subjectAltName | sed 's/^/  /'
echo
echo "Étapes suivantes :"
echo "  1. cp $DIR/ca.crt <projet>/mobile/assets/ca.crt   puis reconstruire l'APK"
echo "  2. mettre ca.key hors ligne (clé USB), puis :  rm $DIR/ca.key"
echo "     Le serveur n'en a pas besoin — seule sa régénération l'exige."
echo "  3. BASE_URL=https://$HOST dans /etc/spotify-sort.env"
echo "  4. systemctl restart spotify-sort"
