from django.contrib import admin

from library.models import WatchHistory, WatchlistItem


@admin.register(WatchlistItem)
class WatchlistItemAdmin(admin.ModelAdmin):
    list_display = ('user', 'movie', 'created_at')
    search_fields = ('user__email', 'movie__title')


@admin.register(WatchHistory)
class WatchHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'video', 'position_seconds', 'updated_at')
    search_fields = ('user__email', 'video__title')
