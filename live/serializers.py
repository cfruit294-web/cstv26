from django.urls import reverse
from rest_framework import serializers

from live.models import LiveChatMessage, LiveStream
from live.tokens import generate_live_hls_token
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
    """Vue publique : n'expose ni la clé de stream ni l'URL d'ingestion RTMP.

    hls_playback_url pointe vers LiveHlsProxyView (relais côté Django), jamais directement vers
    MediaMTX : l'URL directe embarquerait stream_key, qui est aussi le secret d'ingestion RTMP —
    le laisser fuir dans une réponse publique permettrait à quiconque de détourner le live (publier
    du contenu à la place du propriétaire).
    """

    owner_email = serializers.EmailField(source='owner.email', read_only=True)
    hls_playback_url = serializers.SerializerMethodField()
    replay = ReplaySerializer(source='replay_video', read_only=True)

    def get_hls_playback_url(self, obj):
        request = self.context.get('request')
        path = reverse('live:stream-hls', kwargs={'id': obj.id, 'relpath': 'index.m3u8'})
        url = request.build_absolute_uri(path) if request else path
        if obj.visibility == LiveStream.Visibility.PRIVATE:
            url = f'{url}?token={generate_live_hls_token(obj.id)}'
        return url

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
