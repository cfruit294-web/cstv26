# Déployer CSTV sur un VPS

Tout tourne avec Docker sur un seul serveur : Postgres, Redis, Django (web), le worker Celery
(transcodage vidéo), Celery Beat, Next.js, MediaMTX (direct RTMP), nginx, et **Caddy** devant le
tout pour le HTTPS automatique (certificat Let's Encrypt obtenu et renouvelé tout seul).

```
Internet ──443──> Caddy (HTTPS) ──> nginx ──┬─> Next.js        (pages du site)
                                            ├─> Django/Daphne  (/api, /admin, /ws, vidéos protégées)
                                            └─> MediaMTX HLS   (/hls, lecture des lives)
OBS ─────1935──> MediaMTX (ingestion RTMP du direct)
```

Tout fonctionne, **direct compris** (contrairement à un hébergeur PaaS, un VPS ouvre le port RTMP).

## 1. Choisir le serveur

- **Système** : Ubuntu 24.04 LTS.
- **Taille minimale conseillée** : 2 vCPU, 4 Go de RAM, 80 Go de disque. Le transcodage ffmpeg est
  gourmand en CPU : plus de vCPU = vidéos prêtes plus vite.
- Exemples : Hetzner (CX32/CPX31), OVH, DigitalOcean, Contabo. Vérifie que le trafic sortant
  inclus est large (la vidéo en consomme beaucoup).

## 2. Faire pointer le domaine

Chez ton registrar (ou Cloudflare DNS), crée un enregistrement **A** : `cstv.ton-domaine.com` →
l'adresse IPv4 du VPS. Si tu utilises Cloudflare, mets le nuage en **gris (DNS only)** au moins
pour le premier lancement, sinon Caddy ne peut pas obtenir le certificat.

Attends que `ping cstv.ton-domaine.com` renvoie bien l'IP du VPS avant l'étape 5.

## 3. Préparer le serveur

Connecte-toi en SSH (`ssh root@IP_DU_VPS`), puis :

```bash
# Docker + Docker Compose (script officiel)
curl -fsSL https://get.docker.com | sh

# Pare-feu : SSH, HTTP/HTTPS (Caddy) et RTMP (direct)
ufw allow 22/tcp && ufw allow 80/tcp && ufw allow 443/tcp && ufw allow 443/udp && ufw allow 1935/tcp
ufw --force enable
```

Note : Docker contourne ufw pour les ports qu'il publie. Seuls Caddy (80/443) et MediaMTX (1935)
publient des ports ; Postgres, Redis, Django et nginx restent sur le réseau Docker interne.

## 4. Récupérer le code et configurer

```bash
git clone https://github.com/<compte>/<depot>.git /opt/cstv
cd /opt/cstv
cp .env.production.example .env
nano .env
```

Dans `.env`, remplace chaque `CHANGE-ME` :
- `DOMAIN`, `ALLOWED_HOSTS`, `NEXT_PUBLIC_API_URL`, `FRONTEND_URL`, `CORS_ALLOWED_ORIGINS`,
  `RTMP_INGEST_BASE_URL` : ton domaine.
- `SECRET_KEY`, `DB_PASSWORD`, `RTMP_WEBHOOK_SECRET` : trois valeurs aléatoires différentes,
  générées avec `openssl rand -hex 32`.
- Emails (optionnel) : `EMAIL_HOST`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL`.
  Sans ça, remets `EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend` : les emails
  n'apparaîtront que dans les logs.

`.env` ne doit jamais être commité (il est dans `.gitignore`).

## 5. Lancer

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

Le premier build prend plusieurs minutes. Ensuite :

```bash
# État des conteneurs (tous doivent être "running" / "healthy")
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps

# Logs de Caddy : doit indiquer "certificate obtained successfully"
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs caddy

# Créer le compte administrateur
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec web python manage.py createsuperuser
```

Puis ouvre `https://cstv.ton-domaine.com` (site) et `https://cstv.ton-domaine.com/admin/`.

Astuce : pour ne pas retaper les `-f`, ajoute dans `.env` la ligne
`COMPOSE_FILE=docker-compose.yml:docker-compose.prod.yml`, ensuite `docker compose up -d` suffit.

## 6. Mettre à jour après un changement de code

```bash
cd /opt/cstv
git pull
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

Les migrations de base de données sont appliquées automatiquement au démarrage du conteneur `web`.

## 7. Sauvegardes (à mettre en place dès le début)

Base de données, chaque nuit à 3h, 14 jours conservés (`crontab -e` sur le VPS) :

```cron
0 3 * * * cd /opt/cstv && docker compose exec -T db pg_dump -U cstv cstv | gzip > /root/backup-cstv-$(date +\%F).sql.gz && find /root -name 'backup-cstv-*.sql.gz' -mtime +14 -delete
```

Copie régulièrement ces fichiers **hors du serveur** (sinon une panne du VPS emporte tout). Les
vidéos sont dans le volume Docker `media_volume` : à sauvegarder aussi, ou passe au stockage S3
(section suivante), qui les met hors du serveur.

## Stockage des vidéos : disque du VPS ou bucket S3

Par défaut, les vidéos sont sur le disque du VPS (volume `media_volume`), servies par nginx après
vérification des droits par Django. C'est le plus simple pour démarrer.

Quand le disque devient trop petit, passe sur un bucket S3-compatible : **Cloudflare R2** est
recommandé (bande passante sortante gratuite). Crée un bucket **privé** avec une clé d'API limitée
à ce bucket, ajoute ce CORS au bucket :

```json
[{ "AllowedOrigins": ["*"], "AllowedMethods": ["GET", "HEAD"], "AllowedHeaders": ["*"], "MaxAgeSeconds": 3600 }]
```

(`"*"` est nécessaire et sans risque : le navigateur suit une redirection site → bucket et envoie
alors `Origin: null` ; la protection, ce sont les URLs signées qui expirent en 5 minutes.)

Puis renseigne dans `.env` : `AWS_STORAGE_BUCKET_NAME`, `AWS_ACCESS_KEY_ID`,
`AWS_SECRET_ACCESS_KEY`, `AWS_S3_REGION_NAME=auto`,
`AWS_S3_ENDPOINT_URL=https://<account_id>.r2.cloudflarestorage.com`, et relance (étape 6).
Les vidéos déjà sur le disque ne sont pas déplacées automatiquement.

## Le direct (OBS / Wirecast)

Dans l'admin, chaque LiveStream affiche son URL d'ingestion (`rtmp://cstv.ton-domaine.com/...`)
et sa clé. Dans OBS : Paramètres → Stream → Service "Personnalisé", colle l'URL et la clé.

## Limite connue

Supprimer une vidéo ne supprime pas (encore) ses fichiers (source, HLS, miniature) du disque ou du
bucket : ils restent et occupent de la place.
