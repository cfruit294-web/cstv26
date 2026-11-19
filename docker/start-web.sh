#!/bin/sh
# Commande par défaut de l'image (CMD du Dockerfile) : collectstatic puis serveur web Daphne.
# docker-compose.yml n'en a pas besoin (il définit ses propres commandes) ; ce script sert si
# l'image est lancée seule (docker run) ou par un hébergeur qui exécute la commande par défaut.
# Les migrations ne sont pas lancées ici : à faire une fois par déploiement, pas à chaque conteneur.
set -e

python manage.py collectstatic --noinput

exec daphne -b 0.0.0.0 -p "${PORT:-8000}" config.asgi:application
