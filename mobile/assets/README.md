# assets/

## ca.crt — absent volontairement

L'autorité de certification est propre à ton serveur : elle est produite par
`deploy/make-certs.sh` et n'a aucun sens dans le dépôt.

    ./deploy/make-certs.sh 192.0.2.10
    cp secrets/ca.crt mobile/assets/ca.crt

Sans ce fichier, `expo prebuild` s'arrête avec un message explicite plutôt que
de produire un APK incapable de joindre le serveur.

Le certificat lui-même n'est pas un secret — c'est la clé `ca.key` qui l'est,
et elle ne doit jamais quitter le serveur ni entrer ici.
