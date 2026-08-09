from django.contrib import admin

from cms.models import Page


@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = ('title', 'page_type', 'is_published', 'published_at', 'author')
    list_filter = ('page_type', 'is_published')
    search_fields = ('title', 'slug', 'content')
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ('id', 'created_at', 'updated_at')
