"""Sert des fichiers média protégés après vérification des droits par l'appelant.

Trois modes, du plus simple au plus scalable :
- Stockage local sans nginx (dev) : Django lit et renvoie le fichier lui-même.
- Stockage local derrière nginx (USE_X_ACCEL_REDIRECT=True, cf docker-compose.yml) : délègue via
  X-Accel-Redirect, nginx sert le fichier depuis la location interne `/internal-media/` (jamais
  atteignable de l'extérieur) — bien plus efficace pour de gros fichiers vidéo.
- Stockage S3-compatible (AWS_STORAGE_BUCKET_NAME défini) : redirige (302) vers une URL signée
  très courte durée. Le bucket reste privé ; seul celui qui a passé le contrôle d'accès obtient
  une URL, et elle expire vite (MEDIA_SIGNED_URL_EXPIRE).
"""
import mimetypes
from pathlib import Path

from django.conf import settings
from django.core.files.storage import default_storage
from django.http import FileResponse, Http404, HttpResponse, HttpResponseRedirect

from core.storage import is_local_storage, safe_media_name


def resolve_within(root, relative_path):
    """Résout `relative_path` sous `root` en bloquant toute tentative de traversée (`..`, chemin absolu)."""
    root = Path(root).resolve()
    target = (root / relative_path).resolve()
    try:
        target.relative_to(root)
    except ValueError:
        raise Http404
    return target


def _content_disposition(download_name):
    return f'attachment; filename="{download_name}"'


def serve_protected_media(relative_path, download_name=None, content_type=None):
    """relative_path : nom dans le stockage média (ex: 'hls/<id>/master.m3u8')."""
    content_type = content_type or mimetypes.guess_type(relative_path)[0] or 'application/octet-stream'

    if not is_local_storage():
        return _redirect_to_signed_url(relative_path, download_name, content_type)

    absolute_path = resolve_within(settings.MEDIA_ROOT, relative_path)
    if not absolute_path.is_file():
        raise Http404

    if settings.USE_X_ACCEL_REDIRECT:
        response = HttpResponse(content_type=content_type)
        response['X-Accel-Redirect'] = f'/internal-media/{relative_path}'
    else:
        response = FileResponse(open(absolute_path, 'rb'), content_type=content_type)
    if download_name:
        response['Content-Disposition'] = _content_disposition(download_name)
    return response


def _redirect_to_signed_url(relative_path, download_name, content_type):
    # Même garde anti-traversée que resolve_within, mais sur des clés de stockage.
    head, _, tail = relative_path.partition('/')
    name = safe_media_name(head, tail) if tail else None
    if not name or name != relative_path:
        raise Http404

    # Pas de exists() ici : ce serait une requête HEAD vers S3 en plus pour CHAQUE segment vidéo.
    # Une clé absente renvoie simplement une erreur côté S3 au moment du suivi de la redirection.
    parameters = {'ResponseContentType': content_type}
    if download_name:
        parameters['ResponseContentDisposition'] = _content_disposition(download_name)
    url = default_storage.url(name, parameters=parameters, expire=settings.MEDIA_SIGNED_URL_EXPIRE)

    response = HttpResponseRedirect(url)
    # La redirection contient une URL signée : elle ne doit pas être réutilisée après expiration.
    response['Cache-Control'] = 'private, no-store'
    return response
