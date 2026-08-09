from rest_framework import serializers

from live.models import LiveChatMessage, LiveStream
from videos.tokens import generate_hls_token


class ReplaySerializer(serializers.Serializer):
    """Résumé minimal de la vidéo de rediffusion, suffisant pour afficher un lecteur."""

    id = serializers.UUIDField()
    status = serializers.CharField()
    thumbnail = serializers.SerializerMethodField()
    duration_seconds = serializers.IntegerField()
    hls_master_playlist = serializers.SerializerMethodField()

    def get_thumbnail(self, video):
        if not video.thumbnail:
            return None
        request = self.context.get('request')
        url = video.thumbnail.url
        return request.build_absolute_uri(url) if request else url

    def get_hls_master_playlist(self, video):
        if not video.hls_master_playlist:
            return ''
        return f'{video.hls_master_playlist}?token={generate_hls_token(video.id)}'


class LiveStreamSerializer(serializers.ModelSerializer):
    """Vue publique : n'expose ni la clé de stream ni l'URL d'ingestion RTMP."""

    owner_email = serializers.EmailField(source='owner.email', read_only=True)
    hls_playback_url = serializers.ReadOnlyField()
    replay = ReplaySerializer(source='replay_video', read_only=True)

    class Meta:
        model = LiveStream
        fields = (
            'id', 'title', 'description', 'visibility', 'status', 'owner_email',
            'scheduled_at', 'scheduled_duration_minutes', 'started_at', 'ended_at',
            'hls_playback_url', 'replay', 'created_at',
        )
        read_only_fields = fields


class LiveStreamOwnerSerializer(LiveStreamSerializer):
    """Vue propriétaire/admin : inclut la clé de stream et l'URL d'ingestion RTMP (sensibles)."""

    rtmp_ingest_url = serializers.ReadOnlyField()

    class Meta(LiveStreamSerializer.Meta):
        fields = LiveStreamSerializer.Meta.fields + ('stream_key', 'rtmp_ingest_url')


class LiveStreamCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = LiveStream
        fields = ('id', 'title', 'description', 'visibility', 'scheduled_at', 'scheduled_duration_minutes')
        read_only_fields = ('id',)


class LiveChatMessageSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = LiveChatMessage
        fields = ('id', 'user_email', 'message', 'created_at')
        read_only_fields = fields
