# users/models.py
import enum
import uuid
from datetime import timedelta

from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from core.models import Exam, AnswerChoice
from common.constants import Language

from django.contrib.auth import get_user_model
User = get_user_model()




class UserProfile(models.Model):
    """User profile linked to Telegram. Links to auth User."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    tg_id = models.CharField(max_length=50, unique=True, db_index=True)  # Primary identifier
    tg_username = models.CharField(max_length=255, blank=True, null=True)
    tg_data = models.JSONField(default=dict, blank=True)  # Raw Telegram user data
    preferred_language = models.CharField(max_length=10, choices=Language.choices(), default=Language.AMHARIC.value)
    active_subscription = models.ForeignKey('Subscription', on_delete=models.SET_NULL, null=True, blank=True, related_name='active_users')
    expiry_date = models.DateTimeField(null=True, blank=True)  # Denormalized for quick checks

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("User Profile")
        verbose_name_plural = _("User Profiles")
        indexes = [models.Index(fields=['tg_id', 'expiry_date'])]

    def __str__(self):
        return f"User {self.tg_username}"

    def is_subscribed(self):
        expiry_date = self.expiry_date or timezone.now() + timedelta(days=30)
        return self.active_subscription is not None and expiry_date > timezone.now()

    # Optimization: Cache subscription checks
    @property
    def available_exams_count(self):
        if not self.is_subscribed():
            return 1  # Free tier
        return self.active_subscription.tier.max_exam_number


class SubscriptionTier(models.Model):
    """Defines tiers (S0 free, S1, etc.). 
        Static config, not per-user.
        Acts as container for Exams.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    duration_days = models.PositiveIntegerField()  # e.g., 30 for 1mo
    max_exam_number = models.PositiveIntegerField(default=0)
    ai_assistance_enabled = models.BooleanField(default=False)
    personalized_feedback_enabled = models.BooleanField(default=False)
    full_road_sign_quiz = models.BooleanField(default=False)  # Free has limited
    order = models.PositiveSmallIntegerField(default=0, verbose_name=_("Display Order"))
    popular = models.BooleanField(default=False)
    
    unlimited_practice = models.BooleanField(default=False, help_text=_("Unlimited attempts on exams"))
    offline_access = models.BooleanField(default=True, help_text=_("Allow offline exam sync"))
    priority_support = models.BooleanField(default=False)
    ad_free = models.BooleanField(default=True)
    is_free = models.BooleanField(default=False, help_text=_("True if this is the free tier"))
    
    exams = models.ManyToManyField('core.Exam', related_name='tiers', blank=True)  # Pre-allocated Exams by admin
    
    

    class Meta:
        verbose_name = _("Subscription Tier")
        verbose_name_plural = _("Subscription Tiers")
        ordering = ['price']

    def __str__(self):
        # Fallback display in admin — use English translation if available
        trans = self.translations.filter(language='en').first()
        if trans and trans.name:
            return trans.name
        return f"Tier {self.id} ({self.price} ETB)"

    @property
    def display_name(self):
        """Convenient property for templates/serializers"""
        from django.conf import settings
        lang = settings.LANGUAGE_CODE
        trans = self.translations.filter(language=lang).first()
        if trans and trans.name:
            return trans.name
        return self.translations.filter(language='en').first().name if self.translations.filter(language='en').exists() else f"Tier {self.price}"

class Subscription(models.Model):
    """User's active/past subscription. Links to tier; users inherit tier's exams."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='subscriptions')
    tier = models.ForeignKey(SubscriptionTier, on_delete=models.PROTECT)
    start_date = models.DateTimeField(auto_now_add=True)
    expiry_date = models.DateTimeField()  # Computed on save
    is_active = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

        
    class Meta:
        verbose_name = _("Subscription")
        verbose_name_plural = _("Subscriptions")
        indexes = [
            models.Index(fields=['user_profile', 'tier']),
            models.Index(fields=['user_profile', 'is_active']),
            models.Index(fields=['expiry_date']),
        ]

    def save(self, *args, **kwargs):
        if not self.expiry_date:
            start_date = self.start_date or timezone.now()
            self.expiry_date = start_date + timedelta(days=self.tier.duration_days)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.tier} - {self.expiry_date}"

class SubscriptionTierTranslation(models.Model):
    tier = models.ForeignKey(SubscriptionTier, on_delete=models.CASCADE, related_name='translations')
    language = models.CharField(max_length=10, choices=Language.choices())
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    class Meta:
        unique_together = ['tier', 'language']
        verbose_name = _("Subscription Tier Translation")
        verbose_name_plural = _("Subscription Tier Translations")

    def __str__(self):
        return f"{self.tier.id} - {self.get_language_display()}: {self.name}"
    
class ExamAttempt(models.Model):
    class Status(models.TextChoices):
        STARTED = 'STARTED', _('Started')
        COMPLETED = 'COMPLETED', _('Completed')
        ABANDONED = 'ABANDONED', _('Abandoned')

    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    user_profile = models.ForeignKey(
        UserProfile, 
        on_delete=models.CASCADE, 
        related_name='attempts'
    )
    exam = models.ForeignKey(
        Exam, 
        on_delete=models.CASCADE, 
        related_name='attempts'
    )
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True)
    timestamp = models.DateTimeField(auto_now=True)
    score = models.DecimalField(
        max_digits=4,        # allows 100.0
        decimal_places=1,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(100),
        ]
    ) # Calculated server-side
    is_passed = models.BooleanField(null=True)  # Computed based on score >= exam.passing_score
    raw_answers_json = models.JSONField(default=dict)  # {question_id: choice_id}
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.STARTED)
    deleted_at = models.DateTimeField(null=True, blank=True)
    class Meta:
        verbose_name = _("Exam Attempt")
        verbose_name_plural = _("Exam Attempts")
        # unique_together = ['user_profile', 'exam']  # One attempt per exam per user
        indexes = [
            models.Index(fields=['user_profile', 'status']),
            models.Index(fields=['deleted_at']),
        ]

    def calculate_score(self):
        """Server-side score calculation with pass/fail."""
        if not self.raw_answers_json:
            return
        correct_count = 0
        for q_id, c_id in self.raw_answers_json.items():
            try:
                choice = AnswerChoice.objects.get(id=c_id, question_id=q_id)
                if choice.is_correct:
                    correct_count += 1
            except AnswerChoice.DoesNotExist:
                pass  # Invalid answer, count as wrong
        total_questions = len(self.raw_answers_json)
        self.score = (correct_count / total_questions * 100) if total_questions else 0
        self.is_passed = self.score >= self.exam.passing_score
        self.status = self.Status.COMPLETED
        self.end_time = timezone.now()
        self.save()
        
    def delete(self, *args, **kwargs):
        """Override delete to soft-delete"""
        self.deleted_at = timezone.now()
        self.status = self.Status.ABANDONED
        self.save()

    def hard_delete(self, *args, **kwargs):
        """For admin use only"""
        super().delete(*args, **kwargs)
   