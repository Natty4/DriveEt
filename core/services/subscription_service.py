# core/services/subscription_service.py

from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.conf import settings
from datetime import timedelta
from decimal import Decimal
from dateutil.parser import parse as parse_date
import logging

from payment.verification import PaymentVerifier
from payment.models import Transaction, PaymentMethod
from users.models import Subscription, UserProfile, SubscriptionTier

logger = logging.getLogger(__name__)


class SubscriptionService:
    @staticmethod
    @transaction.atomic
    def activate_via_payment(
        user_profile: UserProfile,
        tier_id: str,
        payment_method_id: str,
        reference_number: str,
        account_last_5: str = "",
        pending_transaction: Transaction = None  # New: pass existing pending transaction
    ) -> Transaction:
        tier = SubscriptionTier.objects.get(id=tier_id)
        payment_method = PaymentMethod.objects.get(id=payment_method_id, is_active=True)  # assume imported

        # Use passed transaction or create new
        if pending_transaction:
            transaction_obj = pending_transaction
        else:
            transaction_obj = Transaction.objects.create(
                user_profile=user_profile,
                subscription_tier=tier,
                payment_method=payment_method,
                amount=tier.price,
                reference_number=reference_number,
                account_last_5=account_last_5,
                status=Transaction.Status.PENDING
            )

        verifier = PaymentVerifier()
        result = verifier.verify_payment(payment_method.code.upper(), reference_number)

        if not result.success:
            transaction_obj.status = Transaction.Status.FAILED
            transaction_obj.save()
            raise ValidationError(result.error or "Verification failed")

        # 1. Duplicate protection
        if Transaction.objects.filter(
            payment_method=payment_method,
            reference_number=reference_number,
            status=Transaction.Status.VERIFIED
        ).exists():
            raise ValidationError("This transaction reference has already been used.")

        # 2. Amount exact match (±1 ETB tolerance)
        tolerance = Decimal('1.00')
        if result.amount is None or abs(result.amount - tier.price) > tolerance:
            raise ValidationError(f"Amount mismatch. Expected {tier.price}, got {result.amount}")

        # 3. Age check (max 7 days)
        if result.transaction_date:
            try:
                pay_date = parse_date(result.transaction_date)
                if timezone.is_naive(pay_date):
                    pay_date = timezone.make_aware(pay_date)
                if timezone.now() - pay_date > timedelta(days=7):
                    raise ValidationError("Payment is older than 7 days.")
            except:
                logger.warning("Could not parse payment date")

        # 4. Account last 5 match
        if account_last_5 and result.payer_account and result.payer_account[-5:] != account_last_5:
            raise ValidationError("Payer account last 5 digits do not match.")

        # 5. Receiver verification
        expected_receiver = {
            'TELEBIRR': getattr(settings, 'TELEBIRR_PHONE', None),
            'BOA': getattr(settings, 'BOA_ACCOUNT', None),
        }.get(payment_method.code.upper())

        if expected_receiver and result.receiver_account and expected_receiver not in str(result.receiver_account):
            raise ValidationError("Payment was not sent to the correct receiver account.")

        # Populate audit fields
        transaction_obj.verified_amount = result.amount
        transaction_obj.payer_name = result.payer_name
        transaction_obj.payer_phone = result.payer_phone
        transaction_obj.receiver_name = result.receiver_name
        transaction_obj.receiver_account = result.receiver_account
        transaction_obj.verified_date = parse_date(result.transaction_date) if result.transaction_date else None
        transaction_obj.verified_at = timezone.now()

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
    
    