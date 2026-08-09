import logging
from pathlib import Path

from celery import shared_task
from django.conf import settings
from django.core.files import File

from live.models import LiveStream
from videos.models import Video
from videos.tasks import process_video

logger = logging.getLogger(__name__)

# Visibilité du live -> visibilité de la vidéo de rediffusion générée.
_VISIBILITY_MAP = {
    LiveStream.Visibility.PUBLIC: Video.Visibility.PUBLIC,
    LiveStream.Visibility.PRIVATE: Video.Visibility.PRIVATE,
    LiveStream.Visibility.PREMIUM: Video.Visibility.PREMIUM,
}


def _find_recording(stream_key):
    """Cherche le fichier enregistré par MediaMTX pour ce stream (peu importe le préfixe d'app RTMP configuré)."""
    root = Path(settings.LIVE_RECORDINGS_ROOT)
    if not root.is_dir():
        return None

    candidates = [
        path for path in root.rglob('*')
        if path.is_file() and path.suffix.lower() in ('.mp4', '.ts', '.mkv') and stream_key in path.parts
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


@shared_task
def create_replay_from_stream(stream_id):
    """À la fin d'un live, récupère l'enregistrement MediaMTX et le transforme en vidéo de rediffusion.

    Ne fait rien (silencieusement) si aucun enregistrement n'est trouvé : soit MediaMTX n'est pas
    configuré pour enregistrer, soit ce live n'a jamais été réellement diffusé.
    """
    try:
        stream = LiveStream.objects.get(id=stream_id)
    except LiveStream.DoesNotExist:
        return

    if stream.replay_video_id:
        return

    recording_path = _find_recording(stream.stream_key)
    if not recording_path:
        logger.info('Aucun enregistrement trouvé pour le live %s (clé %s).', stream.id, stream.stream_key)
        return

    video = Video(
        owner=stream.owner,
        title=f'Rediffusion — {stream.title}',
        description=stream.description,
        visibility=_VISIBILITY_MAP.get(stream.visibility, Video.Visibility.PRIVATE),
    )
    with recording_path.open('rb') as fh:
        video.source_file.save(recording_path.name, File(fh), save=True)

    stream.replay_video = video
    stream.save(update_fields=['replay_video'])

    recording_path.unlink(missing_ok=True)

    process_video.delay(str(video.id))
