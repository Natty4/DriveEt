# core/viewsets/payment.py

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.core.exceptions import ValidationError

from payment.models import PaymentMethod, Transaction
from core.serializers.payment import PaymentMethodSerializer, TransactionSerializer
from core.services.subscription_service import SubscriptionService
from core.responses import APIResponse
from core.permissions import IsTelegramAuthenticated
import logging

logger = logging.getLogger(__name__)

from django.contrib.auth import get_user_model


class PaymentViewSet(viewsets.ViewSet):
    permission_classes = [IsTelegramAuthenticated]

    @action(detail=False, methods=['get'])
    def methods(self, request):
        methods = PaymentMethod.objects.filter(is_active=True).prefetch_related('translations')
        serializer = PaymentMethodSerializer(methods, many=True, context={'request': request})
        return APIResponse.success(data=serializer.data)

    @action(detail=False, methods=['post'])
    def purchase(self, request):
        """
        Purchase and activate subscription with immediate verification.
        Expected payload:
        {
            "tier_id": "uuid",
            "payment_method_id": "uuid",
            "reference_number": "string",
            "account_last_5": "optional string"
        }
        """
        tier_id = request.data.get('tier_id')
        payment_method_id = request.data.get('payment_method_id')
        reference_number = request.data.get('reference_number')
        account_last_5 = request.data.get('account_last_5', '')

        missing = [field for field in ['tier_id', 'payment_method_id', 'reference_number'] if not request.data.get(field)]
        if missing:
            return APIResponse.error(
                message=f"Missing required fields: {', '.join(missing)}",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        try:
            transaction_obj = SubscriptionService.activate_via_payment(
                user_profile=request.user.profile,
                tier_id=tier_id,
                payment_method_id=payment_method_id,
                reference_number=reference_number,
                account_last_5=account_last_5
            )

            transaction_serializer = TransactionSerializer(transaction_obj)
            return APIResponse.created(
                data={
                    "transaction": transaction_serializer.data,
                    "subscription_active": True,
                    "expiry_date": request.user.profile.expiry_date.isoformat(),
                    "tier": {
                        "id": transaction_obj.subscription_tier.id,
                        "name": transaction_obj.subscription_tier.display_name
                    }
                },
                message="Subscription activated successfully!"
            )

        except ValidationError as e:
            return APIResponse.error(
                message=str(e),
                status_code=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.exception(f"Unexpected error in purchase for user {request.user.profile.tg_username}")
            return APIResponse.error(
                message="An unexpected error occurred. Please contact support if the issue persists.",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def transactions(self, request):
        transactions = Transaction.objects.filter(
            user_profile=request.user.profile
        ).select_related('subscription_tier', 'payment_method').order_by('-created_at')

        serializer = TransactionSerializer(transactions, many=True)
        return APIResponse.success(data=serializer.data)
    
    
    
    
    