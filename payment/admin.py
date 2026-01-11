from django.contrib import admin
from django.utils.html import format_html
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
    list_display = ('id', 'user_profile', 'subscription_tier', 'payment_method', 'amount', 'status', 'reference_number', 'created_at')
    list_filter = ('status', 'payment_method', 'created_at')
    search_fields = ('reference_number', 'user_profile__tg_id', 'id')
    readonly_fields = ('created_at', 'updated_at', 'reference_number', 'account_last_5', 'screenshot_preview')

    def has_screenshot(self, obj):
        return bool(obj.screenshot)
    has_screenshot.boolean = True

    def screenshot_preview(self, obj):
        if obj.screenshot:
            return format_html('<img src="{}" width="100"/>', obj.screenshot.url)
        return "No screenshot"
    screenshot_preview.short_description = "Payment Proof"

    actions = ['approve_selected', 'reject_selected']

    def approve_selected(self, request, queryset):
        for trans in queryset.filter(status=Transaction.Status.PENDING):
            trans.status = Transaction.Status.VERIFIED
            trans.save()
            trans.activate_subscription()
        self.message_user(request, "Selected transactions approved & subscriptions activated.")
    approve_selected.short_description = "Approve & Activate"

    def reject_selected(self, request, queryset):
        queryset.filter(status=Transaction.Status.PENDING).update(status=Transaction.Status.FAILED)
        self.message_user(request, "Selected transactions rejected.")
    reject_selected.short_description = "Reject"
    
    