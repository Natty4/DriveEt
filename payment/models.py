# payment/models.py

import uuid
from django.db import models, transaction
from django.utils.translation import gettext_lazy as _
from cloudinary.models import CloudinaryField

from common.constants import Language
from users.models import Subscription



class PaymentMethod(models.Model):
    """Available payment methods"""
    class MethodType(models.TextChoices):
        BANK_TRANSFER = 'bank_transfer', _('Bank Transfer')
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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Transaction")
        verbose_name_plural = _("Transactions")
        indexes = [models.Index(fields=['user_profile', 'status'])]

    def activate_subscription(self):
        with transaction.atomic():
            # Create subscription
            sub = Subscription.objects.create(user_profile=self.user_profile, tier=self.subscription_tier)
            # Update user profile
            self.user_profile.active_subscription = sub
            self.user_profile.expiry_date = sub.expiry_date
            self.user_profile.save()
            # No need to copy exams; query via tier


