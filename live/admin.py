from django.conf import settings
from django.contrib import admin
from django.utils.html import format_html

from live.models import LiveChatMessage, LiveStream


@admin.register(LiveStream)
class LiveStreamAdmin(admin.ModelAdmin):
    list_display = ('title', 'owner', 'status', 'visibility', 'scheduled_at', 'started_at', 'ended_at', 'has_replay')
    list_filter = ('status', 'visibility')
    search_fields = ('title', 'owner__email', 'stream_key')
    autocomplete_fields = ('owner',)
    readonly_fields = (
        'id', 'stream_key', 'obs_server_url', 'obs_stream_key', 'replay_video', 'created_at', 'updated_at',
    )
    fieldsets = (
        (None, {'fields': ('id', 'owner', 'title', 'description', 'visibility', 'status')}),
        ('Programmation', {'fields': ('scheduled_at', 'scheduled_duration_minutes', 'started_at', 'ended_at')}),
        ('Connexion OBS / Wirecast', {
            'fields': ('obs_server_url', 'obs_stream_key'),
            'description': (
                "Dans les réglages de diffusion (Stream) d'OBS ou Wirecast, colle « Serveur » et "
                "« Clé de stream » tels quels. Le live passe automatiquement en direct dès que "
                "l'encodeur commence à pousser le flux, et se termine (avec rediffusion générée "
                "automatiquement si l'enregistrement est disponible) dès qu'il arrête."
            ),
        }),
        ('Rediffusion', {
            'fields': ('replay_video',),
            'description': "Générée automatiquement à la fin du live si un enregistrement est disponible.",
        }),
        ('Métadonnées', {'fields': ('created_at', 'updated_at')}),
    )

    @admin.display(description='Rediffusion', boolean=True)
    def has_replay(self, obj):
        return obj.replay_video_id is not None

    @admin.display(description='Serveur (champ « Serveur » d\'OBS/Wirecast)')
    def obs_server_url(self, obj):
        return format_html('<code>{}</code>', settings.RTMP_INGEST_BASE_URL)

    @admin.display(description='Clé de stream (champ « Clé de stream » d\'OBS/Wirecast)')
    def obs_stream_key(self, obj):
        return format_html('<code>{}</code>', obj.stream_key)


@admin.register(LiveChatMessage)
class LiveChatMessageAdmin(admin.ModelAdmin):
    list_display = ('stream', 'user', 'message', 'created_at')
    search_fields = ('stream__title', 'user__email', 'message')
    readonly_fields = ('id', 'created_at', 'updated_at')
