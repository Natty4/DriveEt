# core/viewsets/payment.py

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.core.exceptions import ValidationError
from django.utils import timezone
import logging

from users.models import SubscriptionTier
from payment.models import PaymentMethod, Transaction
from core.serializers.payment import PaymentMethodSerializer, TransactionSerializer
from core.services.subscription_service import SubscriptionService
from core.responses import APIResponse
from core.permissions import IsTelegramAuthenticated
from core.utils.telegram_bot import send_screenshot_to_admin

logger = logging.getLogger(__name__)
class PaymentViewSet(viewsets.ViewSet):
    permission_classes = [IsTelegramAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    @action(detail=False, methods=['get'])
    def methods(self, request):
        methods = PaymentMethod.objects.filter(is_active=True).prefetch_related('translations')
        serializer = PaymentMethodSerializer(methods, many=True, context={'request': request})
        return APIResponse.success(data=serializer.data)

    @action(detail=False, methods=['post'])
    def purchase(self, request):
        """
        Purchase subscription with two verification methods:
        1. Reference number + account_last_5 (auto-verified)
        2. Screenshot upload (manual admin approval)

        Payload (multipart/form-data):
        - tier_id (required)
        - payment_method_id (required)
        - reference_number (optional)
        - account_last_5 (optional)
        - screenshot (file, optional)
        """
        tier_id = request.data.get('tier_id')
        payment_method_id = request.data.get('payment_method_id')
        reference_number = request.data.get('reference_number')
        account_last_5 = request.data.get('account_last_5', '')
        screenshot = request.FILES.get('screenshot')

        # Validation: at least one verification method
        if not reference_number and not screenshot:
            return APIResponse.error(
                message="Provide either reference_number + account_last_5 OR a screenshot.",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        missing = [field for field in ['tier_id', 'payment_method_id'] if not request.data.get(field)]
        if missing:
            return APIResponse.error(
                message=f"Missing required fields: {', '.join(missing)}",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        try:
            user_profile = request.user.profile

            # 1. Create pending transaction
            transaction_obj = Transaction.objects.create(
                user_profile=user_profile,
                subscription_tier_id=tier_id,
                payment_method_id=payment_method_id,
                amount=SubscriptionTier.objects.get(id=tier_id).price,
                reference_number=reference_number,
                account_last_5=account_last_5,
                screenshot=screenshot,  # Auto-uploads to Cloudinary
                status=Transaction.Status.PENDING
            )

            # 2. If reference provided → try auto-verify
            if reference_number:
                try:
                    SubscriptionService.activate_via_payment(
                        user_profile=user_profile,
                        tier_id=tier_id,
                        payment_method_id=payment_method_id,
                        reference_number=reference_number,
                        account_last_5=account_last_5
                    )
                    return APIResponse.created(
                        message="Subscription activated successfully!",
                        data={"transaction_id": str(transaction_obj.id)}
                    )
                except ValidationError as e:
                    logger.info(f"Auto-verification failed: {e}. Falling back to manual review.")

            # 3. Manual review flow (screenshot or failed auto)
            if screenshot:
                # Send screenshot to admin via Telegram
                screenshot_url = transaction_obj.screenshot.url
                send_screenshot_to_admin(
                    user=transaction_obj.user_profile,
                    transaction=transaction_obj,
                    screenshot_url=screenshot_url
                )
                message = "Payment screenshot received. Awaiting admin approval."
            else:
                message = "Reference verification failed. Awaiting manual review."

            return APIResponse.success(
                message=message,
                data={"transaction_id": str(transaction_obj.id)}
            )

        except Exception as e:
            logger.exception("Purchase error")
            return APIResponse.error(
                message="An error occurred during purchase. Please try again.",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
