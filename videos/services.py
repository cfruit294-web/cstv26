"""Wrapper autour de ffmpeg/ffprobe : sonde, miniature, transcodage HLS multi-résolution."""
import json
import subprocess
from pathlib import Path

from django.conf import settings

# (label, largeur, hauteur, bitrate vidéo, bitrate audio), du plus haut vers le plus bas.
RENDITION_LADDER = [
    ('1080p', 1920, 1080, '5000k', '192k'),
    ('720p', 1280, 720, '2800k', '128k'),
    ('480p', 854, 480, '1400k', '128k'),
    ('360p', 640, 360, '800k', '96k'),
]


class TranscodingError(Exception):
    """Levée lorsque ffmpeg/ffprobe échoue ou est absent du système."""


def _run(cmd):
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise TranscodingError(f"Binaire introuvable ({cmd[0]}) : {exc}") from exc
    if result.returncode != 0:
        raise TranscodingError(result.stderr.strip() or f'Échec de la commande : {" ".join(cmd)}')
    return result.stdout


def probe_duration_seconds(source_path):
    output = _run([
        settings.FFPROBE_BINARY, '-v', 'error',
        '-show_entries', 'format=duration', '-of', 'json', str(source_path),
    ])
    return int(float(json.loads(output)['format']['duration']))


def probe_video_height(source_path):
    output = _run([
        settings.FFPROBE_BINARY, '-v', 'error', '-select_streams', 'v:0',
        '-show_entries', 'stream=height', '-of', 'json', str(source_path),
    ])
    streams = json.loads(output).get('streams') or [{}]
    return streams[0].get('height', 0)


def generate_thumbnail(source_path, output_path, at_second=1):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    _run([
        settings.FFMPEG_BINARY, '-y', '-ss', str(at_second), '-i', str(source_path),
        '-vframes', '1', '-q:v', '2', str(output_path),
    ])


def transcode_to_hls_rendition(source_path, output_dir, width, height, video_bitrate, audio_bitrate, segment_seconds=6):
    output_dir.mkdir(parents=True, exist_ok=True)
    playlist_path = output_dir / 'playlist.m3u8'
    _run([
        settings.FFMPEG_BINARY, '-y', '-i', str(source_path),
        '-vf', f'scale=w={width}:h={height}:force_original_aspect_ratio=decrease:force_divisible_by=2,format=yuv420p',
        '-c:a', 'aac', '-ar', '48000', '-b:a', audio_bitrate,
        '-c:v', 'h264', '-pix_fmt', 'yuv420p', '-profile:v', 'main', '-crf', '20', '-sc_threshold', '0',
        '-g', '48', '-keyint_min', '48', '-b:v', video_bitrate,
        '-hls_time', str(segment_seconds), '-hls_playlist_type', 'vod',
        '-hls_segment_filename', str(output_dir / 'segment_%03d.ts'),
        str(playlist_path),
    ])
    return playlist_path


def build_master_playlist(output_dir, renditions):
    """renditions : liste de dicts {width, height, bandwidth, relative_path}."""
    lines = ['#EXTM3U', '#EXT-X-VERSION:3']
    for rendition in renditions:
        lines.append(f'#EXT-X-STREAM-INF:BANDWIDTH={rendition["bandwidth"]},'
                      f'RESOLUTION={rendition["width"]}x{rendition["height"]}')
        lines.append(rendition['relative_path'])

    master_path = Path(output_dir) / 'master.m3u8'
    master_path.write_text('\n'.join(lines) + '\n')
    return master_path
