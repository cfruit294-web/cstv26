from django.contrib import admin

from videos.models import Subtitle, Video
from videos.tasks import process_video


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

    def save_model(self, request, obj, form, change):
        # Contrairement à l'upload via l'API (VideoUploadView), l'admin n'a pas de logique de
        # transcodage dédiée : sans ça, un fichier ajouté/remplacé depuis l'admin resterait
        # bloqué en "En attente" indéfiniment (le film ajouté manuellement n'est jamais rendu jouable).
        super().save_model(request, obj, form, change)
        if not change or 'source_file' in form.changed_data:
            obj.status = Video.Status.PENDING
            obj.error_message = ''
            obj.save(update_fields=['status', 'error_message'])
            process_video.delay(str(obj.id))
