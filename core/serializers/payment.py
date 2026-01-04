# core/serializers/payment.py

from rest_framework import serializers
from payment.models import PaymentMethod, PaymentMethodTranslation, Transaction
from .base import AllTranslationsMixin

class PaymentMethodSerializer(serializers.ModelSerializer, AllTranslationsMixin):
    translations = serializers.SerializerMethodField()

    class Meta:
        model = PaymentMethod
        fields = ['id', 'name', 'code', 'logo', 'is_active', 'order', 'method_type', 'translations']

    def get_translations(self, obj):
        return self.get_translations_dict(
            obj,
            obj.translations.all(),
            fields=['account_details', 'instruction']
        )


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ['id', 'reference_number', 'account_last_5', 'amount', 'status', 'created_at', 'updated_at']
        
        
        