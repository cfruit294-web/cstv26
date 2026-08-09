from pathlib import Path

from celery import shared_task
from django.conf import settings

from videos import services
from videos.models import Video


@shared_task
def process_video(video_id):
    """Sonde, génère la miniature et transcode la vidéo source en HLS multi-résolution."""
    try:
        video = Video.objects.get(id=video_id)
    except Video.DoesNotExist:
        return

    video.status = Video.Status.PROCESSING
    video.save(update_fields=['status'])

    source_path = Path(video.source_file.path)
    output_root = Path(settings.MEDIA_ROOT) / 'hls' / str(video.id)

    try:
        video.duration_seconds = services.probe_duration_seconds(source_path)
        source_height = services.probe_video_height(source_path)

        thumbnail_relative = f'videos/thumbnails/{video.id}.jpg'
        services.generate_thumbnail(source_path, Path(settings.MEDIA_ROOT) / thumbnail_relative)
        video.thumbnail.name = thumbnail_relative

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

        video.renditions = {
            entry['label']: f'hls/{video.id}/{entry["relative_path"]}' for entry in manifest_entries
        }
        video.hls_master_playlist = f'hls/{video.id}/master.m3u8'
        video.status = Video.Status.READY
        video.error_message = ''
        video.save()
    except services.TranscodingError as exc:
        video.status = Video.Status.FAILED
        video.error_message = str(exc)
        video.save(update_fields=['status', 'error_message'])
