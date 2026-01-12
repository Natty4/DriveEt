from django.contrib import admin
from django.utils.html import format_html

from core.utils.telegram_notifications import (
    notify_user_subscription_activated, 
    notify_user_subscription_rejected
)
from payment.models import (
    PaymentMethod, 
    PaymentMethodTranslation, 
    Transaction
)

class PaymentMethodTranslationInline(admin.StackedInline):
    model = PaymentMethodTranslation
    extra = 1
    fields = ('language', 'account_details', 'instruction')

@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'method_type', 'is_active', 'order')
    search_fields = ('name', 'code')
    list_filter = ('is_active', 'method_type')
    inlines = [PaymentMethodTranslationInline]

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'user_profile', 'subscription_tier', 'payment_method',
        'amount', 'status_display', 'reference_number', 'account_last_5',
        'has_screenshot', 'created_at'
    )
    list_filter = ('status', 'payment_method', 'created_at')
    list_editable = ('reference_number', 'account_last_5')
    search_fields = ('reference_number', 'user_profile__telegram_id', 'id')
    readonly_fields = ('created_at', 'updated_at', 'screenshot_preview_full')
    actions = ['approve_selected', 'reject_selected']

    def status_display(self, obj):
        colors = {'PENDING': 'orange', 'VERIFIED': 'green', 'FAILED': 'red', 'EXPIRED': 'gray'}
        return format_html(
            '<span style="color: {};">{}</span>',
            colors.get(obj.status, 'black'),
            obj.get_status_display()
        )
    status_display.short_description = "Status"

    def has_screenshot(self, obj):
        return bool(obj.screenshot)
    has_screenshot.boolean = True

    def screenshot_preview(self, obj):
        if obj.screenshot:
            return format_html('<img src="{}" width="100" style="border-radius:4px;"/>', obj.screenshot.url)
        return "—"
    screenshot_preview.short_description = "Proof"

    def screenshot_preview_full(self, obj):
        if obj.screenshot:
            return format_html('<img src="{}" width="500"/>', obj.screenshot.url)
        return "No screenshot uploaded"
    screenshot_preview_full.short_description = "Full Proof"

    def approve_selected(self, request, queryset):
        approved = 0
        for trans in queryset.filter(status=Transaction.Status.PENDING):
            # Optional: Require proof
            if not trans.reference_number and not trans.screenshot:
                self.message_user(
                    request,
                    f"Cannot approve {trans.id}: missing reference and screenshot.",
                    level='error'
                )
                continue

            trans.status = Transaction.Status.VERIFIED
            trans.save()
            trans.activate_subscription()

            # Notify user on approval
            notify_user_subscription_activated(
                user_profile=trans.user_profile,
                subscription=trans.user_profile.active_subscription
            )

            approved += 1

        self.message_user(
            request,
            f"{approved} transactions approved & subscriptions activated. Users notified."
        )

    approve_selected.short_description = "Approve & Activate (notify user)"

    def reject_selected(self, request, queryset):
        rejected = 0
        for trans in queryset.filter(status=Transaction.Status.PENDING):
            trans.status = Transaction.Status.FAILED
            trans.save()
            rejected += 1

            # Notify user on rejection
            notify_user_subscription_rejected(trans.user_profile)

        self.message_user(
            request,
            f"{rejected} transactions rejected. Users notified."
        )

    reject_selected.short_description = "Reject selected (notify user)"