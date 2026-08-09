from django.contrib import admin

from catalog.models import Movie


@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ('title', 'year', 'type', 'imdb_rating', 'imdb_id', 'created_at')
    list_filter = ('type',)
    search_fields = ('title', 'imdb_id')
    readonly_fields = ('id', 'raw_data', 'created_at', 'updated_at')
