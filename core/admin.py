# core/admin.py

import json
from uuid import uuid4
from django.contrib import admin, messages
from django.utils import timezone
from django.urls import path
from django.utils.html import format_html
from django.shortcuts import render, redirect
from django.contrib.admin import SimpleListFilter
from django.contrib.admin.helpers import ActionForm
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
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
      
      
class AnswerChoiceTranslationInline(admin.StackedInline):
    model = AnswerChoiceTranslation
    extra = 1
    fields = ('language', 'text')
    verbose_name = _("Translation")
    verbose_name_plural = _("Translations")


@admin.register(AnswerChoice)
class AnswerChoiceAdmin(admin.ModelAdmin):
    list_display = ['id', 'question', 'order', 'is_correct', 'text_or_sign']
    list_filter = ['is_correct', 'question__question_type']
    search_fields = ['translations__text', 'road_sign_option__code']

    inlines = [AnswerChoiceTranslationInline]

    def text_or_sign(self, obj):
        if obj.road_sign_option:
            return f"Sign: {obj.road_sign_option.code}"
        trans = obj.translations.filter(language='en').first()
        return trans.text[:60] + "…" if trans else "—"
    text_or_sign.short_description = _("Content")


class AnswerChoiceInline(admin.TabularInline):
    model = AnswerChoice
    extra = 2  # most questions have ≥2 choices
    fields = ('road_sign_option', 'is_correct', 'order')
    # readonly_fields = ('order',)  # usually managed automatically
    show_change_link = True

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        # Optional: can add form validation here
        return formset


class QuestionTranslationInline(admin.StackedInline):
    model = QuestionTranslation
    extra = 1
    fields = ('language', 'content')
    min_num = 1  # at least English recommended
    verbose_name = _("Question Translation")
    verbose_name_plural = _("Question Translations")


class ExplanationTranslationInline(admin.StackedInline):
    model = ExplanationTranslation
    extra = 1
    fields = ('language', 'detail')
    verbose_name = _("Explanation Translation")
    verbose_name_plural = _("Explanation Translations")


class ExplanationInline(admin.StackedInline):
    model = Explanation
    extra = 1
    max_num = 1   # OneToOne relation
    can_delete = True
    fields = ('media_url', 'media_type')
    inlines = [ExplanationTranslationInline]


# ───────────────────────────────────────────────
# Question Admin with JSON Import
# ───────────────────────────────────────────────



class JSONImportForm(forms.Form):
    json_file = forms.FileField(
        label="Upload JSON File",
        help_text="Paste your q_bank array (TT, TI, IT questions)",
        widget=forms.FileInput(attrs={'accept': '.json'})
    )


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'question_type',
        'category',
        'difficulty',
        'is_premium',
        'associated_road_sign',   # shows __str__ of RoadSign
        'created_at',
    )
    list_filter = ('question_type', 'difficulty', 'category', 'is_premium', 'created_at')
    search_fields = ('translations__content', 'associated_road_sign__code')
    readonly_fields = ('created_at', 'updated_at')

    inlines = [
        QuestionTranslationInline,   # reuse your existing inlines
        AnswerChoiceInline,
        ExplanationInline,
    ]
    actions = ['make_premium', 'make_free']
    
    @admin.action(description="Mark selected questions as PREMIUM")
    def make_premium(self, request, queryset):
        updated = queryset.exclude(is_premium=True).update(is_premium=True)
        if updated:
            self.message_user(request, f"{updated} questions marked as PREMIUM.", messages.SUCCESS)
        else:
            self.message_user(request, "No questions were updated (already premium).", messages.INFO)

    @admin.action(description="Mark selected questions as FREE")
    def make_free(self, request, queryset):
        updated = queryset.exclude(is_premium=False).update(is_premium=False)
        if updated:
            self.message_user(request, f"{updated} questions marked as FREE.", messages.SUCCESS)
        else:
            self.message_user(request, "No questions were updated (already free).", messages.INFO)

    # ========================== CUSTOM JSON IMPORT ==========================

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['show_json_import_button'] = True
        return super().changelist_view(request, extra_context=extra_context)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('import-json/', self.admin_site.admin_view(self.import_json_view), name='question_import_json'),
            path('import-json/confirm/', self.admin_site.admin_view(self.confirm_import_view), name='question_import_confirm'),
        ]
        return custom_urls + urls

    # Step 1: Upload JSON
    def import_json_view(self, request):
        if request.method == 'POST':
            form = JSONImportForm(request.POST, request.FILES)
            if form.is_valid():
                file = request.FILES['json_file']
                
                if file.size == 0:
                    messages.error(request, "The uploaded file is empty (0 bytes).")
                    return redirect('admin:yourapp_question_changelist')  # ← fix yourapp name
                
                try:
                    # Read the entire file content as string
                    raw_content = file.read().decode('utf-8')
                    
                    # Make Python booleans JSON-compatible (optional safety)
                    raw_content = raw_content.replace('True', 'true').replace('False', 'false')
                    
                    # IMPORTANT: use json.loads() when you already have a string
                    data = json.loads(raw_content)
                    
                    if not isinstance(data, list):
                        raise ValidationError("Root must be a JSON array []")
                    
                    if len(data) > 500:
                        messages.warning(request, "Large file (>500 questions). Preview may be slow.")
                    
                    # Store in session
                    request.session['import_data'] = data
                    request.session['import_filename'] = file.name
                    
                    return redirect('admin:question_import_confirm')
                    
                except json.JSONDecodeError as e:
                    messages.error(request, f"Invalid JSON: {e}")
                    print("JSON error details:", str(e))  # helpful in console
                except UnicodeDecodeError:
                    messages.error(request, "File is not valid UTF-8 encoded text.")
                except Exception as e:
                    messages.error(request, f"Error processing file: {e}")
                    print("Unexpected error:", str(e))
                    
                # If we reach here → error occurred → stay on page or redirect
                return redirect('..')  # or render the form again with errors

        # GET request → show upload form
        form = JSONImportForm()
        context = {
            **self.admin_site.each_context(request),
            'title': 'Import Questions from JSON',
            'form': form,
            'opts': self.model._meta,
        }
        return render(request, 'admin/question_import_upload.html', context)

    # Step 2: Preview + Confirm Import
    def confirm_import_view(self, request):
        data = request.session.get('import_data')
        if not data:
            messages.error(request, "No import data found. Please upload again.")
            return redirect('admin:question_import_json')

        if request.method == 'POST':
            # Final Import
            stats = self._process_bulk_import(data, dry_run=False, request=request)
            # Clean session
            request.session.pop('import_data', None)
            request.session.pop('import_filename', None)

            messages.success(request,
                f"Import completed! Created: {stats['created']} | "
                f"Updated: {stats['updated']} | Skipped: {stats['skipped']}"
            )
            return redirect('..')

        # Preview mode
        preview_stats = self._process_bulk_import(data, dry_run=True, request=request)

        context = {
            **self.admin_site.each_context(request),
            'title': f"Preview Import — {len(data)} Questions",
            'preview': preview_stats['preview_items'][:20],   # show max 20 rows
            'total_questions': len(data),
            'stats': preview_stats,
            'filename': request.session.get('import_filename', 'questions.json'),
        }
        return render(request, 'admin/question_import_preview.html', context)

    # Core logic: Preview (dry_run=True) or Real Import
    def _process_bulk_import(self, data_list, dry_run=True, request=None):
        created = updated = skipped = 0
        preview_items = []
        lang_codes = ['en', 'am', 'ti', 'or']

        for idx, q in enumerate(data_list, 1):
            try:
                q_type = q.get('type')
                if q_type not in ('TT', 'TI', 'IT'):
                    raise ValueError(f"Invalid question type: {q_type}")

                # ── Category ──
                category = None
                if q.get('cat'):
                    category = QuestionCategory.objects.filter(code__iexact=q['cat']).first()
                    if not category:
                        raise ValueError(f"Category code not found: {q.get('cat')}")

                # ── Associated road sign (mainly useful for sign-related questions) ──
                road_sign = None
                sign_val = q.get('sign')
                if sign_val:
                    if isinstance(sign_val, (int, str)) and str(sign_val).isdigit():
                        road_sign = RoadSign.objects.filter(pk=sign_val).first()
                    else:
                        road_sign = RoadSign.objects.filter(code__iexact=str(sign_val)).first()
                    if not road_sign:
                        raise ValueError(f"Road sign not found: {sign_val}")

                # ── Question image (mainly for IT questions) ──
                question_image = q.get('img')

                # ── Content ──
                content_dict = {
                    lang: str(q[lang]).strip()
                    for lang in lang_codes
                    if lang in q and q[lang]
                }

                if 'en' not in content_dict:
                    raise ValueError("English question text is required")

                # Duplicate check (English content + type)
                existing = None
                if content_dict.get('en'):
                    existing = Question.objects.filter(
                        translations__language='en',
                        translations__content__iexact=content_dict['en'],
                        question_type=q_type
                    ).first()

                status = "updated" if existing else "created"

                if not dry_run:
                    if existing:
                        question = existing
                        updated += 1
                    else:
                        question = Question.objects.create(
                            id=uuid4(),
                            category=category,
                            associated_road_sign=road_sign,
                            question_type=q_type,
                            difficulty=q.get('diff', 'medium'),
                            is_premium=q.get('is_premium', False),
                            media_image=question_image if q_type == 'IT' else None,
                        )
                        created += 1

                    self._save_question_relations(question, q, content_dict, lang_codes, existing)
                else:
                    # Preview
                    preview_items.append({
                        'index': idx,
                        'en': content_dict.get('en', '—')[:70],
                        'type': q_type,
                        'category': category.code if category else '—',
                        'sign': road_sign.code if road_sign else '—',
                        'has_image': bool(question_image) and q_type == 'IT',
                        'choices_count': len(q.get('choices', [])),
                        'status': status,
                    })

                    if existing:
                        updated += 1
                    else:
                        created += 1

            except Exception as e:
                skipped += 1
                msg = f"Skipped question #{idx}: {str(e)}"
                if request and not dry_run:
                    messages.warning(request, msg)
                print(msg)  # console log

        return {
            'created': created,
            'updated': updated,
            'skipped': skipped,
            'preview_items': preview_items,
        }


    def _save_question_relations(self, question, q_data, content_dict, lang_codes, existing):
        # Question Translations
        for lang, text in content_dict.items():
            QuestionTranslation.objects.update_or_create(
                question=question,
                language=lang,
                defaults={'content': text}
            )

        # Choices handling ────────────────────────────────────────
        if existing:
            question.choices.all().delete()

        choices_data = q_data.get('choices') or []
        if not choices_data:
            raise ValueError("At least one answer choice is required")

        for order, ch in enumerate(choices_data, 1):
            is_correct = bool(ch.get('is_correct', False))

            if question.question_type == 'TI':
                # Text → Image : must have road sign reference in choice
                sign_val = ch.get('sign')
                if not sign_val:
                    raise ValueError(f"TI question requires 'sign' in each choice (choice {order})")

                sign_obj = None
                if isinstance(sign_val, (int, str)) and str(sign_val).isdigit():
                    sign_obj = RoadSign.objects.filter(pk=sign_val).first()
                else:
                    sign_obj = RoadSign.objects.filter(code__iexact=str(sign_val)).first()

                if not sign_obj:
                    raise ValueError(f"Road sign not found for choice {order}: {sign_val}")

                AnswerChoice.objects.create(
                    question=question,
                    road_sign_option=sign_obj,
                    is_correct=is_correct,
                    order=order
                )
                # No text translation needed for image choices

            else:
                # TT and IT → text choices
                ch_content = {
                    lang: str(ch[lang]).strip()
                    for lang in lang_codes
                    if lang in ch and ch[lang]
                }

                if 'en' not in ch_content:
                    raise ValueError(f"English text required for choice {order}")

                choice = AnswerChoice.objects.create(
                    question=question,
                    is_correct=is_correct,
                    order=order
                )

                for lang, text in ch_content.items():
                    AnswerChoiceTranslation.objects.create(
                        answer_choice=choice,
                        language=lang,
                        text=text
                    )

        # Explanation ─────────────────────────────────────────────
        exp_data = q_data.get('explanation')
        if exp_data:
            if existing and hasattr(question, 'explanation'):
                question.explanation.delete()

            exp = Explanation.objects.create(
                question=question,
                media_url=exp_data.get('media_url'),
                media_type=exp_data.get('media_type')
            )

            for lang in lang_codes:
                if lang in exp_data and exp_data[lang]:
                    ExplanationTranslation.objects.create(
                        explanation=exp,
                        language=lang,
                        detail=str(exp_data[lang]).strip()
                    )
# === AnswerChoice ===
    
# class AnswerChoiceTranslationInline(admin.StackedInline):
#     model = AnswerChoiceTranslation
#     extra = 1
#     fields = ('language', 'text')

# @admin.register(AnswerChoice)
# class AnswerChoiceAdmin(admin.ModelAdmin):
#     list_display = ['id', 'question', 'is_correct']
#     inlines = [AnswerChoiceTranslationInline]
    
# class AnswerChoiceInline(admin.TabularInline):
#     model = AnswerChoice
#     extra = 1
#     fields = ('road_sign_option', 'is_correct', 'order')
    

# === Explanation ===
# class ExplanationTranslationInline(admin.StackedInline):
#     model = ExplanationTranslation
#     extra = 1
#     fields = ('language', 'detail')

# class ExplanationInline(admin.StackedInline):
#     model = Explanation
#     extra = 1
#     fields = ('media_url', 'media_type')
#     inlines = [ExplanationTranslationInline]

@admin.register(Explanation)  
class ExplanationAdmin(admin.ModelAdmin):
    extra = 1
    inlines = [ExplanationTranslationInline]
    
    
# === Question ===
# class QuestionTranslationInline(admin.StackedInline):
#     model = QuestionTranslation
#     extra = 1
#     fields = ('language', 'content')

# @admin.register(Question)
# class QuestionAdmin(ImportExportMixin, admin.ModelAdmin):
#     list_display = (
#         'id',
#         'category',
#         'question_type',
#         'difficulty',
#         'is_premium',
#         'associated_road_sign',
#         'created_at',
#     )
#     list_filter = (
#         'question_type',
#         'difficulty',
#         'category',
#         'is_premium',
#         'created_at',
#     )
#     search_fields = (
#         'id',
#         'translations__content',
#         'associated_road_sign__code',
#     )
#     inlines = [
#         QuestionTranslationInline,
#         AnswerChoiceInline,
#         ExplanationInline,
#     ]
#     readonly_fields = ('created_at', 'updated_at')

#     actions = ['make_premium', 'make_free']

#     # --------------------
#     # Admin Actions
#     # --------------------

#     @admin.action(description="Mark selected questions as PREMIUM")
#     def make_premium(self, request, queryset):
#         if not queryset.exists():
#             self.message_user(
#                 request,
#                 "No questions selected.",
#                 level=messages.WARNING,
#             )
#             return

#         updated = queryset.exclude(is_premium=True).update(is_premium=True)

#         self.message_user(
#             request,
#             f"{updated} question(s) successfully marked as PREMIUM.",
#             level=messages.SUCCESS,
#         )

#     @admin.action(description="Mark selected questions as FREE")
#     def make_free(self, request, queryset):
#         if not queryset.exists():
#             self.message_user(
#                 request,
#                 "No questions selected.",
#                 level=messages.WARNING,
#             )
#             return

#         updated = queryset.exclude(is_premium=False).update(is_premium=False)

#         self.message_user(
#             request,
#             f"{updated} question(s) successfully marked as FREE.",
#             level=messages.SUCCESS,
#         )

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
        
        