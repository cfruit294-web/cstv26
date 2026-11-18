#!/bin/bash
# `wait -n` (attendre qu'UN des deux jobs se termine) n'existe qu'en bash, pas en sh/dash.
# Point d'entrée pour un hébergeur à service unique (ex: Render) qui ne permet pas de partager un
# disque entre plusieurs services : le worker Celery (transcodage vidéo) et le serveur web tournent
# ici dans le même conteneur, donc sur le même disque. Sur docker-compose (nginx, disque partagé
# entre plusieurs conteneurs), ce script n'est pas utilisé : chaque service garde sa propre commande.
set -e

python manage.py migrate --noinput
python manage.py collectstatic --noinput

celery -A config worker -l info &
WORKER_PID=$!

daphne -b 0.0.0.0 -p "${PORT:-8000}" config.asgi:application &
WEB_PID=$!

# Si l'un des deux meurt, on arrête tout : l'hébergeur redémarre alors le conteneur en entier,
# plutôt que de continuer à tourner à moitié (web up, worker mort, ou l'inverse) sans le savoir.
wait -n "$WORKER_PID" "$WEB_PID"
exit $?
