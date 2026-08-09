# CSTV

Plateforme de streaming vidéo (Django + DRF + PostgreSQL + Redis + Celery).

Développement module par module. **Modules livrés :**
- `core` + `accounts` — authentification complète (inscription, vérification email, login JWT, refresh avec rotation/blacklist, logout, reset password, 2FA TOTP, gestion des sessions/appareils, rôles)
- `catalog` — métadonnées films/séries importées depuis l'API OMDb
- `videos` — upload vidéo, transcodage HLS multi-résolution (1080p/720p/480p/360p) via FFmpeg + Celery, miniature automatique
- `subscriptions` — formules d'abonnement (Basic/Premium/VIP/Entreprise), essai gratuit, cycle de facturation
- `payments` — paiement CinetPay (Orange Money, MTN, Wave, cartes locales), webhook de confirmation
- `live` — planification de lives, clé de stream, webhook RTMP (ingestion externe), chat temps réel (Django Channels/WebSocket)
- `products` — boutique (produits numériques et physiques, catégories, gestion du vendeur)
- `orders` — commandes, paiement CinetPay lié, gestion du stock, téléchargement digital gated
- `community` — publications, commentaires, likes
- `messaging` — conversations privées, messages temps réel (WebSocket), indicateur de saisie, présence
- `dashboard` — statistiques agrégées (utilisateurs, revenus, contenu) réservées aux admins
- `notifications` — notifications in-app persistées + push temps réel (WebSocket), intégrées à `community` (commentaire) et `orders` (commande payée)
- `search` — recherche globale (contenu public) à travers films, vidéos, produits, lives, publications
- `cms` — pages éditoriales (landing, blog, FAQ, mentions légales/CGU), `sitemap.xml`, `robots.txt`

## Démarrage rapide (développement local, sans Docker)

```bash
python -m venv .venv
.venv/Scripts/activate        # Windows
pip install -r requirements/dev.txt
cp .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

- API : http://localhost:8000/api/v1/
- Admin : http://localhost:8000/admin/
- Documentation Swagger : http://localhost:8000/api/docs/
- Health check : http://localhost:8000/api/v1/health/

## Tests

```bash
python manage.py test
```

FFmpeg doit être installé et sur le `PATH` (`ffmpeg`/`ffprobe`) pour un traitement vidéo réel ; les tests automatisés du module `videos` mockent FFmpeg et ne nécessitent pas son installation. L'image Docker l'installe déjà (`apt-get install ffmpeg`).

## Démarrage avec Docker (production-like)

```bash
cp .env.example .env   # renseigner SECRET_KEY, DB_*, etc.
docker compose up --build
```

Services : `web` (Daphne, sert HTTP + WebSocket), `db` (PostgreSQL), `redis`, `celery_worker`, `celery_beat`, `nginx`.

> Non testé dans cet environnement (Docker non installé ici) — à valider sur une machine avec Docker avant déploiement.

### Live streaming : ce qui est inclus / pas inclus

Ce module gère la **planification, l'authentification RTMP (clé de stream) et le chat temps réel**, mais **n'embarque pas de serveur média RTMP**. Pour une ingestion réelle, ajouter un service comme `nginx-rtmp-module` ou `MediaMTX` au `docker-compose.yml`, configuré pour appeler `POST /api/v1/live/webhook/rtmp/` (avec `secret=RTMP_WEBHOOK_SECRET`) sur les événements `on_publish` / `on_publish_done`. Le champ `rtmp_ingest_url` (visible du propriétaire/admin uniquement) indique où l'streamer doit pousser son flux (OBS Studio, etc.), et `hls_playback_url` où le lire une fois live.

## Endpoints `accounts` disponibles

| Méthode | URL | Description |
|---|---|---|
| POST | `/api/v1/accounts/register/` | Inscription |
| POST | `/api/v1/accounts/verify-email/` | Confirmation d'email |
| POST | `/api/v1/accounts/verify-email/resend/` | Renvoi du lien de confirmation |
| POST | `/api/v1/accounts/login/` | Connexion (retourne les tokens ou demande la 2FA) |
| POST | `/api/v1/accounts/login/2fa/` | Validation du code 2FA |
| POST | `/api/v1/accounts/logout/` | Déconnexion (blacklist du refresh token) |
| POST | `/api/v1/accounts/token/refresh/` | Rafraîchissement du token |
| GET/PATCH | `/api/v1/accounts/me/` | Profil courant |
| POST | `/api/v1/accounts/password/change/` | Changement de mot de passe |
| POST | `/api/v1/accounts/password/reset/` | Demande de réinitialisation |
| POST | `/api/v1/accounts/password/reset/confirm/` | Confirmation de réinitialisation |
| POST | `/api/v1/accounts/2fa/enable/` | Initialisation de la 2FA |
| POST | `/api/v1/accounts/2fa/enable/confirm/` | Activation de la 2FA |
| POST | `/api/v1/accounts/2fa/disable/` | Désactivation de la 2FA |
| GET | `/api/v1/accounts/sessions/` | Liste des appareils connectés |
| POST | `/api/v1/accounts/sessions/<id>/revoke/` | Révocation d'une session |

## Endpoints `catalog` disponibles

| Méthode | URL | Description | Accès |
|---|---|---|---|
| GET | `/api/v1/catalog/omdb/search/?q=...` | Recherche live sur OMDb (aucune écriture) | Authentifié |
| POST | `/api/v1/catalog/movies/import/` | Importe/MAJ une fiche (`imdb_id` ou `title`) | admin/modérateur/créateur |
| GET | `/api/v1/catalog/movies/` | Parcourt le catalogue local (`?q=` filtre le titre) | Authentifié |
| GET | `/api/v1/catalog/movies/<id>/` | Détail d'une fiche | Authentifié |

## Endpoints `videos` disponibles

| Méthode | URL | Description | Accès |
|---|---|---|---|
| POST | `/api/v1/videos/upload/` | Upload d'une vidéo source, déclenche le transcodage HLS | admin/modérateur/créateur |
| GET | `/api/v1/videos/` | Liste ses propres vidéos + vidéos publiques prêtes des autres | Authentifié |
| GET | `/api/v1/videos/<id>/` | Détail (propriétaire/admin : tout ; autres : public + prêt uniquement) | Authentifié |
| DELETE | `/api/v1/videos/<id>/` | Suppression (propriétaire/admin uniquement) | Authentifié |
| POST | `/api/v1/videos/<id>/retry/` | Relance le traitement (ex. après échec) | Propriétaire/admin |

## Endpoints `subscriptions` disponibles

| Méthode | URL | Description | Accès |
|---|---|---|---|
| GET | `/api/v1/subscriptions/plans/` | Catalogue public des formules actives | Public |
| GET/POST | `/api/v1/subscriptions/plans/admin/` | Gestion des formules | Admin |
| GET/PATCH/DELETE | `/api/v1/subscriptions/plans/admin/<id>/` | Détail/édition d'une formule | Admin |
| POST | `/api/v1/subscriptions/subscribe/` | Souscrit à une formule (`plan_id`) | Authentifié |
| GET | `/api/v1/subscriptions/me/` | Abonnement courant | Authentifié |
| POST | `/api/v1/subscriptions/cancel/` | Annule le renouvellement automatique | Authentifié |

## Endpoints `payments` disponibles

| Méthode | URL | Description | Accès |
|---|---|---|---|
| POST | `/api/v1/payments/checkout/` | Initie le paiement CinetPay de l'abonnement en attente | Authentifié |
| POST | `/api/v1/payments/cinetpay/notify/` | Callback serveur-à-serveur CinetPay | Public (CinetPay) |
| GET | `/api/v1/payments/` | Historique de paiements | Authentifié (les siens ; admin : tous) |
| GET | `/api/v1/payments/<id>/` | Détail d'un paiement | Propriétaire/admin |

> `CINETPAY_API_KEY`/`CINETPAY_SITE_ID` sont vides par défaut — `checkout` renvoie une 502 explicite tant qu'ils ne sont pas renseignés dans `.env`. Aucune clé CinetPay réelle n'a été fournie pour ce module ; l'intégration est testée avec l'API mockée.

## Endpoints `live` disponibles

| Méthode | URL | Description | Accès |
|---|---|---|---|
| POST | `/api/v1/live/streams/create/` | Planifie un live (génère la clé de stream) | admin/modérateur/créateur |
| GET | `/api/v1/live/streams/` | Liste ses lives + lives publics des autres | Authentifié |
| GET | `/api/v1/live/streams/<id>/` | Détail (clé/URL RTMP visibles du propriétaire/admin uniquement) | Authentifié |
| POST | `/api/v1/live/streams/<id>/start/` | Démarre manuellement (normalement piloté par le webhook RTMP) | Propriétaire/admin |
| POST | `/api/v1/live/streams/<id>/end/` | Termine manuellement | Propriétaire/admin |
| GET | `/api/v1/live/streams/<id>/chat/` | Historique du chat | Authentifié (accès public/propriétaire/admin) |
| POST | `/api/v1/live/webhook/rtmp/` | Callback du serveur média RTMP externe | Public (secret partagé) |
| WS | `/ws/live/<id>/chat/?token=<access_jwt>` | Chat temps réel (JWT en query string) | Authentifié (accès public/propriétaire/admin) |

## Endpoints `products` disponibles

| Méthode | URL | Description | Accès |
|---|---|---|---|
| GET | `/api/v1/products/categories/` | Liste des catégories | Public |
| GET/POST | `/api/v1/products/categories/admin/` | Gestion des catégories | Admin |
| GET | `/api/v1/products/` | Catalogue public (`?category=`, `?type=`, `?q=`) | Public |
| GET | `/api/v1/products/mine/` | Ses propres produits (actifs et inactifs) | admin/créateur/entreprise |
| POST | `/api/v1/products/create/` | Crée un produit | admin/créateur/entreprise |
| GET | `/api/v1/products/<id>/` | Détail public | Public |
| GET/PATCH/DELETE | `/api/v1/products/<id>/manage/` | Édition/suppression | Propriétaire/admin |

## Endpoints `orders` disponibles

| Méthode | URL | Description | Accès |
|---|---|---|---|
| POST | `/api/v1/orders/create/` | Crée une commande (`items: [{product_id, quantity}]`) | Authentifié |
| GET | `/api/v1/orders/` | Historique de commandes | Authentifié (les siennes ; admin : toutes) |
| GET | `/api/v1/orders/<id>/` | Détail d'une commande | Propriétaire/admin |
| POST | `/api/v1/orders/<id>/checkout/` | Initie le paiement CinetPay de la commande | Propriétaire |
| GET | `/api/v1/orders/<id>/download/<product_id>/` | URL de téléchargement (commande payée uniquement) | Propriétaire |

## Endpoints `community` disponibles

| Méthode | URL | Description | Accès |
|---|---|---|---|
| GET/POST | `/api/v1/community/posts/` | Fil de publications / créer une publication | Public (lecture) / Authentifié (écriture) |
| GET/DELETE | `/api/v1/community/posts/<id>/` | Détail / suppression | Auteur/modérateur/admin (suppression) |
| GET/POST | `/api/v1/community/posts/<id>/comments/` | Commentaires d'une publication | Authentifié |
| DELETE | `/api/v1/community/comments/<id>/` | Suppression d'un commentaire | Auteur/modérateur/admin |
| POST | `/api/v1/community/posts/<id>/like/` | Bascule like/unlike | Authentifié |

## Endpoints `messaging` disponibles

| Méthode | URL | Description | Accès |
|---|---|---|---|
| GET/POST | `/api/v1/messaging/conversations/` | Liste ses conversations / en crée une (`participant_ids`) | Authentifié |
| GET/POST | `/api/v1/messaging/conversations/<id>/messages/` | Historique / envoi (fallback REST) | Participant |
| POST | `/api/v1/messaging/conversations/<id>/read/` | Marque tous les messages comme lus | Participant |
| WS | `/ws/messaging/<id>/?token=<access_jwt>` | Messages temps réel, `{"type":"typing"}`, présence en ligne | Participant |

## Endpoints `dashboard` disponibles

| Méthode | URL | Description | Accès |
|---|---|---|---|
| GET | `/api/v1/dashboard/overview/` | Statistiques agrégées (utilisateurs, revenus, contenu) | Admin |

## Endpoints `notifications` disponibles

| Méthode | URL | Description | Accès |
|---|---|---|---|
| GET | `/api/v1/notifications/` | Liste ses notifications (`?unread=true` filtre) | Authentifié |
| GET | `/api/v1/notifications/unread-count/` | Nombre de notifications non lues | Authentifié |
| POST | `/api/v1/notifications/<id>/read/` | Marque une notification comme lue | Authentifié |
| POST | `/api/v1/notifications/read-all/` | Marque toutes les notifications comme lues | Authentifié |
| WS | `/ws/notifications/?token=<access_jwt>` | Push temps réel des nouvelles notifications | Authentifié |

## Endpoints `search` disponibles

| Méthode | URL | Description | Accès |
|---|---|---|---|
| GET | `/api/v1/search/?q=...` | Recherche globale (films, vidéos, produits, lives, publications — contenu public uniquement) | Public |

## Endpoints `cms` disponibles

| Méthode | URL | Description | Accès |
|---|---|---|---|
| GET | `/api/v1/cms/pages/?type=...` | Pages publiées | Public |
| GET | `/api/v1/cms/pages/<slug>/` | Détail d'une page publiée | Public |
| GET/POST | `/api/v1/cms/pages/admin/` | Gestion des pages (brouillons inclus) | Admin/modérateur |
| GET/PATCH/DELETE | `/api/v1/cms/pages/admin/<id>/` | Détail/édition/suppression | Admin/modérateur |
| GET | `/sitemap.xml` | Sitemap des pages publiées | Public |
| GET | `/robots.txt` | Directives robots + lien vers le sitemap | Public |

## Prochains modules (à venir, un par un)

`marketing` (newsletter, campagnes) → `analytics` (rapports détaillés) → `security` (audit, rate limiting avancé) → applications mobiles (API déjà REST-first) → ...
