from django.contrib import admin

from watchparty.models import WatchParty, WatchPartyChatMessage, WatchPartyMembership


class WatchPartyMembershipInline(admin.TabularInline):
    model = WatchPartyMembership
    extra = 0
    fields = ('user', 'role', 'status')
    autocomplete_fields = ('user',)


@admin.register(WatchParty)
class WatchPartyAdmin(admin.ModelAdmin):
    list_display = ('display_title', 'host', 'scheduled_at', 'status', 'is_playing')
    list_filter = ('status',)
    search_fields = ('title', 'host__email', 'video__title')
    autocomplete_fields = ('host', 'video')
    readonly_fields = ('id', 'playback_position_seconds', 'playback_updated_at', 'created_at', 'updated_at')
    inlines = [WatchPartyMembershipInline]


@admin.register(WatchPartyChatMessage)
class WatchPartyChatMessageAdmin(admin.ModelAdmin):
    list_display = ('party', 'user', 'message', 'created_at')
    search_fields = ('party__title', 'user__email', 'message')
    readonly_fields = ('id', 'created_at', 'updated_at')
