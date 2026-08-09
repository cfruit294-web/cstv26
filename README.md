# CSTV

Plateforme de streaming vidéo, entièrement gratuite (Django + DRF + PostgreSQL + Redis + Celery pour l'API, Next.js pour le frontend).

**Modules backend livrés :**
- `core` + `accounts` — authentification complète (inscription, vérification email, login JWT, refresh avec rotation/blacklist, logout, reset password, 2FA TOTP, gestion des sessions/appareils, rôles)
- `catalog` — métadonnées films/séries. Peuplé soit par import OMDb (`movies/import/`), soit **entièrement à la main depuis l'admin** (voir « Ajouter un film manuellement » ci-dessous) — les deux se combinent, aucun des deux n'est obligatoire.
- `videos` — upload vidéo (via l'admin ou l'API), transcodage HLS multi-résolution (1080p/720p/480p/360p) via FFmpeg + Celery, miniature automatique, sous-titres WebVTT (FR/EN)
- `live` — planification de lives, clé de stream, webhook RTMP (ingestion externe), chat temps réel (Django Channels/WebSocket)
- `watchparty` — visionnage synchronisé entre amis (hôte/modérateurs/membres, chat, lecture synchronisée en WebSocket)
- `library` — « Ma liste » (watchlist) et historique de visionnage (reprise automatique de lecture)
- `ads` — publicités pre-roll (vidéo ou image) gérées depuis l'admin, diffusées avant la lecture d'un film
- `community` — publications, commentaires, likes
- `messaging` — conversations privées, messages temps réel (WebSocket), indicateur de saisie, présence
- `dashboard` — statistiques agrégées (utilisateurs, contenu) réservées aux admins
- `notifications` — notifications in-app persistées + push temps réel (WebSocket)
- `search` — recherche globale (contenu public) à travers films, vidéos, lives, publications
- `cms` — pages éditoriales (landing, blog, FAQ, mentions légales/CGU), `sitemap.xml`, `robots.txt`

**Frontend :** `frontend/` — Next.js (App Router, TypeScript, Tailwind), consomme l'API ci-dessus. Voir `frontend/README.md`.

## Ajouter un film manuellement (sans OMDb)

Le catalogue n'a pas besoin de l'API OMDb pour fonctionner. Depuis `/admin/` :

1. **Catalog → Movies → Add** : renseigne le titre, l'année, le genre, les acteurs, etc. `imdb_id` doit juste être une valeur unique (ex. `local-001`) — ce n'est pas vérifié contre une vraie base IMDb.
2. **Videos → Videos → Add** : sélectionne le film créé à l'étape 1 dans le champ `movie`, choisis un propriétaire (`owner`), une visibilité, et uploade le fichier `.mp4` dans `source_file`. Le transcodage HLS se lance automatiquement à l'enregistrement (que ce soit un ajout ou un remplacement du fichier) — inutile de passer par l'API.
3. Optionnel : ajoute des sous-titres `.vtt` (FR/EN) directement en inline sur la fiche vidéo.

Le film apparaît ensuite dans le catalogue public dès que la vidéo passe au statut `ready` (transcodage terminé).

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

> Configuration validée (`docker compose config`, build des images), mais un `docker compose up` complet de bout en bout n'a pas été exécuté dans cet environnement — à valider avant déploiement.

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
| GET | `/api/v1/catalog/movies/<id>/recommendations/` | Films similaires (genre/acteurs partagés) | Public |

## Endpoints `videos` disponibles

| Méthode | URL | Description | Accès |
|---|---|---|---|
| POST | `/api/v1/videos/upload/` | Upload d'une vidéo source, déclenche le transcodage HLS | admin/modérateur/créateur |
| GET | `/api/v1/videos/` | Liste ses propres vidéos + vidéos publiques prêtes des autres | Authentifié |
| GET | `/api/v1/videos/<id>/` | Détail (propriétaire/admin : tout ; autres : public + prêt uniquement) | Authentifié |
| DELETE | `/api/v1/videos/<id>/` | Suppression (propriétaire/admin uniquement) | Authentifié |
| POST | `/api/v1/videos/<id>/retry/` | Relance le traitement (ex. après échec) | Propriétaire/admin |
| POST | `/api/v1/videos/<id>/subtitles/` | Ajoute une piste de sous-titres `.vtt` (fr/en) | Propriétaire/admin |
| DELETE | `/api/v1/videos/subtitles/<id>/` | Supprime une piste de sous-titres | Propriétaire/admin |

## Endpoints `library` disponibles

| Méthode | URL | Description | Accès |
|---|---|---|---|
| GET | `/api/v1/library/watchlist/` | Films dans « Ma liste » | Authentifié |
| POST | `/api/v1/library/watchlist/toggle/` | Ajoute/retire un film (`movie_id`) | Authentifié |
| GET | `/api/v1/library/watchlist/status/<movie_id>/` | Le film est-il dans la liste ? | Authentifié |
| POST | `/api/v1/library/history/` | Sauvegarde la position de lecture (`video`, `position_seconds`) | Authentifié |
| GET | `/api/v1/library/history/<video_id>/` | Position sauvegardée (0 si aucune) | Authentifié |

## Endpoints `ads` disponibles

| Méthode | URL | Description | Accès |
|---|---|---|---|
| GET | `/api/v1/ads/next/?placement=pre_roll` | Publicité active au hasard pour l'emplacement (204 si aucune) | Public |

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

## Endpoints `watchparty` disponibles

| Méthode | URL | Description | Accès |
|---|---|---|---|
| GET | `/api/v1/watchparty/suggestions/` | Vidéos suggérées pour créer une session | Authentifié |
| GET/POST | `/api/v1/watchparty/parties/` | Liste ses sessions / en crée une | Authentifié |
| GET | `/api/v1/watchparty/parties/<id>/` | Détail d'une session | Membre/hôte/admin |
| POST | `/api/v1/watchparty/parties/<id>/join/` | Rejoindre (en attente de validation selon le mode) | Authentifié |
| POST | `/api/v1/watchparty/parties/<id>/start/` \| `/end/` \| `/cancel/` | Contrôle du cycle de vie | Hôte/modérateur |
| GET | `/api/v1/watchparty/parties/<id>/chat/` | Historique du chat | Membre |
| GET | `/api/v1/watchparty/parties/<id>/members/` | Liste des membres | Membre |
| POST | `.../members/<id>/accept/` \| `/reject/` \| `/promote/` | Gestion des membres | Hôte/modérateur |
| WS | `/ws/watchparty/<id>/?token=<access_jwt>` | Lecture synchronisée + chat temps réel | Membre |

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
| GET | `/api/v1/dashboard/overview/` | Statistiques agrégées (utilisateurs, contenu) | Admin |

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
| GET | `/api/v1/search/?q=...` | Recherche globale (films, vidéos, lives, publications — contenu public uniquement) | Public |

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
