# core/admin.py
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.db.models import Count, Prefetch
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext
from django import forms
from .models import *


class TranslationInlineFormSet(forms.models.BaseInlineFormSet):
    """Formset to ensure at least one English translation"""
    def clean(self):
        super().clean()
        has_english = False
        for form in self.forms:
            if not form.cleaned_data.get('DELETE', False):
                if form.cleaned_data.get('language') == 'en':
                    has_english = True
                    break
        if not has_english and not self.instance._state.adding:
            raise forms.ValidationError(
                _("At least one English translation is required.")
            )

class QuestionCategoryTranslationInline(admin.TabularInline):
    model = QuestionCategoryTranslation
    formset = TranslationInlineFormSet
    extra = 1
    min_num = 1
    verbose_name = _("Translation")
    verbose_name_plural = _("Translations")
    fields = ['language', 'name', 'description']

@admin.register(QuestionCategory)
class QuestionCategoryAdmin(admin.ModelAdmin):
    list_display = ['code', 'order', 'name_en', 'name_am']
    list_editable = ['order']
    search_fields = ['code', 'translations__name']
    inlines = [QuestionCategoryTranslationInline]

    def name_en(self, obj):
        trans = obj.translations.filter(language='en').first()
        return trans.name if trans else '-'
    name_en.short_description = 'Name (EN)'

    def name_am(self, obj):
        trans = obj.translations.filter(language='am').first()
        return trans.name if trans else '-'
    name_am.short_description = 'Name (AM)'
   
    
# Road Sign Category Admin
class RoadSignCategoryTranslationInline(admin.TabularInline):
    model = RoadSignCategoryTranslation
    formset = TranslationInlineFormSet
    extra = 1
    min_num = 1
    verbose_name = _("Translation")
    verbose_name_plural = _("Translations")
    fields = ['language', 'name', 'description']

@admin.register(RoadSignCategory)
class RoadSignCategoryAdmin(admin.ModelAdmin):
    list_display = ['code', 'order', 'translations_count', 'road_signs_count']
    list_filter = ['order', ]
    search_fields = ['code', 'translations__name']
    readonly_fields = ['id',]
    inlines = [RoadSignCategoryTranslationInline]
    
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('id', 'code', 'order')
        }),
    )
    
    def translations_count(self, obj):
        return obj.translations.count()
    translations_count.short_description = _('Translations')
    
    def road_signs_count(self, obj):
        return obj.road_signs.count()
    road_signs_count.short_description = _('Road Signs')

# Road Sign Admin
class RoadSignTranslationInline(admin.TabularInline):
    model = RoadSignTranslation
    formset = TranslationInlineFormSet
    extra = 1
    min_num = 1
    verbose_name = _("Translation")
    verbose_name_plural = _("Translations")
    fields = ['language', 'name', 'meaning', 'detailed_explanation']

@admin.register(RoadSign)
class RoadSignAdmin(admin.ModelAdmin):
    list_display = ['code', 'image_preview', 'category', 'translations_count', 'questions_count', 'created_at']
    list_filter = ['category', 'created_at']
    search_fields = ['code', 'translations__name', 'translations__meaning']
    readonly_fields = ['id', 'created_at', 'updated_at']
    inlines = [RoadSignTranslationInline]
    
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('id', 'code', 'image', 'category', 'created_at', 'updated_at')
        }),
    )
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="50" height="50" />', obj.image.url)
        return "-"
    image_preview.short_description = _('Image')
    
    def translations_count(self, obj):
        return obj.translations.count()
    translations_count.short_description = _('Translations')
    
    def questions_count(self, obj):
        return obj.questions.count()
    questions_count.short_description = _('Questions')
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('category').prefetch_related('translations')



class AnswerChoiceTranslationInline(admin.TabularInline):
    model = AnswerChoiceTranslation
    extra = 1
    min_num = 1
    verbose_name = _("Translation")
    verbose_name_plural = _("Translations")
    fields = ['language', 'text']

# Question Admin
class QuestionTranslationInline(admin.TabularInline):
    model = QuestionTranslation
    formset = TranslationInlineFormSet
    extra = 1
    min_num = 1
    verbose_name = _("Translation")
    verbose_name_plural = _("Translations")
    fields = ['language', 'content']

class ExplanationTranslationInline(admin.TabularInline):
    model = ExplanationTranslation
    extra = 1
    min_num = 1
    verbose_name = _("Translation")
    verbose_name_plural = _("Translations")
    fields = ['language', 'detail']
    
class AnswerChoiceInline(admin.TabularInline):
    model = AnswerChoice
    extra = 0
    min_num = 1
    fields = ['is_correct', 'order', 'road_sign_option']
    ordering = ['order']
    inlines = [AnswerChoiceTranslationInline]
    verbose_name = _("Answer Choice")
    verbose_name_plural = _("Answer Choices")
    
    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        # Customize queryset for road_sign_option field
        if obj and obj.road_sign_context:
            # Only show road signs as options for this question's context
            formset.form.base_fields['road_sign_option'].queryset = RoadSign.objects.all()
        return formset
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('road_sign_option').prefetch_related('translations')

class ExplanationInline(admin.StackedInline):
    model = Explanation
    extra = 0
    min_num = 0
    max_num = 1
    fields = ['media_url', 'media_type']
    inlines = [ExplanationTranslationInline]
    verbose_name = _("Explanation")
    verbose_name_plural = _("Explanations")

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = [
        'id_short',
        'category_display',
        'road_sign_context',
        'question_content_preview',
        'question_type_display',
        'difficulty_display',
        'is_premium',
        'translations_count',
        'choices_count',
        'has_explanation',
        'created_at',
    ]
    list_filter = [
        'category',
        'question_type',
        'difficulty',
        'is_premium',
        'road_sign_context__category',  # Filter by road sign category
        'created_at',
    ]
    search_fields = [
        'translations__content',
        'road_sign_context__code',
        'choices__translations__text',
    ]
    readonly_fields = ['id', 'created_at', 'updated_at']
    autocomplete_fields = ['road_sign_context', 'category']
    raw_id_fields = []  # Use autocomplete instead
    date_hierarchy = 'created_at'

    inlines = [
        QuestionTranslationInline,
        AnswerChoiceInline,
        ExplanationInline,
    ]

    fieldsets = (
        (_('Basic Information'), {
            'fields': (
                'id',
                'category',
                'road_sign_context',
                'question_type',
                'is_premium',
                'difficulty',
            )
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    actions = [
        'make_premium',
        'make_free',
        'duplicate_questions',
        'set_difficulty_easy',
        'set_difficulty_medium',
        'set_difficulty_hard',
    ]

    # ------------------- Display Helpers -------------------

    def id_short(self, obj):
        return str(obj.id)[:8]
    id_short.short_description = _('ID')
    id_short.admin_order_field = 'id'

    def category_display(self, obj):
        if obj.category:
            return obj.category.translations.filter(language='en').first().name or obj.category.code
        return "—"
    category_display.short_description = _('Category')
    category_display.admin_order_field = 'category__code'

    def question_content_preview(self, obj):
        if not obj.pk:
            return "—"
        en_trans = obj.translations.filter(language='en').first()
        if en_trans:
            preview = en_trans.content[:80]
            return format_html('<span title="{}">{}{}</span>', en_trans.content, preview, '...' if len(en_trans.content) > 80 else '')
        return "—"
    question_content_preview.short_description = _('Question (EN)')
    question_content_preview.admin_order_field = 'translations__content'

    def question_type_display(self, obj):
        return obj.get_question_type_display()
    question_type_display.short_description = _('Type')
    question_type_display.admin_order_field = 'question_type'

    def difficulty_display(self, obj):
        return obj.get_difficulty_display()
    difficulty_display.short_description = _('Difficulty')
    difficulty_display.admin_order_field = 'difficulty'

    def translations_count(self, obj):
        return obj.translations_count
    translations_count.short_description = _('Trans.')
    translations_count.admin_order_field = 'translations_count'

    def choices_count(self, obj):
        return obj.choices_count
    choices_count.short_description = _('Choices')
    choices_count.admin_order_field = 'choices_count'

    def has_explanation(self, obj):
        return bool(obj.explanation)
    has_explanation.boolean = True
    has_explanation.short_description = _('Explanation?')

    # ------------------- Optimized Queryset -------------------

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'road_sign_context',
            'category',
        ).prefetch_related(
            'translations',
            'choices__translations',
            'explanation',
        ).annotate(
            translations_count=Count('translations', distinct=True),
            choices_count=Count('choices', distinct=True),
        )

    # ------------------- Admin Actions -------------------

    def make_premium(self, request, queryset):
        updated = queryset.update(is_premium=True)
        self.message_user(
            request,
            ngettext(
                "%d question was marked as premium.",
                "%d questions were marked as premium.",
                updated,
            )
            % updated,
            messages.SUCCESS,
        )
    make_premium.short_description = _("Mark selected questions as Premium")

    def make_free(self, request, queryset):
        updated = queryset.update(is_premium=False)
        self.message_user(
            request,
            ngettext(
                "%d question was made free.",
                "%d questions were made free.",
                updated,
            )
            % updated,
            messages.SUCCESS,
        )
    make_free.short_description = _("Mark selected questions as Free")

    def duplicate_questions(self, request, queryset):
        duplicated_count = 0
        for question in queryset:
            # Duplicate the question
            old_id = question.id
            question.id = None
            question._state.adding = True
            question.save()

            # Copy translations
            for trans in question.translations.all():
                trans.id = None
                trans.question = question
                trans.save()

            # Copy choices
            for choice in question.choices.all():
                old_choice_id = choice.id
                choice.id = None
                choice.question = question
                choice.save()

                # Copy choice translations
                for ct in choice.translations.all():
                    ct.id = None
                    ct.answer_choice = choice
                    ct.save()

            # Copy explanation if exists
            if hasattr(question, 'explanation') and question.explanation.exists():
                old_exp = question.explanation.first()
                old_exp.id = None
                old_exp.question = question
                old_exp.save()

                for et in old_exp.translations.all():
                    et.id = None
                    et.explanation = old_exp
                    et.save()

            duplicated_count += 1

        self.message_user(
            request,
            ngettext(
                "%d question was successfully duplicated.",
                "%d questions were successfully duplicated.",
                duplicated_count,
            )
            % duplicated_count,
            messages.SUCCESS,
        )
    duplicate_questions.short_description = _("Duplicate selected questions")

    def set_difficulty_easy(self, request, queryset):
        updated = queryset.update(difficulty=1)
        self.message_user(request, _("%d questions set to Easy.") % updated, messages.SUCCESS)
    set_difficulty_easy.short_description = _("Set difficulty: Easy")

    def set_difficulty_medium(self, request, queryset):
        updated = queryset.update(difficulty=2)
        self.message_user(request, _("%d questions set to Medium.") % updated, messages.SUCCESS)
    set_difficulty_medium.short_description = _("Set difficulty: Medium")

    def set_difficulty_hard(self, request, queryset):
        updated = queryset.update(difficulty=3)
        self.message_user(request, _("%d questions set to Hard.") % updated, messages.SUCCESS)
    set_difficulty_hard.short_description = _("Set difficulty: Hard")

# User Profile Admin
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'telegram_username',  
        'last_active'
    ]
    list_filter = [ 'created_at', 'last_active']
    search_fields = ['user__username', 'telegram_username', 'user__email', 'telegram_id']
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'last_active', 
    ]
    
    fieldsets = (
        (_('User Information'), {
            'fields': ('user', 'telegram_id', 'telegram_username', 'telegram_data')
        }),
        (_('Statistics'), {
            'fields': ('total_exam_attempts', 'correct_answers')
        }),
        (_('Metadata'), {
            'fields': ('created_at', 'updated_at', 'last_active')
        }),
    )
    

# Payment Method Admin
class PaymentMethodTranslationInline(admin.TabularInline):
    model = PaymentMethodTranslation
    formset = TranslationInlineFormSet
    extra = 1
    min_num = 1
    verbose_name = _("Translation")
    verbose_name_plural = _("Translations")
    fields = ['language', 'account_details', 'instruction']

@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'is_active', 'order', 'amount', 'translations_count', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'code', 'translations__account_details']
    readonly_fields = ['id', 'created_at', 'updated_at']
    inlines = [PaymentMethodTranslationInline]
    
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('id', 'name', 'code', 'logo', 'is_active', 'order', 'amount')
        }),
        (_('Metadata'), {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def translations_count(self, obj):
        return obj.translations.count()
    translations_count.short_description = _('Translations')

# User Progress Admin
@admin.register(UserProgress)
class UserProgressAdmin(admin.ModelAdmin):
    list_display = ['user', 'question_preview', 'is_correct', 'time_taken', 'created_at']
    list_filter = ['is_correct', 'created_at']
    search_fields = ['user__username', 'question__translations__content']
    readonly_fields = ['id', 'created_at']
    date_hierarchy = 'created_at'
    
    def question_preview(self, obj):
        translation = obj.question.translations.filter(language='en').first()
        if translation:
            return translation.content[:50] + '...' if len(translation.content) > 50 else translation.content
        return f"Question {obj.question.id}"
    question_preview.short_description = _('Question')
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user', 'question', 'selected_answer').prefetch_related('question__translations')

# Direct Translation Model Admins for debugging/management
@admin.register(RoadSignCategoryTranslation)
class RoadSignCategoryTranslationAdmin(admin.ModelAdmin):
    list_display = ['category', 'language', 'name', 'description_preview']
    list_filter = ['language', 'category']
    search_fields = ['name', 'description', 'category__code']
    
    def description_preview(self, obj):
        return obj.description[:100] + '...' if len(obj.description) > 100 else obj.description
    description_preview.short_description = _('Description')


@admin.register(RoadSignTranslation)
class RoadSignTranslationAdmin(admin.ModelAdmin):
    list_display = ['road_sign', 'language', 'name', 'meaning_preview']
    list_filter = ['language', 'road_sign']
    search_fields = ['name', 'meaning', 'detailed_explanation', 'road_sign__code']
    
    def meaning_preview(self, obj):
        return obj.meaning[:100] + '...' if len(obj.meaning) > 100 else obj.meaning
    meaning_preview.short_description = _('Meaning')
    
    def detailed_explanation_preview(self, obj):
        # Strip HTML tags for preview
        import re
        text = re.sub(r'<[^>]+>', '', obj.detailed_explanation)
        return text[:150] + '...' if len(text) > 150 else text
    detailed_explanation_preview.short_description = _('Detailed Explanation')


@admin.register(QuestionTranslation)
class QuestionTranslationAdmin(admin.ModelAdmin):
    list_display = ['question', 'language', 'content_preview']
    list_filter = ['language']
    search_fields = ['content', 'question__road_sign_context__code']
    
    def content_preview(self, obj):
        return obj.content[:100] + '...' if len(obj.content) > 100 else obj.content
    content_preview.short_description = _('Content')


@admin.register(AnswerChoiceTranslation)
class AnswerChoiceTranslationAdmin(admin.ModelAdmin):
    list_display = ['answer_choice', 'language', 'text_preview', 'question_info']
    list_filter = ['language']
    search_fields = ['text', 'answer_choice__question__translations__content']
    
    def text_preview(self, obj):
        return obj.text[:50] + '...' if len(obj.text) > 50 else obj.text
    text_preview.short_description = _('Text')
    
    def question_info(self, obj):
        question = obj.answer_choice.question
        translation = question.translations.filter(language='en').first()
        return translation.content[:50] + '...' if translation else f"Q{question.id}"
    question_info.short_description = _('Question')


@admin.register(ExplanationTranslation)
class ExplanationTranslationAdmin(admin.ModelAdmin):
    list_display = ['explanation', 'language', 'detail_preview', 'question_info']
    list_filter = ['language']
    search_fields = ['detail', 'explanation__question__translations__content']
    
    def detail_preview(self, obj):
        return obj.detail[:100] + '...' if len(obj.detail) > 100 else obj.detail
    detail_preview.short_description = _('Detail')
    
    def question_info(self, obj):
        question = obj.explanation.question
        translation = question.translations.filter(language='en').first()
        return translation.content[:50] + '...' if translation else f"Q{question.id}"
    question_info.short_description = _('Question')


@admin.register(PaymentMethodTranslation)
class PaymentMethodTranslationAdmin(admin.ModelAdmin):
    list_display = ['payment_method', 'language', 'account_details_preview', 'instruction_preview']
    list_filter = ['language', 'payment_method']
    search_fields = ['account_details', 'instruction', 'payment_method__name']
    
    def account_details_preview(self, obj):
        return obj.account_details[:50] + '...' if len(obj.account_details) > 50 else obj.account_details
    account_details_preview.short_description = _('Account Details')
    
    def instruction_preview(self, obj):
        return obj.instruction[:100] + '...' if len(obj.instruction) > 100 else obj.instruction
    instruction_preview.short_description = _('Instruction')


# @admin.register(SubscriptionPlan)
# class SubscriptionPlanAdmin(admin.ModelAdmin):
#     list_display = ['name', 'plan_type', 'price_etb', 'duration_days', 'is_active', 'order']
#     list_filter = ['plan_type', 'is_active']
#     search_fields = ['name']
#     ordering = ['order', 'price_etb']

# @admin.register(UserSubscription)
# class UserSubscriptionAdmin(admin.ModelAdmin):
#     list_display = ['user', 'plan', 'amount_paid', 'payment_status', 'is_active', 'starts_at']
#     list_filter = ['payment_status', 'is_active', 'plan']
#     search_fields = ['user__username', 'reference_number', 'transaction_id']
#     raw_id_fields = ['user']

class ExamQuestionInline(admin.StackedInline):
    model = ExamQuestion
    extra = 0
    min_num = 0
    max_num = 1
    verbose_name = _("ExamQuestion")
    verbose_name_plural = _("ExamQuestions")

@admin.register(ExamSession)
class ExamSessionAdmin(admin.ModelAdmin):
    list_display = ['user', 'start_time', 'end_time', 'status', 'score', 'passed']
    list_filter = ['status', 'passed']
    search_fields = ['user__username']
    raw_id_fields = ['user']
    inlines = [ExamQuestionInline]

@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'is_premium', 'views', 'created_at']
    list_filter = ['category', 'is_premium']
    search_fields = ['title', 'content']
    prepopulated_fields = {'slug': ('title',)}

@admin.register(AIChatHistory)
class AIChatHistoryAdmin(admin.ModelAdmin):
    list_display = ['user', 'session_id', 'created_at', 'tokens_used']
    list_filter = ['session_id']
    search_fields = ['user__username', 'question', 'answer']
    raw_id_fields = ['user']
    


@admin.register(BundleDefinition)
class BundleDefinitionAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'price_display', 'validity_days', 'quota_summary', 'is_active', 'recommended', 'order')
    list_editable = ('is_active', 'recommended', 'order')
    search_fields = ('name', 'code')
    list_filter = ('is_active', 'recommended')
    
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('name', 'code', 'description', 'price_etb', 'validity_days')
        }),
        (_('Resource Quotas (0 = Unlimited)'), {
            'fields': ('exam_quota', 'total_chat_quota', 'daily_chat_limit', 'search_quota', 'has_unlimited_road_sign_quiz'),
            'description': _('Define the limitations for this bundle type.')
        }),
        (_('Display & Sorting'), {
            'fields': ('is_active', 'recommended', 'order'),
            'classes': ('collapse',)
        }),
    )

    def price_display(self, obj):
        return format_html("<b>{} ETB</b>", obj.price_etb)
    price_display.short_description = _("Price")

    def quota_summary(self, obj):
        return format_html(
            "Exams: {} | Chats: {} | Search: {}",
            "∞" if obj.is_unlimited_exams else obj.exam_quota,
            "∞" if obj.is_unlimited_chats else obj.total_chat_quota,
            "∞" if obj.is_unlimited_search else obj.search_quota
        )
    quota_summary.short_description = _("Quotas")
    
    
    
class ResourceTransactionInline(admin.TabularInline):
    model = ResourceTransaction
    extra = 0
    readonly_fields = ('transaction_type', 'resource_type', 'quantity', 'exams_after', 'chats_after', 'created_at')
    can_delete = False

@admin.register(UserBundle)
class UserBundleAdmin(admin.ModelAdmin):
    list_display = ('user', 'bundle_definition', 'expiry_status', 'exams_remaining', 'chats_remaining', 'is_active')
    list_filter = ('is_active', 'bundle_definition', 'expiry_date')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('purchase_date', 'total_chats_consumed', 'daily_chats_used', 'last_chat_reset')
    inlines = [ResourceTransactionInline]

    def expiry_status(self, obj):
        if obj.is_expired:
            return format_html('<span style="color: red;">Expired ({})</span>', obj.expiry_date.date())
        return format_html('<span style="color: green;">Expires {}</span>', obj.expiry_date.date())
    expiry_status.short_description = _("Status")

@admin.register(ResourceTransaction)
class ResourceTransactionAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'user', 'transaction_type', 'resource_type', 'quantity_display', 'reference')
    list_filter = ('transaction_type', 'resource_type', 'created_at')
    search_fields = ('user__username', 'reference', 'description')

    def quantity_display(self, obj):
        color = "green" if obj.quantity > 0 else "red"
        return format_html('<span style="color: {}; font-weight: bold;">{:+}</span>', color, obj.quantity)
    quantity_display.short_description = _("Qty")
    
    
@admin.register(BundleOrder)
class BundleOrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'bundle_definition', 'order_amount', 'status', 'reference_number', 'created_at')
    list_filter = ('status', 'payment_method', 'created_at')
    search_fields = ('reference_number', 'user__username', 'id')
    readonly_fields = ('ip_address', 'user_agent', 'expires_at')
    actions = ['mark_as_verified']

    def mark_as_verified(self, request, queryset):
        for order in queryset.filter(status=BundleOrder.OrderStatus.PENDING):
            order.status = BundleOrder.OrderStatus.PAYMENT_VERIFIED
            order.verified_amount = order.order_amount
            order.verified_at = timezone.now()
            order.save()
        self.message_user(request, _("Selected orders marked as verified."))
    mark_as_verified.short_description = _("Step 1: Verify Payment (Manual)")

@admin.register(BundlePurchase)
class BundlePurchaseAdmin(admin.ModelAdmin):
    list_display = ('user', 'bundle_definition', 'amount_paid', 'payment_status', 'reference_number', 'verified_by', 'created_at')
    list_filter = ('payment_status', 'payment_method', 'created_at')
    search_fields = ('reference_number', 'transaction_id', 'user__username')
    readonly_fields = ('verified_at', 'verified_by', 'user_bundle', 'ip_address', 'user_agent')
    
    fieldsets = (
        (_('Transaction Info'), {'fields': ('user', 'bundle_definition', 'order', 'user_bundle')}),
        (_('Payment Details'), {'fields': ('amount_paid', 'payment_method', 'payment_status', 'reference_number', 'transaction_id')}),
        (_('Verification Audit'), {'fields': ('verified_at', 'verified_by')}),
    )

    def save_model(self, request, obj, form, change):
        if not obj.pk and not obj.verified_by:
            obj.verified_by = request.user
        super().save_model(request, obj, form, change)

















# Model for managing language settings (if needed)
# @admin.register(Language)
# class LanguageAdmin(admin.ModelAdmin):
#     list_display = ['code', 'name']
#     readonly_fields = ['code', 'name']
    
#     def has_add_permission(self, request):
#         return False  # Languages are defined as enum, not editable
    
#     def has_delete_permission(self, request, obj=None):
#         return False
    
#     def get_queryset(self, request):
#         # Convert enum to queryset-like object
#         from django.db.models import Q
#         languages = []
#         for member in Language:
#             languages.append(type('LanguageObj', (), {
#                 'code': member.value,
#                 'name': member.name.replace('_', ' ').title(),
#                 'pk': member.value
#             })())
#         return type('FakeQuerySet', (), {
#             'filter': lambda **kwargs: [l for l in languages],
#             'all': lambda: languages,
#             'count': lambda: len(languages)
#         })()


































































# from django.contrib import admin
# from django.utils.html import format_html
# from django.utils.translation import gettext_lazy as _
# from django import forms
# from . import models


# class TranslationInlineFormSet(forms.models.BaseInlineFormSet):
#     """Formset to ensure at least one English translation"""
#     def clean(self):
#         super().clean()
#         has_english = False
#         for form in self.forms:
#             if not form.cleaned_data.get('DELETE', False):
#                 if form.cleaned_data.get('language') == 'en':
#                     has_english = True
#                     break
#         if not has_english and not self.instance._state.adding:
#             raise forms.ValidationError(
#                 _("At least one English translation is required.")
#             )


# class RoadSignTranslationInline(admin.TabularInline):
#     model = models.RoadSignTranslation
#     formset = TranslationInlineFormSet
#     extra = 1
#     min_num = 1
#     verbose_name = _("Translation")
#     verbose_name_plural = _("Translations")
#     fields = ['language', 'name', 'description']


# @admin.register(models.RoadSign)
# class RoadSignAdmin(admin.ModelAdmin):
#     list_display = ['code', 'image_preview', 'translations_count', 'created_at']
#     list_filter = ['created_at']
#     search_fields = ['code', 'translations__name', 'translations__description']
#     readonly_fields = ['id', 'created_at', 'updated_at']
#     inlines = [RoadSignTranslationInline]
    
#     fieldsets = (
#         (_('Basic Information'), {
#             'fields': ('id', 'code', 'image', 'created_at', 'updated_at')
#         }),
#     )
    
#     def image_preview(self, obj):
#         if obj.image:
#             return format_html('<img src="{}" width="50" height="50" />', obj.image.url)
#         return "-"
#     image_preview.short_description = _('Image')
    
#     def translations_count(self, obj):
#         return obj.translations.count()
#     translations_count.short_description = _('Translations')


# class QuestionTranslationInline(admin.TabularInline):
#     model = models.QuestionTranslation
#     formset = TranslationInlineFormSet
#     extra = 1
#     min_num = 1
#     verbose_name = _("Translation")
#     verbose_name_plural = _("Translations")
#     fields = ['language', 'content']


# class AnswerChoiceTranslationInline(admin.TabularInline):
#     model = models.AnswerChoiceTranslation
#     extra = 1
#     min_num = 1
#     verbose_name = _("Translation")
#     verbose_name_plural = _("Translations")
#     fields = ['language', 'text']


# class AnswerChoiceInline(admin.TabularInline):
#     model = models.AnswerChoice
#     extra = 0
#     min_num = 1
#     fields = ['is_correct', 'order']
#     ordering = ['order']
#     inlines = [AnswerChoiceTranslationInline]
#     verbose_name = _("Answer Choice")
#     verbose_name_plural = _("Answer Choices")
    
#     def get_queryset(self, request):
#         qs = super().get_queryset(request)
#         return qs.prefetch_related('translations')


# class ExplanationTranslationInline(admin.TabularInline):
#     model = models.ExplanationTranslation
#     extra = 1
#     min_num = 1
#     verbose_name = _("Translation")
#     verbose_name_plural = _("Translations")
#     fields = ['language', 'detail']


# class ExplanationInline(admin.StackedInline):
#     model = models.Explanation
#     extra = 0
#     min_num = 0
#     max_num = 1
#     fields = ['media_url', 'media_type']
#     inlines = [ExplanationTranslationInline]
#     verbose_name = _("Explanation")
#     verbose_name_plural = _("Explanations")


# @admin.register(models.Question)
# class QuestionAdmin(admin.ModelAdmin):
#     list_display = ['id_short', 'road_sign', 'is_premium', 'difficulty', 'translations_count', 'created_at']
#     list_filter = ['is_premium', 'difficulty', 'created_at']
#     search_fields = ['translations__content', 'road_sign__code']
#     readonly_fields = ['id', 'created_at', 'updated_at']
#     inlines = [QuestionTranslationInline, AnswerChoiceInline, ExplanationInline]
    
#     fieldsets = (
#         (_('Basic Information'), {
#             'fields': ('id', 'road_sign', 'is_premium', 'difficulty', 'created_at', 'updated_at')
#         }),
#     )
    
#     def id_short(self, obj):
#         return str(obj.id)[:8]
#     id_short.short_description = _('ID')
    
#     def translations_count(self, obj):
#         return obj.translations.count()
#     translations_count.short_description = _('Translations')
    
#     def get_queryset(self, request):
#         qs = super().get_queryset(request)
#         return qs.prefetch_related('translations', 'choices', 'explanation')

# @admin.register(models.UserProgress)
# class UserProgressAdmin(admin.ModelAdmin):
#     list_display = ['user', 'question_preview', 'is_correct', 'time_taken', 'created_at']
#     list_filter = ['is_correct', 'created_at']
#     search_fields = ['user__username', 'question__translations__content']
#     readonly_fields = ['id', 'created_at']
#     date_hierarchy = 'created_at'
    
#     def question_preview(self, obj):
#         translation = obj.question.translations.filter(language='en').first()
#         if translation:
#             return translation.content[:50] + '...' if len(translation.content) > 50 else translation.content
#         return f"Question {obj.question.id}"
#     question_preview.short_description = _('Question')
    
#     def get_queryset(self, request):
#         qs = super().get_queryset(request)
#         return qs.select_related('question', 'selected_answer').prefetch_related('question__translations')


# @admin.register(models.UserProfile)
# class UserProfileAdmin(admin.ModelAdmin):
#     list_display = ['user', 'telegram_username', 'is_pro_user', 'pro_since']
#     list_filter = ['is_pro_user', 'created_at']
#     search_fields = ['user__username', 'telegram_username', 'user__email']
#     readonly_fields = ['created_at', 'updated_at', 'last_active']
#     fieldsets = (
#         (_('User Information'), {
#             'fields': ('user', 'telegram_id', 'telegram_username', 'telegram_data')
#         }),
#         (_('Subscription'), {
#             'fields': ('is_pro_user', 'pro_since', 'pro_expires')
#         }),
#         (_('Statistics'), {
#             'fields': ('total_attempts', 'correct_answers')
#         }),
#         (_('Metadata'), {
#             'fields': ('created_at', 'updated_at', 'last_active')
#         }),
#     )
    
#     # def accuracy_display(self, obj):
#     #     return f"{obj.accuracy:.1f}%"
#     # accuracy_display.short_description = _('Accuracy')


# class PaymentMethodTranslationInline(admin.TabularInline):
#     model = models.PaymentMethodTranslation
#     formset = TranslationInlineFormSet
#     extra = 1
#     min_num = 1
#     verbose_name = _("Translation")
#     verbose_name_plural = _("Translations")
#     fields = ['language', 'account_details', 'instruction']


# @admin.register(models.PaymentMethod)
# class PaymentMethodAdmin(admin.ModelAdmin):
#     list_display = ['name', 'code', 'is_active', 'order', 'translations_count', 'created_at']
#     list_filter = ['is_active', 'created_at']
#     search_fields = ['name', 'code', 'translations__account_details']
#     readonly_fields = ['id', 'created_at', 'updated_at']
#     inlines = [PaymentMethodTranslationInline]
    
#     fieldsets = (
#         (_('Basic Information'), {
#             'fields': ('id', 'name', 'code', 'is_active', 'order')
#         }),
#         (_('Metadata'), {
#             'fields': ('created_at', 'updated_at')
#         }),
#     )
    
#     def translations_count(self, obj):
#         return obj.translations.count()
#     translations_count.short_description = _('Translations')


# # Translation model admins for direct access
# @admin.register(models.RoadSignTranslation)
# class RoadSignTranslationAdmin(admin.ModelAdmin):
#     list_display = ['road_sign', 'language', 'name']
#     list_filter = ['language', 'road_sign']
#     search_fields = ['name', 'description', 'road_sign__code']


# class RoadSignCategoryTranslationInline(admin.TabularInline):
#     model = models.RoadSignCategoryTranslation
#     extra = 1
#     min_num = 1
#     verbose_name = _("Translation")
#     verbose_name_plural = _("Translations")
#     fields = ['language', 'name', 'description']
    
# @admin.register(models.RoadSignCategory)
# class RoadSignCategoryAdmin(admin.ModelAdmin):
#     list_display = ['code', 'order', 'translations_count', 'road_signs_count']
#     list_filter = ['order']
#     search_fields = ['code', 'translations__name']
#     readonly_fields = ['id', 'created_at', 'updated_at']
#     inlines = [RoadSignCategoryTranslationInline]
    
#     def translations_count(self, obj):
#         return obj.translations.count()
#     translations_count.short_description = _('Translations')
    
#     def road_signs_count(self, obj):
#         return obj.road_signs.count()
#     road_signs_count.short_description = _('Road Signs')
    
    
# @admin.register(models.QuestionTranslation)
# class QuestionTranslationAdmin(admin.ModelAdmin):
#     list_display = ['question', 'language', 'content_preview']
#     list_filter = ['language']
#     search_fields = ['content', 'question__road_sign__code']
    
#     def content_preview(self, obj):
#         return obj.content[:100] + '...' if len(obj.content) > 100 else obj.content
#     content_preview.short_description = _('Content')


# @admin.register(models.AnswerChoiceTranslation)
# class AnswerChoiceTranslationAdmin(admin.ModelAdmin):
#     list_display = ['answer_choice', 'language', 'text_preview']
#     list_filter = ['language']
#     search_fields = ['text', 'answer_choice__question__translations__content']
    
#     def text_preview(self, obj):
#         return obj.text[:50] + '...' if len(obj.text) > 50 else obj.text
#     text_preview.short_description = _('Text')


# @admin.register(models.ExplanationTranslation)
# class ExplanationTranslationAdmin(admin.ModelAdmin):
#     list_display = ['explanation', 'language', 'detail_preview']
#     list_filter = ['language']
#     search_fields = ['detail', 'explanation__question__translations__content']
    
#     def detail_preview(self, obj):
#         return obj.detail[:100] + '...' if len(obj.detail) > 100 else obj.detail
#     detail_preview.short_description = _('Detail')


# @admin.register(models.PaymentMethodTranslation)
# class PaymentMethodTranslationAdmin(admin.ModelAdmin):
#     list_display = ['payment_method', 'language', 'account_details_preview']
#     list_filter = ['language', 'payment_method']
#     search_fields = ['account_details', 'instruction', 'payment_method__name']
    
#     def account_details_preview(self, obj):
#         return obj.account_details[:50] + '...' if len(obj.account_details) > 50 else obj.account_details
#     account_details_preview.short_description = _('Account Details')
    