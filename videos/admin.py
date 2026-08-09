from django.contrib import admin

from videos.models import Video


@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = ('title', 'owner', 'status', 'visibility', 'duration_seconds', 'created_at')
    list_filter = ('status', 'visibility')
    search_fields = ('title', 'owner__email')
    readonly_fields = ('id', 'renditions', 'hls_master_playlist', 'error_message', 'created_at', 'updated_at')
