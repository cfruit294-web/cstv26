from django.contrib import admin

from ads.models import Ad


@admin.register(Ad)
class AdAdmin(admin.ModelAdmin):
    list_display = ('title', 'creative_type', 'placement', 'is_active', 'duration_seconds', 'created_at')
    list_filter = ('creative_type', 'placement', 'is_active')
    search_fields = ('title',)
