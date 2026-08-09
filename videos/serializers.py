from django.conf import settings
from rest_framework import serializers

from videos.models import Video
from videos.tokens import generate_hls_token

ALLOWED_VIDEO_EXTENSIONS = ('.mp4', '.mov', '.mkv', '.avi', '.webm')


class VideoSerializer(serializers.ModelSerializer):
    owner_email = serializers.EmailField(source='owner.email', read_only=True)
    hls_master_playlist = serializers.SerializerMethodField()
    renditions = serializers.SerializerMethodField()

    class Meta:
        model = Video
        fields = (
            'id', 'title', 'description', 'visibility', 'status', 'owner_email', 'movie',
            'thumbnail', 'duration_seconds', 'hls_master_playlist', 'renditions',
            'error_message', 'created_at', 'updated_at',
        )
        read_only_fields = (
            'id', 'status', 'owner_email', 'thumbnail', 'duration_seconds',
            'hls_master_playlist', 'renditions', 'error_message', 'created_at', 'updated_at',
        )

    def _token(self, obj):
        return generate_hls_token(obj.id)

    def get_hls_master_playlist(self, obj):
        if not obj.hls_master_playlist:
            return ''
        return f'{obj.hls_master_playlist}?token={self._token(obj)}'

    def get_renditions(self, obj):
        if not obj.renditions:
            return {}
        token = self._token(obj)
        return {label: f'{path}?token={token}' for label, path in obj.renditions.items()}


class VideoUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Video
        fields = ('id', 'title', 'description', 'visibility', 'movie', 'source_file')
        read_only_fields = ('id',)
        extra_kwargs = {'source_file': {'write_only': True}}

    def validate_source_file(self, value):
        if not value.name.lower().endswith(ALLOWED_VIDEO_EXTENSIONS):
            raise serializers.ValidationError(
                f"Format non supporté. Extensions autorisées : {', '.join(ALLOWED_VIDEO_EXTENSIONS)}.",
            )
        max_size_bytes = settings.MAX_VIDEO_UPLOAD_SIZE_MB * 1024 * 1024
        if value.size > max_size_bytes:
            raise serializers.ValidationError(
                f'Le fichier dépasse la taille maximale de {settings.MAX_VIDEO_UPLOAD_SIZE_MB} Mo.',
            )
        return value
