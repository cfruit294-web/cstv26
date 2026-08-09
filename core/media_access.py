"""Sert des fichiers sous MEDIA_ROOT après vérification des droits par l'appelant.

En dev (DEBUG, pas de nginx devant runserver) : lit le fichier directement.
En prod (derrière nginx) : délègue via X-Accel-Redirect, nginx sert le fichier
depuis la location interne `/internal-media/` (jamais atteignable de l'extérieur).
"""
import mimetypes
from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404, HttpResponse


def resolve_within(root, relative_path):
    """Résout `relative_path` sous `root` en bloquant toute tentative de traversée (`..`, chemin absolu)."""
    root = Path(root).resolve()
    target = (root / relative_path).resolve()
    try:
        target.relative_to(root)
    except ValueError:
        raise Http404
    return target


def serve_protected_media(relative_path, download_name=None, content_type=None):
    """relative_path : chemin relatif à MEDIA_ROOT (ex: 'hls/<id>/master.m3u8')."""
    absolute_path = resolve_within(settings.MEDIA_ROOT, relative_path)
    if not absolute_path.is_file():
        raise Http404

    content_type = content_type or mimetypes.guess_type(str(absolute_path))[0] or 'application/octet-stream'

    if settings.DEBUG:
        response = FileResponse(open(absolute_path, 'rb'), content_type=content_type)
        if download_name:
            response['Content-Disposition'] = f'attachment; filename="{download_name}"'
        return response

    response = HttpResponse(content_type=content_type)
    response['X-Accel-Redirect'] = f'/internal-media/{relative_path}'
    if download_name:
        response['Content-Disposition'] = f'attachment; filename="{download_name}"'
    return response
