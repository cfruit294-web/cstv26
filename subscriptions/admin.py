from django.contrib import admin

from subscriptions.models import Plan, Subscription


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'tier', 'price', 'currency', 'billing_period', 'trial_days', 'is_active')
    list_filter = ('tier', 'billing_period', 'is_active')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan', 'status', 'current_period_end', 'auto_renew', 'created_at')
    list_filter = ('status', 'auto_renew')
    search_fields = ('user__email', 'plan__name')
    readonly_fields = ('id', 'created_at', 'updated_at')
