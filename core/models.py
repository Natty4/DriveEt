# core/models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal
import uuid
import enum


class Language(enum.Enum):
    """Language enum for consistent usage across the application"""
    ENGLISH = 'en'
    AMHARIC = 'am'
    TIGRIGNA = 'ti'
    AFAN_OROMO = 'or'
    
    @classmethod
    def choices(cls):
        return [(member.value, member.name.replace('_', ' ').title()) for member in cls]
    
    @classmethod
    def values(cls):
        return [member.value for member in cls]

class QuestionCategory(models.Model):
    """Category for questions (e.g., Road Signs, Traffic Rules, Vehicle Handling, Driver Ethics)"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True, verbose_name=_("Code"))  # e.g., SIGN, RULES, VEHICLE
    order = models.PositiveSmallIntegerField(default=0, verbose_name=_("Display Order"))
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Question Category")
        verbose_name_plural = _("Question Categories")
        ordering = ['order', 'code']

    def __str__(self):
        return self.code

class QuestionCategoryTranslation(models.Model):
    """Multi-language support for question category names and descriptions"""
    category = models.ForeignKey(
        QuestionCategory,
        on_delete=models.CASCADE,
        related_name='translations'
    )
    language = models.CharField(
        max_length=10,
        choices=Language.choices(),
        default=Language.ENGLISH.value
    )
    name = models.CharField(max_length=200, verbose_name=_("Name"))
    description = models.TextField(verbose_name=_("Description"), blank=True)

    class Meta:
        verbose_name = _("Question Category Translation")
        verbose_name_plural = _("Question Category Translations")
        unique_together = ['category', 'language']
        ordering = ['language']

    def __str__(self):
        return f"{self.category.code} - {self.get_language_display()}"

class RoadSignCategory(models.Model):
    """Category for grouping road signs (e.g., Warning, Regulatory, Informative)"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True, verbose_name=_("Code"))
    order = models.PositiveSmallIntegerField(default=0, verbose_name=_("Display Order"))
    
    class Meta:
        verbose_name = _("Road Sign Category")
        verbose_name_plural = _("Road Sign Categories")
        ordering = ['order', 'code']
    
    def __str__(self):
        return self.code

class RoadSignCategoryTranslation(models.Model):
    """Translation for road sign category names"""
    category = models.ForeignKey(
        RoadSignCategory,
        on_delete=models.CASCADE,
        related_name='translations'
    )
    language = models.CharField(
        max_length=10,
        choices=Language.choices(),
        default=Language.ENGLISH.value
    )
    name = models.CharField(max_length=200, verbose_name=_("Name"))
    description = models.TextField(verbose_name=_("Description"), blank=True)
    
    class Meta:
        verbose_name = _("Road Sign Category Translation")
        verbose_name_plural = _("Road Sign Category Translations")
        unique_together = ['category', 'language']
        ordering = ['language']
    
    def __str__(self):
        return f"{self.category.code} - {self.get_language_display()}"


class RoadSign(models.Model):
    """Road sign model with category support"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=50, unique=True, help_text=_("Internal code for the road sign"))
    image = models.ImageField(upload_to='road_signs/')
    category = models.ForeignKey(
        RoadSignCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='road_signs',
        verbose_name=_("Category")
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("Road Sign")
        verbose_name_plural = _("Road Signs")
        ordering = ['code']
        indexes = [
            models.Index(fields=['category']),
            models.Index(fields=['code']),
        ]
    
    def __str__(self):
        return f"{self.code}"
    
    @property
    def name(self):
        """Get name in current language or English as fallback"""
        translation = self.translations.filter(language='en').first()
        return translation.name if translation else self.code
    
    def get_translation(self, language_code='en'):
        """Get translation for specific language"""
        return self.translations.filter(language=language_code).first()
    
    def get_all_translations(self):
        """Get all translations as a dictionary"""
        translations = {}
        for translation in self.translations.all():
            translations[translation.language] = {
                'name': translation.name,
                'meaning': translation.meaning,
                'detailed_explanation': translation.detailed_explanation
            }
        return translations
    
    def get_translations_by_language(self, language_code='en'):
        """Get translations for specific language, fallback to English"""
        translation = self.translations.filter(language=language_code).first()
        if not translation and language_code != 'en':
            translation = self.translations.filter(language='en').first()
        return translation


class RoadSignTranslation(models.Model):
    """Translation for road sign with separate meaning and detailed explanation"""
    road_sign = models.ForeignKey(
        RoadSign, 
        on_delete=models.CASCADE, 
        related_name='translations'
    )
    language = models.CharField(
        max_length=10, 
        choices=Language.choices(),
        default=Language.ENGLISH.value
    )
    name = models.CharField(max_length=200, verbose_name=_("Name"))
    meaning = models.CharField(max_length=500, verbose_name=_("Meaning"), help_text=_("Concise meaning for quick reference"))
    detailed_explanation = models.TextField(
        verbose_name=_("Detailed Explanation"),
        help_text=_("Rich content including HTML, images, GIFs, video/audio URLs for complete learning")
    )
    
    class Meta:
        verbose_name = _("Road Sign Translation")
        verbose_name_plural = _("Road Sign Translations")
        unique_together = ['road_sign', 'language']
        ordering = ['language']
        indexes = [
            models.Index(fields=['road_sign', 'language']),
            models.Index(fields=['name']),
        ]
    
    def __str__(self):
        return f"{self.road_sign.code} - {self.get_language_display()}"


class Question(models.Model):
    """Question model with explicit question type"""
    
    class QuestionType(models.TextChoices):
        IT = 'IT', _('Image to Text')  # Show image, choose text answer
        TI = 'TI', _('Text to Image')  # Show text, choose image answer
        TT = 'TT', _('Text to Text')  # Show text, choose text answer
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    category = models.ForeignKey(
        QuestionCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,  # Allow temporary null during migration
        related_name='questions',
        verbose_name=_("Category")
    )
        
    road_sign_context = models.ForeignKey(
        RoadSign, 
        on_delete=models.CASCADE, 
        related_name='questions',
        verbose_name=_("Associated Road Sign"),
        help_text=_("The road sign this question is about"),
        null=True,
        blank=True,
    )
    question_type = models.CharField(
        max_length=2,
        choices=QuestionType.choices,
        default=QuestionType.IT,
        verbose_name=_("Question Type")
    )
    is_premium = models.BooleanField(default=False, verbose_name=_("Premium Question"))
    difficulty = models.PositiveSmallIntegerField(
        choices=[(1, 'Easy'), (2, 'Medium'), (3, 'Hard')],
        default=2
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("Question")
        verbose_name_plural = _("Questions")
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['road_sign_context']),
            models.Index(fields=['is_premium', 'difficulty']),
        ]
    
    def __str__(self):
        translation = self.translations.filter(language='en').first()
        return f"Question: {translation.content[:50]}..." if translation else f"Question {self.id}"
    
    @property
    def is_image_to_text(self):
        return self.question_type == self.QuestionType.IT
    
    @property
    def is_text_to_image(self):
        return self.question_type == self.QuestionType.TI
    
    @property
    def is_text_to_text(self):
        return self.question_type == self.QuestionType.TT


class QuestionTranslation(models.Model):
    """Translation for question content"""
    question = models.ForeignKey(
        Question, 
        on_delete=models.CASCADE, 
        related_name='translations'
    )
    language = models.CharField(
        max_length=10, 
        choices=Language.choices(),
        default=Language.ENGLISH.value
    )
    content = models.TextField(verbose_name=_("Content"))
    
    class Meta:
        verbose_name = _("Question Translation")
        verbose_name_plural = _("Question Translations")
        unique_together = ['question', 'language']
        ordering = ['language']
    
    def __str__(self):
        return f"Q{self.question.id} - {self.get_language_display()}"


class AnswerChoice(models.Model):
    """Answer choices for questions - can be text or image (road sign)"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    question = models.ForeignKey(
        Question, 
        on_delete=models.CASCADE, 
        related_name='choices'
    )
    road_sign_option = models.ForeignKey(
        RoadSign,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='answer_choices',
        verbose_name=_("Road Sign Option"),
        help_text=_("For Text→Image questions: the road sign image option")
    )
    is_correct = models.BooleanField(default=False, verbose_name=_("Correct Answer"))
    order = models.PositiveSmallIntegerField(default=0, verbose_name=_("Display Order"))
    
    class Meta:
        verbose_name = _("Answer Choice")
        verbose_name_plural = _("Answer Choices")
        ordering = ['order']
        unique_together = ['question', 'order']
    
    def __str__(self):
        if self.road_sign_option:
            return f"Image: {self.road_sign_option.code}"
        translation = self.translations.filter(language='en').first()
        return f"{translation.text[:50]}..." if translation else f"Choice {self.id}"
    
    @property
    def is_image_option(self):
        return self.road_sign_option is not None


class AnswerChoiceTranslation(models.Model):
    """Translation for answer choice text"""
    answer_choice = models.ForeignKey(
        AnswerChoice, 
        on_delete=models.CASCADE, 
        related_name='translations'
    )
    language = models.CharField(
        max_length=10, 
        choices=Language.choices(),
        default=Language.ENGLISH.value
    )
    text = models.CharField(max_length=500, verbose_name=_("Text"))
    
    class Meta:
        verbose_name = _("Answer Choice Translation")
        verbose_name_plural = _("Answer Choice Translations")
        unique_together = ['answer_choice', 'language']
        ordering = ['language']
    
    def __str__(self):
        return f"A{self.answer_choice.id} - {self.get_language_display()}"


class Explanation(models.Model):
    """Detailed explanation for questions"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    question = models.OneToOneField(
        Question, 
        on_delete=models.CASCADE, 
        related_name='explanation'
    )
    media_url = models.URLField(blank=True, null=True, verbose_name=_("Media URL"))
    media_type = models.CharField(
        max_length=20,
        choices=[('image', 'Image'), ('video', 'Video'), ('gif', 'GIF'), ('audio', 'Audio')],
        blank=True,
        null=True
    )
    
    class Meta:
        verbose_name = _("Explanation")
        verbose_name_plural = _("Explanations")
    
    def __str__(self):
        return f"Explanation for Q{self.question.id}"


class ExplanationTranslation(models.Model):
    """Translation for explanation details"""
    explanation = models.ForeignKey(
        Explanation, 
        on_delete=models.CASCADE, 
        related_name='translations'
    )
    language = models.CharField(
        max_length=10, 
        choices=Language.choices(),
        default=Language.ENGLISH.value
    )
    detail = models.TextField(verbose_name=_("Detail"))
    
    class Meta:
        verbose_name = _("Explanation Translation")
        verbose_name_plural = _("Explanation Translations")
        unique_together = ['explanation', 'language']
        ordering = ['language']
    
    def __str__(self):
        return f"Exp{self.explanation.id} - {self.get_language_display()}"


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
        choices=MethodType,
        default=MethodType.MOBILE_WALLET
        
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=150.00,
        verbose_name=_("Required Amount"),
        help_text=_("Amount in ETB for Pro subscription")
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


class UserProgress(models.Model):
    """User quiz progress tracking"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='progress_records'
    )
    question = models.ForeignKey(
        Question, 
        on_delete=models.CASCADE, 
        related_name='user_progress'
    )
    selected_answer = models.ForeignKey(
        AnswerChoice, 
        on_delete=models.CASCADE,
        related_name='user_selections'
    )
    is_correct = models.BooleanField()
    time_taken = models.FloatField(help_text="Time taken in seconds", blank=True, null=True)
    session_id = models.CharField(max_length=100, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _("User Progress")
        verbose_name_plural = _("User Progress")
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['session_id']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {'Correct' if self.is_correct else 'Incorrect'}"


class UserProfile(models.Model):
    """Extended user profile with bundle system"""
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='profile'
    )
    telegram_id = models.BigIntegerField(unique=True, blank=True, null=True)
    telegram_username = models.CharField(max_length=100, blank=True, null=True)
    telegram_data = models.JSONField(default=dict, blank=True)
    
    # Bundle info (replaces subscription)
    active_bundle = models.ForeignKey(
        'UserBundle',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='active_users',
        verbose_name=_("Active Bundle")
    )
    
    
    # Offline cache token for PWA (now bundle-based)
    offline_cache_token = models.UUIDField(default=uuid.uuid4, editable=False)
    offline_cache_generated = models.DateTimeField(blank=True, null=True)
    
    # Progress tracking
    total_exam_attempts = models.PositiveIntegerField(default=0)
    total_practice_questions = models.PositiveIntegerField(default=0)
    correct_answers = models.PositiveIntegerField(default=0)
    highest_exam_score = models.FloatField(default=0)
    last_active = models.DateTimeField(auto_now=True)
    
    # Preferences
    preferred_language = models.CharField(
        max_length=10,
        choices=Language.choices(),
        default=Language.ENGLISH.value
    )
    exam_time_limit = models.IntegerField(default=1800, help_text=_("Exam time limit in seconds"))
    questions_per_exam = models.IntegerField(default=50)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("User Profile")
        verbose_name_plural = _("User Profiles")
        indexes = [
            models.Index(fields=['telegram_id']),
            models.Index(fields=['active_bundle']),
        ]
    
    def __str__(self):
        bundle_name = self.active_bundle.bundle_definition.name if self.active_bundle else 'No Bundle'
        return f"{self.user.username} - {bundle_name}"
    
    @property
    def accuracy(self):
        total_attempts = self.total_practice_questions + (self.total_exam_attempts * self.questions_per_exam)
        if total_attempts == 0:
            return 0
        return (self.correct_answers / total_attempts) * 100
    
    @property
    def has_active_bundle(self):
        """Check if user has an active, non-expired bundle"""
        if not self.active_bundle:
            return False
        return self.active_bundle.is_active and not self.active_bundle.is_expired
    
    @property
    def bundle_remaining_resources(self):
        """Get remaining resources from active bundle"""
        if not self.has_active_bundle:
            return None
        return self.active_bundle.get_remaining_resources()
    
    @property
    def is_pro_user(self):
        """Backward compatibility - check if user has active bundle"""
        return self.has_active_bundle
    
    @property
    def days_remaining(self):
        """Days remaining in active bundle"""
        if not self.has_active_bundle:
            return 0
        from django.utils import timezone
        delta = self.active_bundle.expiry_date - timezone.now()
        return max(0, delta.days)
    
    def activate_bundle(self, user_bundle):
        """Activate a bundle for the user"""
        self.active_bundle = user_bundle
        self.save(update_fields=['active_bundle', 'updated_at'])
    
    def generate_new_cache_token(self):
        """Generate a new offline cache token"""
        self.offline_cache_token = uuid.uuid4()
        self.offline_cache_generated = timezone.now()
        self.save()
        return self.offline_cache_token
        

# class SubscriptionPlan(models.Model):
#     """Different subscription plans (lifetime, 6 months, etc.)"""
    
#     class PlanType(models.TextChoices):
#         LIFETIME = 'lifetime', _('Lifetime Access')
#         YEARLY = 'yearly', _('A Year Access')
#         SIX_MONTHS = '6months', _('6 Months Access')
#         THREE_MONTHS = '3months', _('3 Months Access')
#         ONE_MONTH = '1month', _('1 Month Access')
    
#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     name = models.CharField(max_length=100, verbose_name=_("Plan Name"))
#     plan_type = models.CharField(
#         max_length=20,
#         choices=PlanType.choices,
#         verbose_name=_("Plan Type")
#     )
#     price_etb = models.DecimalField(
#         max_digits=10,
#         decimal_places=2,
#         verbose_name=_("Price (ETB)")
#     )
#     duration_days = models.IntegerField(
#         null=True,
#         blank=True,
#         verbose_name=_("Duration (days)"),
#         help_text=_("Null for lifetime access")
#     )
#     number_of_exam = models.IntegerField(
#         null=True,
#         blank=True,
#         verbose_name=_("Max Number of exam can be produced for this plan"),
#         help_text=_("Null for lifetime access")
#     )
#     recommended_plan = models.BooleanField(default=False, verbose_name=_("Recommended"))
#     is_active = models.BooleanField(default=True, verbose_name=_("Active"))
#     features = models.JSONField(
#         default=list,
#         verbose_name=_("Features"),
#         help_text=_("List of features for this plan")
#     )
#     order = models.PositiveSmallIntegerField(default=0, verbose_name=_("Display Order"))
    
#     class Meta:
#         verbose_name = _("Subscription Plan")
#         verbose_name_plural = _("Subscription Plans")
#         ordering = ['order', 'price_etb']
    
#     def __str__(self):
#         return f"{self.name} - {self.price_etb} ETB"
    
#     def save(self, *args, **kwargs):
#         # Set duration based on plan type if not specified
#         if not self.duration_days:
#             durations = {
#                 'lifetime': None,
#                 'yearly': 365,
#                 '6months': 180,
#                 '3months': 90,
#                 '1month': 30
#             }
#             self.duration_days = durations.get(self.plan_type)
#         super().save(*args, **kwargs)

# class UserSubscription(models.Model):
#     """Track user subscriptions"""
    
#     class PaymentStatus(models.TextChoices):
#         PENDING = 'pending', _('Pending')
#         COMPLETED = 'completed', _('Completed')
#         FAILED = 'failed', _('Failed')
#         REFUNDED = 'refunded', _('Refunded')
    
#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     user = models.ForeignKey(
#         'auth.User',
#         on_delete=models.CASCADE,
#         related_name='subscriptions'
#     )
#     plan = models.ForeignKey(
#         SubscriptionPlan,
#         on_delete=models.PROTECT,
#         related_name='user_subscriptions'
#     )
#     payment_method = models.ForeignKey(
#         'PaymentMethod',
#         on_delete=models.SET_NULL,
#         null=True,
#         blank=True
#     )
#     amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
#     payment_status = models.CharField(
#         max_length=20,
#         choices=PaymentStatus.choices,
#         default=PaymentStatus.PENDING
#     )
#     reference_number = models.CharField(max_length=100, blank=True)
#     transaction_id = models.CharField(max_length=100, blank=True)
#     starts_at = models.DateTimeField(auto_now_add=True)
#     expires_at = models.DateTimeField(null=True, blank=True)
#     is_active = models.BooleanField(default=True)
    
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)
    
#     class Meta:
#         verbose_name = _("User Subscription")
#         verbose_name_plural = _("User Subscriptions")
#         ordering = ['-created_at']
    
#     def __str__(self):
#         return f"{self.user.username} - {self.plan.name}"
    
#     def save(self, *args, **kwargs):
#         if not self.expires_at and self.plan.duration_days:
#             from django.utils import timezone
#             self.expires_at = timezone.now() + timezone.timedelta(days=self.plan.duration_days)
#         super().save(*args, **kwargs)


class ExamSession(models.Model):
    """Track exam attempts"""
    
    class ExamStatus(models.TextChoices):
        IN_PROGRESS = 'in_progress', _('In Progress')
        COMPLETED = 'completed', _('Completed')
        TIMED_OUT = 'timed_out', _('Timed Out')
        CANCELLED = 'cancelled', _('Cancelled')
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        'auth.User',
        on_delete=models.CASCADE,
        related_name='exam_sessions'
    )
    questions = models.ManyToManyField('Question', through='ExamQuestion')
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=ExamStatus.choices,
        default=ExamStatus.IN_PROGRESS
    )
    score = models.FloatField(null=True, blank=True)
    time_taken = models.IntegerField(null=True, blank=True, help_text=_("Time taken in seconds"))
    passed = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = _("Exam Session")
        verbose_name_plural = _("Exam Sessions")
        ordering = ['-start_time']
    
    def __str__(self):
        return f"Exam {self.id} - {self.user.username}"


class ExamQuestion(models.Model):
    """Questions used in an exam session"""
    exam_session = models.ForeignKey(ExamSession, on_delete=models.CASCADE)
    question = models.ForeignKey('Question', on_delete=models.CASCADE)
    order = models.IntegerField()
    selected_answer = models.ForeignKey(
        'AnswerChoice',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    is_correct = models.BooleanField(null=True, blank=True)
    time_spent = models.FloatField(null=True, blank=True, help_text=_("Time spent in seconds"))
    
    class Meta:
        ordering = ['order']
        unique_together = ['exam_session', 'question']
    
    def __str__(self):
        return f"{self.exam_session.id} - Q{self.order}"



class ArticleCategory(models.Model):
    """Categories for articles and legal documents"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = _("Article Category")
        verbose_name_plural = _("Article Categories")
        ordering = ['order', 'name']
    
    def __str__(self):
        return self.name


class Article(models.Model):
    """Articles, legal rules, and learning materials"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    content = models.TextField()
    category = models.ForeignKey(
        ArticleCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='articles'
    )
    is_premium = models.BooleanField(default=False)
    order = models.PositiveSmallIntegerField(default=0)
    tags = models.JSONField(default=list, blank=True)
    views = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("Article")
        verbose_name_plural = _("Articles")
        ordering = ['order', '-created_at']
    
    def __str__(self):
        return self.title


class AIChatHistory(models.Model):
    """Store AI chat history for users"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        'auth.User',
        on_delete=models.CASCADE,
        related_name='ai_chats'
    )
    session_id = models.CharField(max_length=100)
    question = models.TextField()
    answer = models.TextField()
    tokens_used = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _("AI Chat History")
        verbose_name_plural = _("AI Chat Histories")
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.created_at.date()}"




# =================== Prepaid Bundle Models ===================

class BundleDefinition(models.Model):
    """
    Template for prepaid bundles
    Defines the resources and validity for a bundle type
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, verbose_name=_("Bundle Name"))
    code = models.CharField(max_length=50, unique=True, verbose_name=_("Bundle Code"))
    description = models.TextField(verbose_name=_("Description"), blank=True)
    
    # Resource quotas
    exam_quota = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Exam Attempts"),
        help_text=_("Number of exam attempts included (0 = unlimited)")
    )
    total_chat_quota = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Total Chat Quota"),
        help_text=_("Total AI chat messages included (0 = unlimited)")
    )
    daily_chat_limit = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Daily Chat Limit"),
        help_text=_("Daily limit for AI chat messages (0 = unlimited)")
    )
    search_quota = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Search Quota"),
        help_text=_("Number of searchable questions (0 = unlimited)")
    )
    has_unlimited_road_sign_quiz = models.BooleanField(
        default=False,
        verbose_name=_("Unlimited Road Sign Quiz"),
        help_text=_("Unlimited access to road sign quizzes")
    )
    
    # Validity and pricing
    validity_days = models.PositiveIntegerField(
        verbose_name=_("Validity (days)"),
        help_text=_("Number of days the bundle is valid for")
    )
    price_etb = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_("Price (ETB)"),
        validators=[MinValueValidator(Decimal('0.00'))]
    )

    recommended = models.BooleanField(default=False, verbose_name=_("Recommended"))
    is_active = models.BooleanField(default=True, verbose_name=_("Active"))
    order = models.PositiveIntegerField(default=0, verbose_name=_("Display Order"))
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("Bundle Definition")
        verbose_name_plural = _("Bundle Definitions")
        ordering = ['order', 'price_etb']
    
    def __str__(self):
        return f"{self.name} - {self.price_etb} ETB"
    
    @property
    def is_unlimited_exams(self):
        return self.exam_quota == 0
    
    @property
    def is_unlimited_chats(self):
        return self.total_chat_quota == 0
    
    @property
    def is_unlimited_search(self):
        return self.search_quota == 0


class UserBundle(models.Model):
    """
    Active bundle instance for a user
    Tracks resource balances and validity
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='bundles',
        verbose_name=_("User")
    )
    bundle_definition = models.ForeignKey(
        BundleDefinition,
        on_delete=models.PROTECT,
        related_name='user_bundles',
        verbose_name=_("Bundle Definition")
    )
    
    # Purchase and validity
    purchase_date = models.DateTimeField(auto_now_add=True, verbose_name=_("Purchase Date"))
    expiry_date = models.DateTimeField(verbose_name=_("Expiry Date"))
    is_active = models.BooleanField(default=True, verbose_name=_("Active"))
    
    # Current balances (atomic updates only!)
    exams_remaining = models.PositiveIntegerField(default=0, verbose_name=_("Exams Remaining"))
    chats_remaining = models.PositiveIntegerField(default=0, verbose_name=_("Chats Remaining"))
    search_remaining = models.PositiveIntegerField(default=0, verbose_name=_("Search Remaining"))
    total_chats_consumed = models.PositiveIntegerField(default=0, verbose_name=_("Total Chats Consumed"))
    
    # Daily chat tracking
    last_chat_reset = models.DateTimeField(
        default=timezone.now,
        verbose_name=_("Last Chat Reset")
    )
    daily_chats_used = models.PositiveIntegerField(default=0, verbose_name=_("Daily Chats Used"))
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("User Bundle")
        verbose_name_plural = _("User Bundles")
        ordering = ['-purchase_date']
        indexes = [
            models.Index(fields=['user', 'is_active', 'expiry_date']),
            models.Index(fields=['expiry_date']),
            models.Index(fields=['last_chat_reset']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.bundle_definition.name}"
    
    def save(self, *args, **kwargs):
        # Set initial balances from bundle definition if this is a new instance
        if not self.pk:
            self.expiry_date = timezone.now() + timezone.timedelta(
                days=self.bundle_definition.validity_days
            )
            self.exams_remaining = self.bundle_definition.exam_quota
            self.chats_remaining = self.bundle_definition.total_chat_quota
            self.search_remaining = self.bundle_definition.search_quota
            self.last_chat_reset = timezone.now()
        
        super().save(*args, **kwargs)
    
    @property
    def is_expired(self):
        return self.expiry_date < timezone.now()
    
    @property
    def can_use_exam(self):
        if not self.is_active:
            return False
        if self.is_expired:
            return False
        if self.bundle_definition.is_unlimited_exams:
            return True
        return self.exams_remaining > 0
    
    @property
    def can_use_chat(self):
        if not self.is_active:
            return False
        if self.is_expired:
            return False
        
        # Check daily limit
        if self.bundle_definition.daily_chat_limit > 0:
            # Reset daily counter if needed
            self._reset_daily_chat_if_needed()
            if self.daily_chats_used >= self.bundle_definition.daily_chat_limit:
                return False
        
        # Check total quota
        if self.bundle_definition.is_unlimited_chats:
            return True
        return self.chats_remaining > 0
    
    @property
    def can_use_search(self):
        if not self.is_active:
            return False
        if self.is_expired:
            return False
        if self.bundle_definition.is_unlimited_search:
            return True
        return self.search_remaining > 0
    
    @property
    def has_unlimited_road_sign_quiz(self):
        return self.bundle_definition.has_unlimited_road_sign_quiz
    
    def _reset_daily_chat_if_needed(self):
        """Reset daily chat counter if it's a new day"""
        from django.utils import timezone
        now = timezone.now()
        
        if (now - self.last_chat_reset).days >= 1:
            self.daily_chats_used = 0
            self.last_chat_reset = now
            self.save(update_fields=['daily_chats_used', 'last_chat_reset'])
    
    def get_remaining_resources(self):
        """Get dictionary of remaining resources"""
        return {
            'exams_remaining': self.exams_remaining,
            'chats_remaining': self.chats_remaining,
            'search_remaining': self.search_remaining,
            'daily_chats_used': self.daily_chats_used,
            'daily_chat_limit': self.bundle_definition.daily_chat_limit,
            'total_chats_consumed': self.total_chats_consumed,
            'is_active': self.is_active,
            'expiry_date': self.expiry_date,
            'days_remaining': max(0, (self.expiry_date - timezone.now()).days),
        }


class ResourceTransaction(models.Model):
    """
    Ledger for tracking all resource usage
    Ensures atomic updates and provides audit trail
    """
    class TransactionType(models.TextChoices):
        PURCHASE = 'purchase', _('Bundle Purchase')
        CONSUME = 'consume', _('Resource Consumption')
        REFUND = 'refund', _('Resource Refund')
        RESET = 'reset', _('Daily Reset')
        EXPIRY = 'expiry', _('Bundle Expiry')
    
    class ResourceType(models.TextChoices):
        EXAM = 'exam', _('Exam Attempt')
        CHAT = 'chat', _('AI Chat')
        SEARCH = 'search', _('Search')
        ROAD_SIGN = 'road_sign', _('Road Sign Quiz')
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='resource_transactions',
        verbose_name=_("User")
    )
    user_bundle = models.ForeignKey(
        UserBundle,
        on_delete=models.CASCADE,
        related_name='transactions',
        verbose_name=_("User Bundle"),
        null=True,
        blank=True
    )
    
    transaction_type = models.CharField(
        max_length=20,
        choices=TransactionType.choices,
        verbose_name=_("Transaction Type")
    )
    resource_type = models.CharField(
        max_length=20,
        choices=ResourceType.choices,
        null=True,
        blank=True,
        verbose_name=_("Resource Type")
    )
    
    # Quantity changes (positive for additions, negative for consumption)
    quantity = models.IntegerField(verbose_name=_("Quantity"))
    
    # Balances before and after
    exams_before = models.PositiveIntegerField(null=True, blank=True, verbose_name=_("Exams Before"))
    exams_after = models.PositiveIntegerField(null=True, blank=True, verbose_name=_("Exams After"))
    chats_before = models.PositiveIntegerField(null=True, blank=True, verbose_name=_("Chats Before"))
    chats_after = models.PositiveIntegerField(null=True, blank=True, verbose_name=_("Chats After"))
    search_before = models.PositiveIntegerField(null=True, blank=True, verbose_name=_("Search Before"))
    search_after = models.PositiveIntegerField(null=True, blank=True, verbose_name=_("Search After"))
    
    # Metadata
    reference = models.CharField(max_length=100, blank=True, verbose_name=_("Reference"))
    description = models.TextField(blank=True, verbose_name=_("Description"))
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name=_("IP Address"))
    user_agent = models.TextField(blank=True, verbose_name=_("User Agent"))
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _("Resource Transaction")
        verbose_name_plural = _("Resource Transactions")
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['transaction_type', 'resource_type']),
            models.Index(fields=['user_bundle']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.get_transaction_type_display()} - {self.quantity}"


class BundleOrder(models.Model):
    """
    Order for bundle purchase before payment verification
    """
    class OrderStatus(models.TextChoices):
        PENDING = 'pending', _('Pending Payment')
        PAYMENT_VERIFIED = 'payment_verified', _('Payment Verified')
        INSUFFICIENT_FUNDS = 'insufficient_funds', _('Insufficient Funds')
        COMPLETED = 'completed', _('Order Completed')
        CANCELLED = 'cancelled', _('Order Cancelled')
        EXPIRED = 'expired', _('Order Expired')
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='bundle_orders',
        verbose_name=_("User")
    )
    bundle_definition = models.ForeignKey(
        BundleDefinition,
        on_delete=models.PROTECT,
        related_name='orders',
        verbose_name=_("Selected Bundle")
    )
    
    # Order details
    order_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_("Order Amount (ETB)")
    )
    status = models.CharField(
        max_length=20,
        choices=OrderStatus.choices,
        default=OrderStatus.PENDING,
        verbose_name=_("Order Status")
    )
    
    # Payment verification
    payment_method = models.ForeignKey(
        'PaymentMethod',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bundle_orders',
        verbose_name=_("Payment Method")
    )
    reference_number = models.CharField(max_length=100, blank=True, verbose_name=_("Reference Number"))
    verified_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_("Verified Amount")
    )
    verified_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Verified At"))
    
    # Resulting bundle (if order completed)
    resulting_bundle = models.OneToOneField(
        UserBundle,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='order',
        verbose_name=_("Resulting Bundle")
    )
    
    # Alternative bundles suggested (if insufficient funds)
    suggested_bundles = models.ManyToManyField(
        BundleDefinition,
        through='OrderBundleSuggestion',
        related_name='suggested_in_orders',
        verbose_name=_("Suggested Bundles")
    )
    
    # Metadata
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name=_("IP Address"))
    user_agent = models.TextField(blank=True, verbose_name=_("User Agent"))
    expires_at = models.DateTimeField(verbose_name=_("Expires At"))
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("Bundle Order")
        verbose_name_plural = _("Bundle Orders")
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['status', 'expires_at']),
            models.Index(fields=['reference_number']),
        ]
    
    def __str__(self):
        return f"Order {self.id} - {self.user.username} - {self.bundle_definition.name}"
    
    def save(self, *args, **kwargs):
        if not self.expires_at:
            from django.utils import timezone
            self.expires_at = timezone.now() + timezone.timedelta(hours=24)  # 24-hour expiry
        super().save(*args, **kwargs)
    
    @property
    def is_expired(self):
        from django.utils import timezone
        return self.expires_at < timezone.now()
    
    @property
    def amount_difference(self):
        """Calculate difference between verified amount and order amount"""
        if self.verified_amount:
            return self.verified_amount - self.order_amount
        return None
    
    @property
    def can_be_completed(self):
        """Check if order can be completed"""
        return (
            self.status == self.OrderStatus.PAYMENT_VERIFIED and
            self.verified_amount and
            self.verified_amount >= self.order_amount and
            not self.is_expired
        )


class OrderBundleSuggestion(models.Model):
    """
    Suggested bundles for insufficient funds
    """
    order = models.ForeignKey(BundleOrder, on_delete=models.CASCADE)
    bundle_definition = models.ForeignKey(BundleDefinition, on_delete=models.CASCADE)
    reason = models.CharField(max_length=200, verbose_name=_("Suggestion Reason"))
    order_score = models.FloatField(default=0.0, verbose_name=_("Recommendation Score"))
    
    class Meta:
        unique_together = ['order', 'bundle_definition']
        ordering = ['-order_score']
   

class BundlePurchase(models.Model):
    """
    Transaction log for bundle purchases
    Links to payment verification
    """
    class PaymentStatus(models.TextChoices):
        PENDING = 'pending', _('Pending')
        COMPLETED = 'completed', _('Completed')
        FAILED = 'failed', _('Failed')
        REFUNDED = 'refunded', _('Refunded')
        CANCELLED = 'cancelled', _('Cancelled')
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='bundle_purchases',
        verbose_name=_("User")
    )
    bundle_definition = models.ForeignKey(
        BundleDefinition,
        on_delete=models.PROTECT,
        related_name='purchases',
        verbose_name=_("Bundle Definition")
    )
    order = models.OneToOneField(
        BundleOrder,
        on_delete=models.CASCADE,
        related_name='final_purchase',
        verbose_name=_("Source Order")
    )
    # Payment details
    amount_paid = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_("Amount Paid (ETB)")
    )
    payment_method = models.ForeignKey(
        'PaymentMethod',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bundle_purchases',
        verbose_name=_("Payment Method")
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
        verbose_name=_("Payment Status")
    )
    
    # References
    reference_number = models.CharField(max_length=100, blank=True, verbose_name=_("Reference Number"))
    transaction_id = models.CharField(max_length=100, blank=True, verbose_name=_("Transaction ID"))
    
    # Resulting user bundle
    user_bundle = models.OneToOneField(
        UserBundle,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='purchase_record',
        verbose_name=_("Resulting User Bundle")
    )
    
    # Verification
    verified_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Verified At"))
    verified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_purchases',
        verbose_name=_("Verified By")
    )
    
    # Metadata
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name=_("IP Address"))
    user_agent = models.TextField(blank=True, verbose_name=_("User Agent"))
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("Bundle Purchase")
        verbose_name_plural = _("Bundle Purchases")
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'payment_status']),
            models.Index(fields=['payment_status', 'created_at']),
            models.Index(fields=['reference_number']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.bundle_definition.name} - {self.amount_paid} ETB"
    
    def create_user_bundle(self):
        """Create UserBundle when payment is completed"""
        if self.payment_status == self.PaymentStatus.COMPLETED and not self.user_bundle:
            user_bundle = UserBundle.objects.create(
                user=self.user,
                bundle_definition=self.bundle_definition
            )
            self.user_bundle = user_bundle
            self.save()
            return user_bundle
        return None























































# from django.db import models
# from django.contrib.auth.models import User
# from django.utils.translation import gettext_lazy as _
# import uuid


# class Language(models.TextChoices):
#     ENGLISH = 'en', _('English')
#     AMHARIC = 'am', _('Amharic')
#     TIGRIGNA = 'ti', _('Tigrigna')
#     AFAN_OROMO = 'or', _('Afan Oromo')
#     # Add more languages as needed


# class RoadSign(models.Model):
#     """Road sign model"""
#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     code = models.CharField(max_length=50, unique=True, help_text="Internal code for the road sign")
#     image = models.ImageField(upload_to='road_signs/')
    
#     # Metadata
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)
    
#     class Meta:
#         verbose_name = _("Road Sign")
#         verbose_name_plural = _("Road Signs")
#         ordering = ['code']
    
#     def __str__(self):
#         return f"{self.code}"
    
#     @property
#     def name(self):
#         """Get name in current language or English as fallback"""
#         translation = self.translations.filter(language='en').first()
#         return translation.name if translation else self.code
    
#     def get_translation(self, language_code='en'):
#         """Get translation for specific language"""
#         return self.translations.filter(language=language_code).first()


# class RoadSignTranslation(models.Model):
#     """Translation for road sign descriptions"""
#     road_sign = models.ForeignKey(
#         RoadSign, 
#         on_delete=models.CASCADE, 
#         related_name='translations'
#     )
#     language = models.CharField(
#         max_length=10, 
#         choices=Language.choices,
#         default=Language.ENGLISH
#     )
#     name = models.CharField(max_length=200, verbose_name=_("Name"))
#     description = models.TextField(verbose_name=_("Description"), blank=True)
    
#     class Meta:
#         verbose_name = _("Road Sign Translation")
#         verbose_name_plural = _("Road Sign Translations")
#         unique_together = ['road_sign', 'language']
#         ordering = ['language']
    
#     def __str__(self):
#         return f"{self.road_sign.code} - {self.get_language_display()}"


# class Question(models.Model):
#     """Question model"""
#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     road_sign = models.ForeignKey(
#         RoadSign, 
#         on_delete=models.CASCADE, 
#         related_name='questions',
#         verbose_name=_("Associated Road Sign")
#     )
#     is_premium = models.BooleanField(default=False, verbose_name=_("Premium Question"))
#     difficulty = models.PositiveSmallIntegerField(
#         choices=[(1, 'Easy'), (2, 'Medium'), (3, 'Hard')],
#         default=2
#     )
    
#     # Metadata
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)
    
#     class Meta:
#         verbose_name = _("Question")
#         verbose_name_plural = _("Questions")
#         ordering = ['-created_at']
    
#     def __str__(self):
#         translation = self.translations.filter(language='en').first()
#         return f"Question: {translation.content[:50]}..." if translation else f"Question {self.id}"


# class QuestionTranslation(models.Model):
#     """Translation for question content"""
#     question = models.ForeignKey(
#         Question, 
#         on_delete=models.CASCADE, 
#         related_name='translations'
#     )
#     language = models.CharField(
#         max_length=10, 
#         choices=Language.choices,
#         default=Language.ENGLISH
#     )
#     content = models.TextField(verbose_name=_("Content"))
    
#     class Meta:
#         verbose_name = _("Question Translation")
#         verbose_name_plural = _("Question Translations")
#         unique_together = ['question', 'language']
#         ordering = ['language']
    
#     def __str__(self):
#         return f"Q{self.question.id} - {self.get_language_display()}"


# class AnswerChoice(models.Model):
#     """Answer choices for questions"""
#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     question = models.ForeignKey(
#         Question, 
#         on_delete=models.CASCADE, 
#         related_name='choices'
#     )
#     is_correct = models.BooleanField(default=False, verbose_name=_("Correct Answer"))
#     order = models.PositiveSmallIntegerField(default=0, verbose_name=_("Display Order"))
    
#     class Meta:
#         verbose_name = _("Answer Choice")
#         verbose_name_plural = _("Answer Choices")
#         ordering = ['order']
#         unique_together = ['question', 'order']
    
#     def __str__(self):
#         translation = self.translations.filter(language='en').first()
#         return f"{translation.text[:50]}..." if translation else f"Choice {self.id}"


# class AnswerChoiceTranslation(models.Model):
#     """Translation for answer choice text"""
#     answer_choice = models.ForeignKey(
#         AnswerChoice, 
#         on_delete=models.CASCADE, 
#         related_name='translations'
#     )
#     language = models.CharField(
#         max_length=10, 
#         choices=Language.choices,
#         default=Language.ENGLISH
#     )
#     text = models.CharField(max_length=500, verbose_name=_("Text"))
    
#     class Meta:
#         verbose_name = _("Answer Choice Translation")
#         verbose_name_plural = _("Answer Choice Translations")
#         unique_together = ['answer_choice', 'language']
#         ordering = ['language']
    
#     def __str__(self):
#         return f"A{self.answer_choice.id} - {self.get_language_display()}"


# class Explanation(models.Model):
#     """Detailed explanation for questions"""
#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     question = models.OneToOneField(
#         Question, 
#         on_delete=models.CASCADE, 
#         related_name='explanation'
#     )
#     media_url = models.URLField(blank=True, null=True, verbose_name=_("Media URL"))
#     media_type = models.CharField(
#         max_length=20,
#         choices=[('image', 'Image'), ('video', 'Video'), ('gif', 'GIF')],
#         blank=True,
#         null=True
#     )
    
#     class Meta:
#         verbose_name = _("Explanation")
#         verbose_name_plural = _("Explanations")
    
#     def __str__(self):
#         return f"Explanation for Q{self.question.id}"


# class ExplanationTranslation(models.Model):
#     """Translation for explanation details"""
#     explanation = models.ForeignKey(
#         Explanation, 
#         on_delete=models.CASCADE, 
#         related_name='translations'
#     )
#     language = models.CharField(
#         max_length=10, 
#         choices=Language.choices,
#         default=Language.ENGLISH
#     )
#     detail = models.TextField(verbose_name=_("Detail"))
    
#     class Meta:
#         verbose_name = _("Explanation Translation")
#         verbose_name_plural = _("Explanation Translations")
#         unique_together = ['explanation', 'language']
#         ordering = ['language']
    
#     def __str__(self):
#         return f"Exp{self.explanation.id} - {self.get_language_display()}"


# class UserProfile(models.Model):
#     """Extended user profile with pro status"""
#     user = models.OneToOneField(
#         User, 
#         on_delete=models.CASCADE, 
#         related_name='profile'
#     )
#     telegram_id = models.BigIntegerField(unique=True, blank=True, null=True)
#     telegram_username = models.CharField(max_length=100, blank=True, null=True)
#     telegram_data = models.JSONField(default=dict, blank=True)
    
#     is_pro_user = models.BooleanField(default=False, verbose_name=_("Pro User"))
#     pro_since = models.DateTimeField(blank=True, null=True, verbose_name=_("Pro Since"))
#     pro_expires = models.DateTimeField(blank=True, null=True, verbose_name=_("Pro Expires"))
    
#     # Progress tracking
#     total_attempts = models.PositiveIntegerField(default=0)
#     correct_answers = models.PositiveIntegerField(default=0)
#     last_active = models.DateTimeField(auto_now=True)
    
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)
    
#     class Meta:
#         verbose_name = _("User Profile")
#         verbose_name_plural = _("User Profiles")
    
#     def __str__(self):
#         return f"{self.user.username} - {'Pro' if self.is_pro_user else 'Free'}"
    
#     @property
#     def accuracy(self):
#         if self.total_attempts == 0:
#             return 0
#         return (self.correct_answers / self.total_attempts) * 100


# class PaymentMethod(models.Model):
#     """Available payment methods"""
#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     name = models.CharField(max_length=100, verbose_name=_("Name"))
#     code = models.CharField(max_length=50, unique=True, verbose_name=_("Code"))
#     is_active = models.BooleanField(default=True, verbose_name=_("Active"))
#     order = models.PositiveSmallIntegerField(default=0, verbose_name=_("Display Order"))
    
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)
    
#     class Meta:
#         verbose_name = _("Payment Method")
#         verbose_name_plural = _("Payment Methods")
#         ordering = ['order', 'name']
    
#     def __str__(self):
#         return self.name


# class PaymentMethodTranslation(models.Model):
#     """Translation for payment method details and instructions"""
#     payment_method = models.ForeignKey(
#         PaymentMethod, 
#         on_delete=models.CASCADE, 
#         related_name='translations'
#     )
#     language = models.CharField(
#         max_length=10, 
#         choices=Language.choices,
#         default=Language.ENGLISH
#     )
#     account_details = models.TextField(verbose_name=_("Account Details"))
#     instruction = models.TextField(verbose_name=_("Instruction"))
    
#     class Meta:
#         verbose_name = _("Payment Method Translation")
#         verbose_name_plural = _("Payment Method Translations")
#         unique_together = ['payment_method', 'language']
#         ordering = ['language']
    
#     def __str__(self):
#         return f"{self.payment_method.name} - {self.get_language_display()}"


# class UserProgress(models.Model):
#     """User quiz progress tracking"""
#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     user = models.ForeignKey(
#         User, 
#         on_delete=models.CASCADE, 
#         related_name='progress_records'
#     )
#     question = models.ForeignKey(
#         Question, 
#         on_delete=models.CASCADE, 
#         related_name='user_progress'
#     )
#     selected_answer = models.ForeignKey(
#         AnswerChoice, 
#         on_delete=models.CASCADE,
#         related_name='user_selections'
#     )
#     is_correct = models.BooleanField()
#     time_taken = models.FloatField(help_text="Time taken in seconds", blank=True, null=True)
#     session_id = models.CharField(max_length=100, blank=True, null=True)
    
#     created_at = models.DateTimeField(auto_now_add=True)
    
#     class Meta:
#         verbose_name = _("User Progress")
#         verbose_name_plural = _("User Progress")
#         indexes = [
#             models.Index(fields=['user', 'created_at']),
#             models.Index(fields=['session_id']),
#         ]
    
#     def __str__(self):
#         return f"{self.user.username} - {'Correct' if self.is_correct else 'Incorrect'}"