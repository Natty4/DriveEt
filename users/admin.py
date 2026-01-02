from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from core.admin import ExpiryStatusFilter
from users.models import (
    UserProfile, 
    SubscriptionTier, 
    Subscription, 
    SubscriptionTierTranslation
    )

class SubscriptionTierTranslationInline(admin.StackedInline):
    model = SubscriptionTierTranslation
    extra = 1
    fields = ('language', 'name', 'description')

@admin.register(SubscriptionTier)
class SubscriptionTierAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'price', 'duration_days', 'max_exam_number', 'full_road_sign_quiz')
    search_fields = ('translations__name',)
    list_filter = ('price', 'duration_days', 'full_road_sign_quiz')
    inlines = [SubscriptionTierTranslationInline]
    filter_horizontal = ('exams',)

    def display_name(self, obj):
        return obj.display_name
    display_name.short_description = 'Name'

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('tg_username', 'subscription_status', 'expiry_countdown', 'preferred_language')
    search_fields = ('tg_username', 'tg_id')
    list_filter = ('preferred_language', ExpiryStatusFilter)
    readonly_fields = ('tg_id', 'tg_username', 'created_at', 'updated_at')

    def subscription_status(self, obj):
        return "Active" if obj.is_subscribed() else "Inactive"
    subscription_status.short_description = "Subscription"

    def expiry_countdown(self, obj):
        if obj.expiry_date:
            days = (obj.expiry_date - timezone.now()).days
            if days < 0:
                return format_html('<span style="color:red;">Expired</span>')
            elif days <= 7:
                return format_html('<span style="color:orange;">{} days</span>', days)
            else:
                return f"{days} days"
        return "—"
    expiry_countdown.short_description = "Expiry"
    
    
@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user_profile', 'tier', 'start_date', 'expiry_date', 'is_active', 'days_left')
    list_filter = ('tier', 'is_active')
    search_fields = ('user_profile__telegram_id',)
    actions = ['activate_selected', 'deactivate_selected', 'mark_as_expired']

    def days_left(self, obj):
        if obj.expiry_date:
            days = (obj.expiry_date - timezone.now()).days
            return f"{days} days" if days >= 0 else "Expired"
        return "Permanent"
    days_left.short_description = "Days Left"

    def mark_as_expired(self, request, queryset):
        now = timezone.now()
        updated = 0
        for sub in queryset.filter(is_active=True, expiry_date__lt=now):
            sub.is_active = False
            sub.save()
            updated += 1

        # Optional: clear active_subscription on profile if expired
        for sub in queryset.filter(is_active=False):
            profile = sub.user_profile
            if profile.active_subscription == sub:
                profile.active_subscription = None
                profile.expiry_date = None
                profile.save()

        self.message_user(request, f"{updated} subscriptions marked as expired and deactivated.")
    mark_as_expired.short_description = "Mark selected as expired (manual cleanup)"

    def activate_selected(self, request, queryset):
        for sub in queryset:
            profile = sub.user_profile
            profile.active_subscription = sub
            profile.expiry_date = sub.expiry_date
            profile.save()
        self.message_user(request, "Selected subscriptions activated.")
    activate_selected.short_description = "Activate selected subscriptions"

    def deactivate_selected(self, request, queryset):
        updated = 0
        for sub in queryset.filter(is_active=True):
            sub.is_active = False
            sub.save()
            updated += 1
            
        for sub in queryset:
            profile = sub.user_profile
            profile.active_subscription = None
            profile.expiry_date = None
            profile.save()

        self.message_user(request, f"{updated} Selected subscriptions deactivated.")
    deactivate_selected.short_description = "Deactivate selected subscriptions"