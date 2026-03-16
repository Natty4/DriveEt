# payment/models.py

import uuid
from django.db import models, transaction
from django.db.models import UniqueConstraint, Q
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from datetime import timedelta
from cloudinary.models import CloudinaryField


from common.constants import Language
from users.models import Subscription



class PaymentMethod(models.Model):
    """Available payment methods"""
    class MethodType(models.TextChoices):
        BANK_TRANSFER = 'BANK_TRANSFER', _('Bank Transfer')
        MOBILE_WALLET = 'MOBILE_WALLET', _('Mobile Wallet')
        OTHER = 'other', _('Other Method')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, verbose_name=_("Name"))
    code = models.CharField(max_length=50, unique=True, verbose_name=_("Code"))
    logo = models.CharField(null=True, blank=True, help_text=_("A valid logo url"))
    is_active = models.BooleanField(default=True, verbose_name=_("Active"))
    order = models.PositiveSmallIntegerField(default=0, verbose_name=_("Display Order"))
    method_type = models.CharField(
        max_length=20,
        choices=MethodType.choices,
        default=MethodType.MOBILE_WALLET
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Payment Method")
        verbose_name_plural = _("Payment Methods")
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class PaymentMethodTranslation(models.Model):
    """Translation for payment method details and instructions"""
    payment_method = models.ForeignKey(
        PaymentMethod,
        on_delete=models.CASCADE,
        related_name='translations'
    )
    language = models.CharField(
        max_length=10,
        choices=Language.choices(),
        default=Language.ENGLISH.value
    )
    account_details = models.TextField(verbose_name=_("Account Details"))
    instruction = models.TextField(verbose_name=_("Instruction"))

    class Meta:
        verbose_name = _("Payment Method Translation")
        verbose_name_plural = _("Payment Method Translations")
        unique_together = ['payment_method', 'language']
        ordering = ['language']

    def __str__(self):
        return f"{self.payment_method.name} - {self.get_language_display()}"


class Transaction(models.Model):
    """Tracks payments with states."""
    class Status(models.TextChoices):
        PENDING = 'PENDING', _('Pending')
        VERIFIED = 'VERIFIED', _('Verified')
        EXPIRED = 'EXPIRED', _('Expired')
        FAILED = 'FAILED', _('Failed')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_profile = models.ForeignKey('users.UserProfile', on_delete=models.CASCADE, related_name='transactions')
    subscription_tier = models.ForeignKey('users.SubscriptionTier', on_delete=models.PROTECT)
    reference_number = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Bank/mobile wallet transaction reference (optional if screenshot is provided)"
    )
    account_last_5 = models.CharField(
        max_length=5,
        blank=True,
        null=True,
        help_text="Last 5 digits of payer account (optional)"
    )
    screenshot = CloudinaryField(
        'image',
        folder='transaction_screenshots/',
        resource_type='image',
        null=True,
        blank=True,
        help_text="Screenshot of payment proof (alternative to reference number)"
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.SET_NULL, null=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    
    verified_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    payer_name = models.CharField(max_length=255, blank=True, null=True)
    payer_phone = models.CharField(max_length=20, blank=True, null=True)
    receiver_name = models.CharField(max_length=255, blank=True, null=True)
    receiver_account = models.CharField(max_length=50, blank=True, null=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_date = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Transaction")
        verbose_name_plural = _("Transactions")
        indexes = [
            models.Index(fields=['user_profile', 'status']),
            models.Index(fields=['payment_method', 'reference_number']),
            ]
        constraints = [
            UniqueConstraint(
                fields=['payment_method', 'reference_number'],
                condition=Q(status='VERIFIED'),
                name='unique_verified_payment_reference'
            )
        ]

    def activate_subscription(self):
        with transaction.atomic():
            now = timezone.now()

            # Deactivate ALL previous subscriptions of this user
            Subscription.objects.filter(
                user_profile=self.user_profile,
                is_active=True
            ).update(is_active=False)

            # Check if renewing same tier
            latest_same_tier = Subscription.objects.filter(
                user_profile=self.user_profile,
                tier=self.subscription_tier
            ).order_by('-created_at', '-updated_at').first()

            if latest_same_tier:
                # Renewal / extension
                base_date = latest_same_tier.expiry_date if latest_same_tier.expiry_date and latest_same_tier.expiry_date > now else now
                new_expiry = base_date + timedelta(days=self.subscription_tier.duration_days)
                latest_same_tier.expiry_date = new_expiry
                latest_same_tier.is_active = True
                latest_same_tier.save(update_fields=['expiry_date', 'is_active'])
                subscription = latest_same_tier
            else:
                # New subscription
                new_expiry = now + timedelta(days=self.subscription_tier.duration_days) if self.subscription_tier.duration_days > 0 else None
                subscription = Subscription.objects.create(
                    user_profile=self.user_profile,
                    tier=self.subscription_tier,
                    expiry_date=new_expiry,
                    is_active=True
                )

            # Update profile
            self.user_profile.active_subscription = subscription
            self.user_profile.expiry_date = subscription.expiry_date
            self.user_profile.save(update_fields=['active_subscription', 'expiry_date'])

            # Optional: mark transaction as used if not already
            if self.status != Transaction.Status.VERIFIED:
                self.status = Transaction.Status.VERIFIED
                self.save()
        


