from django.contrib import admin
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
    readonly_fields = ('created_at', 'updated_at', 'reference_number', 'account_last_5')
    
    actions = ['force_verify_selected']

    def force_verify_selected(self, request, queryset):
        verified = 0
        for trans in queryset.filter(status=Transaction.Status.PENDING):
            trans.status = Transaction.Status.VERIFIED
            trans.save()
            trans.activate_subscription()
            verified += 1
        self.message_user(request, f"{verified} transactions force-verified and subscriptions activated.")
    force_verify_selected.short_description = "Force verify & activate selected transactions"
    
    