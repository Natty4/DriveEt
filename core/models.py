# core/models.py

import enum
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from cloudinary.models import CloudinaryField
from common.constants import Language


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
    image = CloudinaryField(
        'image',
        folder='road_signs/',           # Auto-creates folder
        resource_type='image',
        null=True,
        blank=True
    )
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
        translation = self.translations.filter(language=settings.LANGUAGE_CODE).first() or self.translations.filter(language='en').first()
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
    associated_road_sign = models.ForeignKey(  # Renamed for clarity
        RoadSign,
        on_delete=models.SET_NULL,  # Changed to SET_NULL to avoid cascade delete if sign updated
        null=True,
        blank=True,
        related_name='questions',
        verbose_name=_("Associated Road Sign"),
        help_text=_("Link to road sign if this question is specifically about one; use for sign metadata/translations")
    )
    media_image = CloudinaryField(
        'image',
        folder='questions/',
        resource_type='image',
        null=True,
        blank=True,
        help_text="Upload image for IT/TI questions"
    )
    question_type = models.CharField(
        max_length=2,
        choices=QuestionType.choices,
        default=QuestionType.IT,
        verbose_name=_("Question Type")
    )
    difficulty = models.CharField(max_length=50, default='medium', verbose_name=_("Difficulty"))  # Added for filtering
    
    is_premium = models.BooleanField(default=True)
    unique = models.BooleanField(default=True, verbose_name=_("Unique"), help_text=_("If true, can only be used in one exam"))
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Question")
        verbose_name_plural = _("Questions")
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['associated_road_sign']),
            models.Index(fields=['difficulty']),
            models.Index(fields=['category']),
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
        # unique_together = ['question', 'order']

    def __str__(self):
        if self.road_sign_option:
            return f"Image: {self.road_sign_option.code}"
        translation = self.translations.filter(language='en').first()
        return f"{translation.text[:50]}..." if translation else f"Choice {self.id}"

    def save(self, *args, **kwargs):
        if not self.order:
            last = AnswerChoice.objects.filter(
                question=self.question
            ).order_by('-order').first()

            self.order = (last.order + 1) if last else 1

        super().save(*args, **kwargs)

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
    media_url = models.URLField(blank=True, null=True, verbose_name=_("Media URL"))  # Sanitize in views to prevent XSS
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


class Exam(models.Model):
    """Exam metadata. Linked to tiers via M2M."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    difficulty = models.CharField(max_length=50)  # e.g., Easy, Hard
    duration_minutes = models.PositiveIntegerField(default=30)
    question_count = models.PositiveIntegerField(default=50)
    passing_score = models.PositiveIntegerField(default=70, help_text=_("Passing percentage"))  # Added per refinement
    is_free = models.BooleanField(default=False)  # For S0
    questions = models.ManyToManyField(Question, related_name='exams')  # Composition
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Exam")
        verbose_name_plural = _("Exams")
        indexes = [models.Index(fields=['is_free'])]


    def __str__(self):
        # Fallback display in admin — use English translation if available
        trans = self.translations.filter(language='en').first()
        if trans and trans.title:
            return trans.title
        return f"Exam {self.id}[:8] ({self.difficulty})"

    @property
    def display_title(self):
        """Convenient property for templates/serializers"""
        from django.conf import settings
        lang = settings.LANGUAGE_CODE
        trans = self.translations.filter(language=lang).first()
        if trans and trans.title:
            return trans.title
        return self.translations.filter(language='en').first().title if self.translations.filter(language='en').exists() else f"Exam {self.id}[:8]"


class ExamTranslation(models.Model):
    exam = models.ForeignKey(Exam, related_name='translations', on_delete=models.CASCADE)
    language = models.CharField(max_length=10, choices=Language.choices())
    title = models.CharField(max_length=200)
    description = models.TextField()
    
    class Meta:
        unique_together = ['exam', 'language', 'title']
        verbose_name = _("Exam Translation")
        verbose_name_plural = _("Exam Translations")

    def __str__(self):
        return f"{self.exam.id} - {self.get_language_display()}: {self.title}"


