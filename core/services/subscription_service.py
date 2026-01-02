# users/services/subscription_service.py
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from payment.verification import PaymentVerifier
from payment.models import Transaction, PaymentMethod
from users.models import Subscription, UserProfile, SubscriptionTier
from django.core.exceptions import ValidationError
import logging

logger = logging.getLogger(__name__)


class SubscriptionService:
    @staticmethod
    @transaction.atomic
    def activate_via_payment(
        user_profile: UserProfile,
        tier_id: str,
        payment_method_id: str,
        reference_number: str,
        account_last_5: str = ""
    ) -> Transaction:
        # 1. Validate tier
        try:
            tier = SubscriptionTier.objects.get(id=tier_id)
        except SubscriptionTier.DoesNotExist:
            raise ValidationError("Invalid subscription tier.")

        # 2. Validate payment method
        try:
            payment_method = PaymentMethod.objects.get(id=payment_method_id, is_active=True)
        except PaymentMethod.DoesNotExist:
            raise ValidationError("Invalid or inactive payment method.")

        # 3. Create pending transaction
        transaction_obj = Transaction.objects.create(
            user_profile=user_profile,
            subscription_tier=tier,
            payment_method=payment_method,
            amount=tier.price,
            reference_number=reference_number,
            account_last_5=account_last_5,
            status=Transaction.Status.PENDING
        )

        # 4. Perform verification
        verifier = PaymentVerifier()
        result = verifier.verify_payment(
            method=payment_method.code.upper(),
            reference=reference_number
        )

        if not result.success:
            transaction_obj.status = Transaction.Status.FAILED
            transaction_obj.save()
            raise ValidationError(result.error or "Payment verification failed.")

        if result.amount is not None and result.amount < tier.price:
            transaction_obj.status = Transaction.Status.FAILED
            transaction_obj.save()
            raise ValidationError("Payment amount is less than required.")

        # 5. Handle subscription renewal / extension
        now = timezone.now()
        duration = timedelta(days=tier.duration_days)

        # Find active or recent subscription for this tier
        existing_sub = Subscription.objects.filter(
            user_profile=user_profile,
            tier=tier,
            is_active=True
        ).first()

        if existing_sub:
            # RENEWAL: Extend expiry date from current expiry (or now if expired)
            base_date = existing_sub.expiry_date if existing_sub.expiry_date > now else now
            new_expiry = base_date + duration

            existing_sub.expiry_date = new_expiry
            existing_sub.save()

            logger.info(f"Renewed subscription {existing_sub.id}: extended to {new_expiry}")

            subscription = existing_sub
        else:
            # NEW subscription
            new_expiry = now + duration if tier.duration_days > 0 else None
            subscription = Subscription.objects.create(
                user_profile=user_profile,
                tier=tier,
                expiry_date=new_expiry,
                is_active=True
            )
            logger.info(f"Created new subscription {subscription.id} for tier {tier.id}")

        # 6. Update user profile (active subscription & expiry)
        user_profile.active_subscription = subscription
        user_profile.expiry_date = subscription.expiry_date
        user_profile.save(update_fields=['active_subscription', 'expiry_date'])

        # 7. Mark transaction as verified
        transaction_obj.status = Transaction.Status.VERIFIED
        transaction_obj.save()

        return transaction_obj
    
    