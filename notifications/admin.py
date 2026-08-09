from django.contrib import admin

from notifications.models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'category', 'title', 'is_read', 'created_at')
    list_filter = ('category', 'is_read')
    search_fields = ('recipient__email', 'title')
    readonly_fields = ('id', 'created_at', 'updated_at')
