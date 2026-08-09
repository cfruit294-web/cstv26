from django.contrib import admin

from videos.models import Subtitle, Video


class SubtitleInline(admin.TabularInline):
    model = Subtitle
    extra = 0
    fields = ('language', 'file')


@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = ('title', 'owner', 'status', 'visibility', 'duration_seconds', 'created_at')
    list_filter = ('status', 'visibility')
    search_fields = ('title', 'owner__email')
    readonly_fields = ('id', 'renditions', 'hls_master_playlist', 'error_message', 'created_at', 'updated_at')
    inlines = [SubtitleInline]
