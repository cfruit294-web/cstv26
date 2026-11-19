import logging
import tempfile
from pathlib import Path

from celery import shared_task

from core.storage import local_copy, upload_directory, upload_file
from videos import services
from videos.models import Video

logger = logging.getLogger(__name__)


@shared_task
def process_video(video_id):
    """Sonde, génère la miniature et transcode la vidéo source en HLS multi-résolution.

    Tout le travail ffmpeg se fait dans un dossier temporaire ; le résultat est ensuite poussé vers
    le stockage média (disque local ou S3, cf core/storage.py). Le worker n'a donc pas besoin de
    partager un disque avec le serveur web.
    """
    try:
        video = Video.objects.get(id=video_id)
    except Video.DoesNotExist:
        return

    video.status = Video.Status.PROCESSING
    video.save(update_fields=['status'])

    try:
        with tempfile.TemporaryDirectory(prefix=f'cstv-{video.id}-') as workdir:
            _transcode_and_store(video, Path(workdir))
    except services.TranscodingError as exc:
        _mark_failed(video, str(exc))
    except Exception as exc:  # noqa: BLE001 — stockage/réseau : ne jamais laisser la vidéo bloquée en "processing"
        logger.exception('Traitement de la vidéo %s échoué', video.id)
        _mark_failed(video, f'Erreur pendant le traitement ou l\'envoi vers le stockage : {exc}')


def _transcode_and_store(video, workdir):
    output_root = workdir / 'hls'
    thumbnail_local = workdir / 'thumbnail.jpg'

    with local_copy(video.source_file, workdir) as source_path:
        video.duration_seconds = services.probe_duration_seconds(source_path)
        source_height = services.probe_video_height(source_path)
        services.generate_thumbnail(source_path, thumbnail_local)

        applicable_ladder = [r for r in services.RENDITION_LADDER if r[2] <= source_height]
        if not applicable_ladder:
            applicable_ladder = [services.RENDITION_LADDER[-1]]

        manifest_entries = []
        for label, width, height, video_bitrate, audio_bitrate in applicable_ladder:
            services.transcode_to_hls_rendition(
                source_path, output_root / label, width, height, video_bitrate, audio_bitrate,
            )
            bandwidth = (int(video_bitrate.rstrip('k')) + int(audio_bitrate.rstrip('k'))) * 1000
            manifest_entries.append({
                'label': label, 'width': width, 'height': height,
                'bandwidth': bandwidth, 'relative_path': f'{label}/playlist.m3u8',
            })

    services.build_master_playlist(output_root, manifest_entries)

    hls_prefix = f'hls/{video.id}'
    upload_directory(output_root, hls_prefix)
    if thumbnail_local.is_file():
        video.thumbnail.name = upload_file(thumbnail_local, f'videos/thumbnails/{video.id}.jpg')

    video.renditions = {entry['label']: f'{hls_prefix}/{entry["relative_path"]}' for entry in manifest_entries}
    video.hls_master_playlist = f'{hls_prefix}/master.m3u8'
    video.status = Video.Status.READY
    video.error_message = ''
    video.save()


def _mark_failed(video, message):
    video.status = Video.Status.FAILED
    video.error_message = message
    video.save(update_fields=['status', 'error_message'])
