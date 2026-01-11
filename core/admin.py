# core/admin.py

from django.contrib import admin, messages
from django.utils import timezone
from django.utils.html import format_html
from django.shortcuts import render, redirect
from django.contrib.admin import SimpleListFilter
from import_export.admin import ImportExportMixin
from cloudinary.models import CloudinaryField
from cloudinary.forms import CloudinaryJsFileField
from django import forms
from django.db.models import Count, Q

from core.models import (
    QuestionCategory, QuestionCategoryTranslation,
    RoadSignCategory, RoadSignCategoryTranslation,
    RoadSign, RoadSignTranslation,
    Question, QuestionTranslation,
    AnswerChoice, AnswerChoiceTranslation,
    Explanation, ExplanationTranslation,
    Exam, ExamTranslation
)
from users.models import ExamAttempt

# Custom filter for subscription expiry
class ExpiryStatusFilter(SimpleListFilter):
    title = 'Subscription Expiry'
    parameter_name = 'expiry'

    def lookups(self, request, model_admin):
        return (
            ('active', 'Active'),
            ('expiring_soon', 'Expiring Soon (≤7 days)'),
            ('expired', 'Expired'),
        )

    def queryset(self, request, queryset):
        now = timezone.now()
        if self.value() == 'expiring_soon':
            return queryset.filter(expiry_date__lte=now + timezone.timedelta(days=7), expiry_date__gt=now)
        if self.value() == 'expired':
            return queryset.filter(expiry_date__lt=now)
        if self.value() == 'active':
            return queryset.filter(expiry_date__gt=now)
        return queryset

# === QuestionCategory ===
class QuestionCategoryTranslationInline(admin.StackedInline):
    model = QuestionCategoryTranslation
    extra = 1
    fields = ('language', 'name', 'description')

@admin.register(QuestionCategory)
class QuestionCategoryAdmin(admin.ModelAdmin):
    list_display = ('code', 'order', 'created_at')
    search_fields = ('code', 'translations__name')
    list_filter = ('order', 'created_at')
    inlines = [QuestionCategoryTranslationInline]

# === RoadSignCategory ===
class RoadSignCategoryTranslationInline(admin.StackedInline):
    model = RoadSignCategoryTranslation
    extra = 1
    fields = ('language', 'name', 'description')

@admin.register(RoadSignCategory)
class RoadSignCategoryAdmin(admin.ModelAdmin):
    list_display = ('code', 'order')
    search_fields = ('code', 'translations__name')
    list_filter = ('order',)
    inlines = [RoadSignCategoryTranslationInline]

# === RoadSign ===
class RoadSignTranslationInline(admin.StackedInline):
    model = RoadSignTranslation
    extra = 1
    fields = ('language', 'name', 'meaning', 'detailed_explanation')
      

@admin.register(RoadSign)
class RoadSignAdmin(admin.ModelAdmin):
    list_display = ('code', 'category', 'image_preview', 'created_at')
    search_fields = ('code', 'translations__name')
    list_filter = ('category', 'created_at')
    inlines = [RoadSignTranslationInline]
    readonly_fields = ('image_preview', 'created_at', 'updated_at')

    def image_preview(self, obj):
        """Safe preview for Cloudinary or local images"""
        if obj.image:
            # Use Cloudinary optimized URL
            url = obj.image.url.replace('/upload/', '/upload/w_150,h_150,c_fill,q_auto/')
            return format_html('<img src="{}" width="100" style="border-radius:8px;"/>', url)
        return "No image"
    image_preview.short_description = "Preview"
       

# === AnswerChoice ===
@admin.register(AnswerChoice)
class AnswerChoiceAdmin(admin.ModelAdmin):
    list_display = ['id', 'question', 'is_correct']
    
class AnswerChoiceTranslationInline(admin.StackedInline):
    model = AnswerChoiceTranslation
    extra = 1
    fields = ('language', 'text')

class AnswerChoiceInline(admin.TabularInline):
    model = AnswerChoice
    extra = 1
    fields = ('road_sign_option', 'is_correct', 'order')
    inlines = [AnswerChoiceTranslationInline]

# === Explanation ===
class ExplanationTranslationInline(admin.StackedInline):
    model = ExplanationTranslation
    extra = 1
    fields = ('language', 'detail')

class ExplanationInline(admin.StackedInline):
    model = Explanation
    extra = 1
    fields = ('media_url', 'media_type')
    inlines = [ExplanationTranslationInline]

@admin.register(Explanation)  
class ExplanationAdmin(admin.ModelAdmin):
    extra = 1
    inlines = [ExplanationTranslationInline]
    
    
# === Question ===
class QuestionTranslationInline(admin.StackedInline):
    model = QuestionTranslation
    extra = 1
    fields = ('language', 'content')

@admin.register(Question)
class QuestionAdmin(ImportExportMixin, admin.ModelAdmin):
    list_display = (
        'id',
        'category',
        'question_type',
        'difficulty',
        'is_premium',
        'associated_road_sign',
        'created_at',
    )
    list_filter = (
        'question_type',
        'difficulty',
        'category',
        'is_premium',
        'created_at',
    )
    search_fields = (
        'id',
        'translations__content',
        'associated_road_sign__code',
    )
    inlines = [
        QuestionTranslationInline,
        AnswerChoiceInline,
        ExplanationInline,
    ]
    readonly_fields = ('created_at', 'updated_at')

    actions = ['make_premium', 'make_free']

    # --------------------
    # Admin Actions
    # --------------------

    @admin.action(description="Mark selected questions as PREMIUM")
    def make_premium(self, request, queryset):
        if not queryset.exists():
            self.message_user(
                request,
                "No questions selected.",
                level=messages.WARNING,
            )
            return

        updated = queryset.exclude(is_premium=True).update(is_premium=True)

        self.message_user(
            request,
            f"{updated} question(s) successfully marked as PREMIUM.",
            level=messages.SUCCESS,
        )

    @admin.action(description="Mark selected questions as FREE")
    def make_free(self, request, queryset):
        if not queryset.exists():
            self.message_user(
                request,
                "No questions selected.",
                level=messages.WARNING,
            )
            return

        updated = queryset.exclude(is_premium=False).update(is_premium=False)

        self.message_user(
            request,
            f"{updated} question(s) successfully marked as FREE.",
            level=messages.SUCCESS,
        )

# === Exam ===
class ExamTranslationInline(admin.StackedInline):
    model = ExamTranslation
    extra = 1
    fields = ('language', 'title', 'description')


class ExamGeneratorForm(forms.Form):
    title_en = forms.CharField(max_length=200, label="Title (English)")
    title_am = forms.CharField(max_length=200, label="Title (Amharic)")
    title_ti = forms.CharField(max_length=200, label="Title (Tigrinya)", required=False)
    title_or = forms.CharField(max_length=200, label="Title (Oromiffa)", required=False)

    difficulty = forms.ChoiceField(
        choices=[('', 'Any'), ('easy', 'Easy'), ('medium', 'Medium'), ('hard', 'Hard')]
    )
    question_count = forms.IntegerField(min_value=10, max_value=100, initial=50)
    is_free = forms.BooleanField(required=False, label="Free Exam")

    question_type = forms.MultipleChoiceField(
        choices=Question.QuestionType.choices,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Question Types"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # SAFE: DB access only after Django is fully ready
        categories = QuestionCategory.objects.annotate(
            question_count=Count('questions')
        )

        for cat in categories:
            field_name = f"cat_{cat.code}_count"
            self.fields[field_name] = forms.IntegerField(
                label=f"{cat.code} ({cat.question_count} available)",
                min_value=0,
                initial=0,
                required=False
            )
    
@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ('get_title', 'difficulty', 'duration_minutes', 'question_count', 'passing_score', 'is_free')
    search_fields = ('translations__title',)
    list_filter = ('difficulty', 'is_free', 'passing_score')
    inlines = [ExamTranslationInline]
    # filter_horizontal = ('questions',)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        self.request = request
        return qs.prefetch_related('translations')

    def get_title(self, obj):
        lang = getattr(self.request, 'LANGUAGE_CODE', 'en')
        trans = obj.translations.filter(language=lang).first()
        if trans and trans.title:
            return trans.title
        trans = obj.translations.filter(language='en').first()
        if trans and trans.title:
            return trans.title
        return obj.translations.first().title if obj.translations.exists() else f"Exam {obj.id}"
    get_title.short_description = 'Title'
    get_title.admin_order_field = 'translations__title'
    
    def get_urls(self):
        urls = super().get_urls()
        from django.urls import path
        custom_urls = [
            path('generate/', self.admin_site.admin_view(self.generate_exam_view), name='exam_generate'),
        ]
        return custom_urls + urls

    def generate_exam_view(self, request):
        if request.method == 'POST':
            form = ExamGeneratorForm(request.POST)
            if form.is_valid():
                # Create exam
                exam = Exam.objects.create(
                    difficulty=form.cleaned_data['difficulty'] or 'medium',
                    duration_minutes=45,
                    question_count=form.cleaned_data['question_count'],
                    passing_score=74,
                    is_free=form.cleaned_data['is_free']
                )

                # Add translations
                ExamTranslation.objects.create(exam=exam, language='en', title=form.cleaned_data['title_en'])
                ExamTranslation.objects.create(exam=exam, language='am', title=form.cleaned_data['title_am'])
                if form.cleaned_data['title_ti']:
                    ExamTranslation.objects.create(exam=exam, language='ti', title=form.cleaned_data['title_ti'])
                if form.cleaned_data['title_or']:
                    ExamTranslation.objects.create(exam=exam, language='or', title=form.cleaned_data['title_or'])

                # Collect questions
                selected_questions = Question.objects.all()
                filters = Q()

                # Category counts
                total_needed = form.cleaned_data['question_count']
                assigned = []

                for cat in QuestionCategory.objects.all():
                    count_field = f"cat_{cat.code}_count"
                    count = form.cleaned_data.get(count_field, 0)
                    if count > 0:
                        qs = Question.objects.filter(category=cat)
                        if form.cleaned_data['difficulty']:
                            qs = qs.filter(difficulty=form.cleaned_data['difficulty'])
                        if form.cleaned_data['question_type']:
                            qs = qs.filter(question_type__in=form.cleaned_data['question_type'])
                        assigned.extend(list(qs.order_by('?')[:count]))

                # Fill remaining if needed
                if len(assigned) < total_needed:
                    remaining = Question.objects.exclude(id__in=[q.id for q in assigned])
                    if form.cleaned_data['difficulty']:
                        remaining = remaining.filter(difficulty=form.cleaned_data['difficulty'])
                    if form.cleaned_data['question_type']:
                        remaining = remaining.filter(question_type__in=form.cleaned_data['question_type'])
                    assigned.extend(list(remaining.order_by('?')[:total_needed - len(assigned)]))

                exam.questions.set(assigned[:total_needed])
                self.message_user(request, f"Exam '{form.cleaned_data['title_en']}' generated with {len(assigned)} questions!")
                return redirect('..')
        else:
            form = ExamGeneratorForm()

        context = {
            **self.admin_site.each_context(request),
            'form': form,
            'title': "Generate New Exam",
        }
        return render(request, 'admin/exam_generate.html', context)

@admin.register(ExamAttempt)
class ExamAttemptAdmin(admin.ModelAdmin):
    list_display = ('user_profile', 'exam', 'status', 'score', 'is_passed', 'start_time', 'timestamp')
    list_filter = ('status', 'is_passed', 'start_time')
    search_fields = ('user_profile__tg_id', 'exam__translations__title')
    readonly_fields = ('start_time', 'end_time', 'raw_answers_json', 'score', 'is_passed', 'timestamp')
    
    actions = ['soft_delete', 'hard_delete']

    def soft_delete(self, request, queryset):
        queryset.update(deleted_at=timezone.now(), status='ABANDONED')
        self.message_user(request, "Selected attempts soft-deleted.")

    def hard_delete(self, request, queryset):
        count = queryset.count()
        queryset.hard_delete()
        self.message_user(request, f"{count} attempts permanently deleted.")
        
        