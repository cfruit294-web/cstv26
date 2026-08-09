from rest_framework import serializers

from videos.serializers import VideoSerializer
from watchparty.models import WatchParty, WatchPartyChatMessage, WatchPartyMembership


def membership_status(user, party):
    """'host' | 'moderator' | 'member' | 'pending' | 'rejected' | None (jamais demandé)."""
    if not user.is_authenticated:
        return None
    if party.host_id == user.id:
        return 'host'
    membership = WatchPartyMembership.objects.filter(party=party, user=user).first()
    if membership is None:
        return None
    if membership.status == WatchPartyMembership.Status.ACCEPTED:
        return membership.role
    return membership.status


class WatchPartySerializer(serializers.ModelSerializer):
    """Vue unique liste/détail : le contenu vidéo/position n'est révélé qu'aux membres acceptés et à l'hôte."""

    host_email = serializers.EmailField(source='host.email', read_only=True)
    display_title = serializers.ReadOnlyField()
    video_title = serializers.CharField(source='video.title', read_only=True)
    video_thumbnail = serializers.SerializerMethodField()
    member_count = serializers.SerializerMethodField()
    my_status = serializers.SerializerMethodField()
    video = serializers.SerializerMethodField()
    current_position_seconds = serializers.SerializerMethodField()

    class Meta:
        model = WatchParty
        fields = (
            'id', 'host_email', 'display_title', 'title', 'video_title', 'video_thumbnail',
            'scheduled_at', 'status', 'member_count', 'my_status', 'video',
            'current_position_seconds', 'is_playing', 'created_at',
        )
        read_only_fields = fields

    def _authorized(self, obj) -> bool:
        return self.get_my_status(obj) in ('host', 'member', 'moderator')

    def get_video_thumbnail(self, obj):
        if not obj.video.thumbnail:
            return None
        request = self.context.get('request')
        url = obj.video.thumbnail.url
        return request.build_absolute_uri(url) if request else url

    def get_member_count(self, obj) -> int:
        return obj.memberships.filter(status=WatchPartyMembership.Status.ACCEPTED).count() + 1

    def get_my_status(self, obj):
        request = self.context.get('request')
        if not request:
            return None
        return membership_status(request.user, obj)

    def get_video(self, obj):
        if not self._authorized(obj):
            return None
        return VideoSerializer(obj.video, context=self.context).data

    def get_current_position_seconds(self, obj):
        if not self._authorized(obj):
            return None
        return obj.current_position_seconds


class WatchPartyCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = WatchParty
        fields = ('id', 'video', 'title', 'scheduled_at')
        read_only_fields = ('id',)

    def validate_video(self, value):
        if value.status != value.Status.READY or value.visibility != value.Visibility.PUBLIC:
            raise serializers.ValidationError(
                'Seule une vidéo publique et prête peut être utilisée pour une séance de visionnage.',
            )
        return value


class WatchPartyMembershipSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = WatchPartyMembership
        fields = ('id', 'user_email', 'role', 'status', 'created_at')
        read_only_fields = fields


class WatchPartyChatMessageSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = WatchPartyChatMessage
        fields = ('id', 'user_email', 'message', 'created_at')
        read_only_fields = fields
