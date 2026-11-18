# Déployer CSTV sur Render

## Ce qui fonctionne et ce qui ne fonctionne pas

- ✅ Catalogue de films, upload/transcodage vidéo, sous-titres, "Ma liste", historique de
  visionnage, recommandations, publicités pre-roll, communauté, messagerie, notifications, CMS.
- ❌ **Le direct (RTMP)** ne peut pas être ingéré par Render : ça ne supporte que le HTTP/HTTPS, pas
  le port TCP brut (1935) dont OBS/Wirecast ont besoin. Pour activer le direct plus tard, héberge
  MediaMTX sur un petit VPS externe et renseigne `RTMP_INGEST_BASE_URL` /
  `MEDIAMTX_HLS_INTERNAL_URL` avec son adresse. Tout le reste du site fonctionne sans ça.

## Architecture choisie

Web (Daphne) et worker Celery (transcodage vidéo) tournent **dans le même service Render**
(`cstv-api`), pas dans deux services séparés comme en docker-compose. Raison : Render ne permet pas
à deux services de partager un disque persistant, or le worker écrit les vidéos transcodées sur
disque et le web les sert — ils doivent voir les mêmes fichiers. Voir
`docker/render/start-combined.sh`. Limite acceptée : web et worker ne scalent pas indépendamment
(largement suffisant pour démarrer ; à revoir plus tard si besoin avec un stockage S3).

Pas de Celery Beat déployé : aucune tâche périodique n'est actuellement planifiée
(`CELERY_BEAT_SCHEDULE` est vide). Si tu en ajoutes une plus tard, il faudra un service
Background Worker supplémentaire pour `celery -A config beat`.

## Étapes

1. **Créer le blueprint** : sur [render.com](https://dashboard.render.com), "New" → "Blueprint",
   connecte le dépôt GitHub `cfruit294-web/cstv26`. Render lit `render.yaml` à la racine et propose
   de créer : `cstv-db` (Postgres), `cstv-redis`, `cstv-api`, `cstv-frontend`.

2. **Renseigner les variables manuelles** (marquées `sync: false` dans `render.yaml`, vides par
   défaut) sur le service `cstv-api`, dans l'onglet Environment :
   - `OMDB_API_KEY` — uniquement si tu veux aussi pouvoir importer des fiches depuis OMDb (pas
     obligatoire, tu ajoutes déjà tes films à la main).
   - `EMAIL_HOST` / `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` / `DEFAULT_FROM_EMAIL` — pour que les
     emails (vérification de compte, réinitialisation de mot de passe) partent vraiment. Sans ça,
     `EMAIL_BACKEND` reste sur la console (les emails s'affichent dans les logs, personne ne les
     reçoit).

3. **Lancer le déploiement.** Render construit les images Docker (`Dockerfile` et
   `frontend/Dockerfile`), crée la base et Redis, démarre les services. Ça prend quelques minutes
   la première fois.

4. **Vérifier les URLs réellement attribuées.** Si les noms `cstv-api`/`cstv-frontend` sont déjà
   pris par quelqu'un d'autre sur Render, il ajoute un suffixe (ex: `cstv-api-a1b2.onrender.com`).
   Regarde les vraies URLs dans le dashboard, et si elles diffèrent de celles codées dans
   `render.yaml` (`CORS_ALLOWED_ORIGINS`, `FRONTEND_URL` sur `cstv-api` ; `NEXT_PUBLIC_API_URL` sur
   `cstv-frontend`), corrige-les dans l'onglet Environment de chaque service puis redéploie
   ("Manual Deploy").

5. **Créer un compte admin** : dans le dashboard Render, ouvre le "Shell" du service `cstv-api` et
   lance :
   ```
   python manage.py createsuperuser
   ```

6. **Ajouter un film** : va sur `https://<ton-url-cstv-api>/admin/`, connecte-toi, puis suis la
   section "Ajouter un film manuellement (sans OMDb)" du `README.md`.

## Coûts

Le plan `starter` est nécessaire pour `cstv-api` et `cstv-frontend` (le disque persistant n'existe
pas sur le plan gratuit, et un service gratuit s'endort après inactivité — incompatible avec un
worker Celery qui doit rester actif). `cstv-db` et `cstv-redis` sont sur le plan gratuit par défaut
dans `render.yaml` — vérifie les conditions actuelles sur render.com (le Postgres gratuit expire
généralement au bout de quelques semaines/mois selon les CGU du moment) avant de considérer le site
comme prêt pour de vrais utilisateurs sur la durée.
