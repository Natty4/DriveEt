# core/serializers.py
from rest_framework import serializers
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken
from . import models
import uuid


# class UserProfileSerializer(serializers.ModelSerializer):
#     accuracy = serializers.FloatField(read_only=True)
    
#     class Meta:
#         model = models.UserProfile
#         fields = [
#             'telegram_id', 'telegram_username', 'total_exam_attempts',
#             'correct_answers', 'accuracy', 'offline_cache_token'
#         ]

class BundleDefinitionSerializer(serializers.ModelSerializer):
    """Serializer for BundleDefinition"""
    
    class Meta:
        model = models.BundleDefinition
        fields = [
            'id', 'name', 'code', 'description',
            'exam_quota', 'total_chat_quota', 'daily_chat_limit',
            'search_quota', 'has_unlimited_road_sign_quiz',
            'validity_days', 'price_etb', 'recommended', 'is_active', 'order',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class UserBundleSerializer(serializers.ModelSerializer):
    """Serializer for UserBundle"""
    bundle_definition = BundleDefinitionSerializer(read_only=True)
    days_remaining = serializers.SerializerMethodField()
    is_expired = serializers.SerializerMethodField()
    
    class Meta:
        model = models.UserBundle
        fields = [
            'id', 'bundle_definition', 'purchase_date', 'expiry_date',
            'is_active', 'exams_remaining', 'chats_remaining',
            'search_remaining', 'total_chats_consumed', 'daily_chats_used',
            'last_chat_reset', 'days_remaining', 'is_expired',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_days_remaining(self, obj):
        from django.utils import timezone
        if obj.is_expired:
            return 0
        return max(0, (obj.expiry_date - timezone.now()).days)
    
    def get_is_expired(self, obj):
        return obj.is_expired


class UserProfileSerializer(serializers.ModelSerializer):
    """Updated UserProfile serializer with bundle info"""
    active_bundle = UserBundleSerializer(read_only=True)
    accuracy = serializers.FloatField(read_only=True)
    has_active_bundle = serializers.BooleanField(read_only=True)
    bundle_remaining_resources = serializers.DictField(read_only=True)
    
    class Meta:
        model = models.UserProfile
        fields = [
            'telegram_id', 'telegram_username', 'active_bundle',
            'has_active_bundle', 'bundle_remaining_resources',
            'total_exam_attempts', 'total_practice_questions',
            'correct_answers', 'accuracy', 'highest_exam_score',
            'preferred_language', 'exam_time_limit',
            'questions_per_exam', 'last_active'
        ]

class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'profile']


# Telegram JWT Response Serializer
class TelegramAuthResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()
    user = UserSerializer()

    @staticmethod
    def build(user: User):
        refresh = RefreshToken.for_user(user)

        # Telegram-only claims
        refresh["source"] = "telegram"
        refresh["telegram_id"] = user.profile.telegram_id

        return {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": UserSerializer(user).data,
        }

class TranslationSerializerMixin:
    """Mixin to add translation methods"""
    
    def get_translations_dict(self, obj, translation_model, fields):
        """Get all translations as a dictionary"""
        translations = {}
        for translation in translation_model.objects.filter(
            **{self.get_translation_fk_field(): obj}
        ):
            translation_data = {}
            for field in fields:
                translation_data[field] = getattr(translation, field)
            translations[translation.language] = translation_data
        return translations

class QuestionCategoryTranslationSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.QuestionCategoryTranslation
        fields = ['language', 'name', 'description']


class QuestionCategorySerializer(serializers.ModelSerializer):
    translations = serializers.SerializerMethodField()
    
    class Meta:
        model = models.QuestionCategory
        fields = ['id', 'code', 'order', 'translations']
    
    def get_translations(self, obj):
        """Get all translations as a dictionary"""
        translations = {}
        for translation in obj.translations.all():
            translations[translation.language] = {
                'name': translation.name,
                'description': translation.description
            }
        return translations


class RoadSignCategoryTranslationSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.RoadSignCategoryTranslation
        fields = ['language', 'name', 'description']

class RoadSignCategorySerializer(serializers.ModelSerializer):
    translations = serializers.SerializerMethodField()
    
    class Meta:
        model = models.RoadSignCategory
        fields = ['id', 'code', 'order', 'translations']
    
    def get_translations(self, obj):
        """Get all translations as a dictionary"""
        translations = {}
        for translation in obj.translations.all():
            translations[translation.language] = {
                'name': translation.name,
                'description': translation.description
            }
        return translations


class RoadSignTranslationSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.RoadSignTranslation
        fields = ['language', 'name', 'meaning', 'detailed_explanation']


class RoadSignSerializer(serializers.ModelSerializer, TranslationSerializerMixin):
    translations = serializers.SerializerMethodField()
    category = RoadSignCategorySerializer(read_only=True)
    
    class Meta:
        model = models.RoadSign
        fields = ['id', 'code', 'image', 'category', 'translations']
    
    def get_translations(self, obj):
        """Get all translations for the road sign"""
        return self.get_translations_dict(
            obj, 
            models.RoadSignTranslation,
            ['name', 'meaning', 'detailed_explanation']
        )
    
    def get_translation_fk_field(self):
        return 'road_sign'


class QuestionTranslationSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.QuestionTranslation
        fields = ['language', 'content']


class AnswerChoiceTranslationSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.AnswerChoiceTranslation
        fields = ['language', 'text']


class AnswerChoiceSerializer(serializers.ModelSerializer, TranslationSerializerMixin):
    translations = serializers.SerializerMethodField()
    road_sign_option = RoadSignSerializer(read_only=True)
    
    class Meta:
        model = models.AnswerChoice
        fields = [
            'id', 'translations', 'road_sign_option',
            'is_correct', 'order'
        ]
    
    def get_translations(self, obj):
        """Get all translations for the answer choice"""
        # For image-based choices (road_sign_option), we don't need text translations
        if obj.road_sign_option:
            return {}
        
        return self.get_translations_dict(
            obj,
            models.AnswerChoiceTranslation,
            ['text']
        )
    
    def get_translation_fk_field(self):
        return 'answer_choice'


class ExplanationTranslationSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.ExplanationTranslation
        fields = ['language', 'detail']


class ExplanationSerializer(serializers.ModelSerializer, TranslationSerializerMixin):
    translations = serializers.SerializerMethodField()
    
    class Meta:
        model = models.Explanation
        fields = ['id', 'translations', 'media_url', 'media_type']
    
    def get_translations(self, obj):
        """Get all translations for the explanation"""
        return self.get_translations_dict(
            obj,
            models.ExplanationTranslation,
            ['detail']
        )
    
    def get_translation_fk_field(self):
        return 'explanation'


class QuestionSerializer(serializers.ModelSerializer, TranslationSerializerMixin):
    road_sign_context = RoadSignSerializer(read_only=True)
    translations = serializers.SerializerMethodField()
    choices = AnswerChoiceSerializer(many=True, read_only=True)
    explanation = ExplanationSerializer(read_only=True)
    question_type_display = serializers.SerializerMethodField()
    category = QuestionCategorySerializer(read_only=True)

    class Meta:
        model = models.Question
        fields = [
            'id', 'road_sign_context', 'translations','category', 
            'question_type', 'question_type_display','is_premium', 
            'difficulty', 'choices', 'explanation', 'created_at'
        ]
        

    def get_translations(self, obj):
        """Get all translations for the question"""
        return self.get_translations_dict(
            obj,
            models.QuestionTranslation,
            ['content']
        )
        
    def get_translation_fk_field(self):
        return 'question'

    # Implement the method to calculate the field's value
    def get_question_type_display(self, obj):
        """Returns the human-readable display value for question_type."""
        # This calls the method Django adds to models with choices
        return obj.get_question_type_display()
    

    def to_representation(self, instance):
        """
        Override to add fields that are properties on the model instance.
        The question_type_display assignment has been REMOVED.
        """
        data = super().to_representation(instance)
        # These fields are properties on the Question model
        data['is_image_to_text'] = instance.is_image_to_text
        data['is_text_to_image'] = instance.is_text_to_image
        data['is_text_to_text'] = instance.is_text_to_text
        return data
    

class OptimizedQuestionSerializer(serializers.ModelSerializer):
    """
    Optimized serializer for the /questions/all/ endpoint
    Returns all data in a single structure for PWA caching
    """
    road_sign_context = serializers.SerializerMethodField()
    translations = serializers.SerializerMethodField()
    choices = serializers.SerializerMethodField()
    explanation = serializers.SerializerMethodField()
    
    class Meta:
        model = models.Question
        fields = [
            'id', 'road_sign_context', 'translations', 'question_type',
            'is_premium', 'difficulty', 'choices', 'explanation'
        ]
    
    def get_road_sign_context(self, obj):
        """Get road sign with all translations"""
        road_sign = obj.road_sign_context
        return {
            'id': str(road_sign.id),
            'code': road_sign.code,
            'image': road_sign.image.url if road_sign.image else None,
            'category': {
                'id': str(road_sign.category.id) if road_sign.category else None,
                'code': road_sign.category.code if road_sign.category else None,
                'translations': self._get_category_translations(road_sign.category)
            } if road_sign.category else None,
            'translations': self._get_road_sign_translations(road_sign)
        }
    
    def _get_category_translations(self, category):
        """Get all translations for a category"""
        if not category:
            return {}
        translations = {}
        for trans in category.translations.all():
            translations[trans.language] = {
                'name': trans.name,
                'description': trans.description
            }
        return translations
    
    def _get_road_sign_translations(self, road_sign):
        """Get all translations for a road sign"""
        translations = {}
        for trans in road_sign.translations.all():
            translations[trans.language] = {
                'name': trans.name,
                'meaning': trans.meaning,
                'detailed_explanation': trans.detailed_explanation
            }
        return translations
    
    def get_translations(self, obj):
        """Get all translations for the question"""
        translations = {}
        for trans in obj.translations.all():
            translations[trans.language] = {
                'content': trans.content
            }
        return translations
    
    def get_choices(self, obj):
        """Get all choices with their translations"""
        choices_data = []
        for choice in obj.choices.all():
            choice_data = {
                'id': str(choice.id),
                'is_correct': choice.is_correct,
                'order': choice.order,
                'is_image_option': choice.is_image_option
            }
            
            if choice.road_sign_option:
                # For image-based choices
                choice_data['road_sign_option'] = {
                    'id': str(choice.road_sign_option.id),
                    'code': choice.road_sign_option.code,
                    'image': choice.road_sign_option.image.url if choice.road_sign_option.image else None,
                    'translations': self._get_road_sign_translations(choice.road_sign_option)
                }
                choice_data['translations'] = {}  # No text translations for image options
            else:
                # For text-based choices
                text_translations = {}
                for trans in choice.translations.all():
                    text_translations[trans.language] = {
                        'text': trans.text
                    }
                choice_data['translations'] = text_translations
                choice_data['road_sign_option'] = None
            
            choices_data.append(choice_data)
        return choices_data
    
    def get_explanation(self, obj):
        """Get explanation if exists"""
        if hasattr(obj, 'explanation'):
            explanation = obj.explanation
            explanation_translations = {}
            for trans in explanation.translations.all():
                explanation_translations[trans.language] = {
                    'detail': trans.detail
                }
            
            return {
                'id': str(explanation.id),
                'media_url': explanation.media_url,
                'media_type': explanation.media_type,
                'translations': explanation_translations
            }
        return None


class PaymentMethodTranslationSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.PaymentMethodTranslation
        fields = ['language', 'account_details', 'instruction']


class PaymentMethodSerializer(serializers.ModelSerializer):
    translations = PaymentMethodTranslationSerializer(many=True, read_only=True)
    account_details = serializers.SerializerMethodField()
    instruction = serializers.SerializerMethodField()
    
    class Meta:
        model = models.PaymentMethod
        fields = [
            'id', 'name', 'code', 'logo', 'is_active', 'order', 'amount',
            'translations', 'account_details', 'instruction'
        ]
    
    def get_account_details(self, obj):
        """Get account details in requested language or English"""
        request = self.context.get('request')
        language = request.query_params.get('lang', 'en') if request else 'en'
        
        translation = obj.translations.filter(language=language).first()
        if not translation and language != 'en':
            translation = obj.translations.filter(language='en').first()
        
        return translation.account_details if translation else ''
    
    def get_instruction(self, obj):
        """Get instruction in requested language or English"""
        request = self.context.get('request')
        language = request.query_params.get('lang', 'en') if request else 'en'
        
        translation = obj.translations.filter(language=language).first()
        if not translation and language != 'en':
            translation = obj.translations.filter(language='en').first()
        
        return translation.instruction if translation else ''


class OfflineCacheDataSerializer(serializers.Serializer):
    """Serializer for offline cache data dump"""
    questions = serializers.ListField(child=serializers.DictField())
    road_signs = serializers.ListField(child=serializers.DictField())
    categories = serializers.ListField(child=serializers.DictField())
    payment_methods = serializers.ListField(child=serializers.DictField())
    cache_token = serializers.UUIDField()
    generated_at = serializers.DateTimeField()
    expires_at = serializers.DateTimeField()


class SearchResultSerializer(serializers.Serializer):
    """Serializer for search results"""
    type = serializers.CharField()  # 'road_sign' or 'question'
    id = serializers.UUIDField()
    relevance = serializers.FloatField()
    match_field = serializers.CharField()
    match_text = serializers.CharField()
    data = serializers.DictField()


# class SubscriptionPlanSerializer(serializers.ModelSerializer):
#     features = serializers.ListField(child=serializers.CharField())
#     plan_type_display = serializers.SerializerMethodField()
    
#     class Meta:
#         model = models.SubscriptionPlan
#         fields = [
#             'id', 'name', 'plan_type', 'plan_type_display', 'price_etb', 
#             'duration_days', 'features', 'recommended_plan', 'is_active'
#         ]
        
#     def get_plan_type_display(self, obj):
#         """Returns the human-readable display value for plan_type."""
#         # This calls the method Django adds to models with choices
#         return obj.get_plan_type_display()


# class UserSubscriptionSerializer(serializers.ModelSerializer):
#     plan = SubscriptionPlanSerializer(read_only=True)
#     payment_method_name = serializers.CharField(source='payment_method.name', read_only=True)
    
#     class Meta:
#         model = models.UserSubscription
#         fields = [
#             'id', 'plan', 'payment_method_name', 'amount_paid',
#             'payment_status', 'starts_at', 'expires_at', 'is_active'
#         ]


class ExamQuestionSerializer(serializers.ModelSerializer):
    question = QuestionSerializer(read_only=True)
    selected_answer = AnswerChoiceSerializer(read_only=True)
    
    class Meta:
        model = models.ExamQuestion
        fields = [
            'id', 'question', 'order', 'selected_answer',
            'is_correct', 'time_spent'
        ]


class ExamSessionSerializer(serializers.ModelSerializer):
    questions = ExamQuestionSerializer(source='examquestion_set', many=True, read_only=True)
    user = UserSerializer(read_only=True)
    time_taken_formatted = serializers.SerializerMethodField()
    
    class Meta:
        model = models.ExamSession
        fields = [
            'id', 'user', 'start_time', 'end_time', 'status',
            'score', 'time_taken', 'time_taken_formatted', 'passed',
            'questions'
        ]
    
    def get_time_taken_formatted(self, obj):
        if not obj.time_taken:
            return None
        minutes = obj.time_taken // 60
        seconds = obj.time_taken % 60
        return f"{minutes}m {seconds}s"


class ArticleCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = models.ArticleCategory
        fields = ['id', 'name', 'slug', 'order']


class ArticleSerializer(serializers.ModelSerializer):
    category = ArticleCategorySerializer(read_only=True)
    excerpt = serializers.SerializerMethodField()
    
    class Meta:
        model = models.Article
        fields = [
            'id', 'title', 'slug', 'excerpt', 'content',
            'category', 'is_premium', 'tags', 'views',
            'created_at', 'updated_at'
        ]
    
    def get_excerpt(self, obj):
        return obj.content[:150] + '...' if len(obj.content) > 150 else obj.content


class AIChatHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = models.AIChatHistory
        fields = ['id', 'question', 'answer', 'created_at']


class PaymentVerificationSerializer(serializers.Serializer):
    reference_number = serializers.CharField(max_length=100, required=True)
    sender_last_5_digits = serializers.CharField(max_length=5, required=False)
    payment_method = serializers.CharField(max_length=50, required=True)
    
    def validate_payment_method(self, value):
        valid_methods = ['TELEBIRR', 'BOA', 'DASHEN']
        if value.upper() not in valid_methods:
            raise serializers.ValidationError(
                f"Invalid payment method. Valid options: {', '.join(valid_methods)}"
            )
        return value.upper()





class ResourceTransactionSerializer(serializers.ModelSerializer):
    """Serializer for ResourceTransaction"""
    
    class Meta:
        model = models.ResourceTransaction
        fields = [
            'id', 'user', 'user_bundle', 'transaction_type',
            'resource_type', 'quantity', 'exams_before',
            'exams_after', 'chats_before', 'chats_after',
            'search_before', 'search_after', 'reference',
            'description', 'ip_address', 'user_agent',
            'created_at'
        ]
        read_only_fields = ['created_at']


class BundlePurchaseSerializer(serializers.ModelSerializer):
    """Serializer for BundlePurchase"""
    bundle_definition = BundleDefinitionSerializer(read_only=True)
    user_bundle = UserBundleSerializer(read_only=True)
    payment_method_name = serializers.CharField(source='payment_method.name', read_only=True)
    
    class Meta:
        model = models.BundlePurchase
        fields = [
            'id', 'user', 'bundle_definition', 'amount_paid',
            'payment_method', 'payment_method_name', 'payment_status',
            'reference_number', 'transaction_id', 'user_bundle',
            'verified_at', 'verified_by', 'ip_address', 'user_agent',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']



class BundlePurchaseRequestSerializer(serializers.Serializer):
    """Serializer for bundle purchase requests"""
    bundle_definition_id = serializers.UUIDField(required=True)
    reference_number = serializers.CharField(max_length=100, required=True)
    transaction_id = serializers.CharField(max_length=100, required=False)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    payment_method_id = serializers.UUIDField(required=True)
    
    def validate(self, data):
        # Validate bundle exists and is active
        from core.models import BundleDefinition
        try:
            bundle = BundleDefinition.objects.get(
                id=data['bundle_definition_id'],
                is_active=True
            )
            data['bundle_definition'] = bundle
        except BundleDefinition.DoesNotExist:
            raise serializers.ValidationError("Bundle not found or inactive")
        
        # Validate amount if provided
        if 'amount' in data and data['amount'] < bundle.price_etb:
            raise serializers.ValidationError(
                f"Amount must be at least {bundle.price_etb} ETB"
            )
        
        return data


class ResourceConsumptionResponseSerializer(serializers.Serializer):
    """Serializer for resource consumption responses"""
    success = serializers.BooleanField()
    message = serializers.CharField()
    remaining_resources = serializers.DictField()
    transaction_id = serializers.UUIDField(required=False)


class BundleOrderSerializer(serializers.ModelSerializer):
    """Serializer for BundleOrder"""
    bundle_definition = BundleDefinitionSerializer(read_only=True)
    payment_method = PaymentMethodSerializer(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    amount_difference = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = models.BundleOrder
        fields = [
            'id', 'bundle_definition', 'order_amount', 'status',
            'payment_method', 'reference_number', 'verified_amount',
            'verified_at', 'resulting_bundle', 'is_expired',
            'amount_difference', 'expires_at', 'created_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class BundleSuggestionSerializer(serializers.Serializer):
    """Serializer for bundle suggestions"""
    bundle = BundleDefinitionSerializer()
    reason = serializers.CharField()
    score = serializers.FloatField()
    remaining_budget = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    deficit = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)


class CreateOrderRequestSerializer(serializers.Serializer):
    """Serializer for creating orders"""
    bundle_definition_id = serializers.UUIDField(required=True)
    payment_method_id = serializers.UUIDField(required=True)
    
    def validate(self, data):
        # Validate bundle exists and is active
        try:
            bundle = models.BundleDefinition.objects.get(
                id=data['bundle_definition_id'],
                is_active=True
            )
            data['bundle_definition'] = bundle
        except models.BundleDefinition.DoesNotExist:
            raise serializers.ValidationError("Bundle not found or inactive")
        
        # Validate payment method
        try:
            payment_method = models.PaymentMethod.objects.get(
                id=data['payment_method_id'],
                is_active=True
            )
            data['payment_method'] = payment_method
        except models.PaymentMethod.DoesNotExist:
            raise serializers.ValidationError("Payment method not found or inactive")
        
        return data


class VerifyPaymentRequestSerializer(serializers.Serializer):
    """Serializer for payment verification"""
    order_id = serializers.UUIDField(required=True)
    reference_number = serializers.CharField(max_length=100, required=True)
    sender_last_5_digits = serializers.CharField(max_length=5, required=False)


class AcceptSuggestionRequestSerializer(serializers.Serializer):
    """Serializer for accepting suggestions"""
    order_id = serializers.UUIDField(required=True)
    suggested_bundle_id = serializers.UUIDField(required=True)


class PaymentVerificationResponseSerializer(serializers.Serializer):
    """Serializer for payment verification responses"""
    success = serializers.BooleanField()
    status = serializers.CharField()
    message = serializers.CharField()
    verified_amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    required_amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    deficit = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    suggestions = BundleSuggestionSerializer(many=True, required=False)
    can_upgrade_existing = serializers.DictField(required=False)
    order = BundleOrderSerializer(required=False)
    bundle = UserBundleSerializer(required=False)
    remaining_resources = serializers.DictField(required=False)









































# from rest_framework import serializers
# from django.contrib.auth.models import User
# from rest_framework_simplejwt.tokens import RefreshToken
# from . import models


# class UserSerializer(serializers.ModelSerializer):
#     is_pro_user = serializers.BooleanField(source='profile.is_pro_user', read_only=True)
    
#     class Meta:
#         model = models.User
#         fields = ['id', 'username', 'email', 'is_pro_user']


# class TranslationSerializer(serializers.Serializer):
#     """Base serializer for translations"""
#     en = serializers.CharField(required=True)
#     am = serializers.CharField(required=False, allow_blank=True)
#     or_ET = serializers.CharField(required=False, allow_blank=True)
#     ti = serializers.CharField(required=False, allow_blank=True)


# class RoadSignTranslationSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = models.RoadSignTranslation
#         fields = ['language', 'name', 'description']


# class RoadSignSerializer(serializers.ModelSerializer):
#     translations = RoadSignTranslationSerializer(many=True, read_only=True)
#     name = serializers.SerializerMethodField()
#     description = serializers.SerializerMethodField()
    
#     class Meta:
#         model = models.RoadSign
#         fields = ['id', 'code', 'image', 'translations', 'name', 'description']
    
#     def get_name(self, obj):
#         """Get name in requested language or English"""
#         request = self.context.get('request')
#         language = request.query_params.get('lang', 'en') if request else 'en'
        
#         translation = obj.translations.filter(language=language).first()
#         if not translation and language != 'en':
#             translation = obj.translations.filter(language='en').first()
        
#         return translation.name if translation else obj.code
    
#     def get_description(self, obj):
#         """Get description in requested language or English"""
#         request = self.context.get('request')
#         language = request.query_params.get('lang', 'en') if request else 'en'
        
#         translation = obj.translations.filter(language=language).first()
#         if not translation and language != 'en':
#             translation = obj.translations.filter(language='en').first()
        
#         return translation.description if translation else ''


# class QuestionTranslationSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = models.QuestionTranslation
#         fields = ['language', 'content']


# class AnswerChoiceTranslationSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = models.AnswerChoiceTranslation
#         fields = ['language', 'text']


# class AnswerChoiceSerializer(serializers.ModelSerializer):
#     translations = AnswerChoiceTranslationSerializer(many=True, read_only=True)
#     text = serializers.SerializerMethodField()
    
#     class Meta:
#         model = models.AnswerChoice
#         fields = ['id', 'translations', 'text', 'is_correct', 'order']
    
#     def get_text(self, obj):
#         """Get text in requested language or English"""
#         request = self.context.get('request')
#         language = request.query_params.get('lang', 'en') if request else 'en'
        
#         translation = obj.translations.filter(language=language).first()
#         if not translation and language != 'en':
#             translation = obj.translations.filter(language='en').first()
        
#         return translation.text if translation else ''


# class ExplanationTranslationSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = models.ExplanationTranslation
#         fields = ['language', 'detail']


# class ExplanationSerializer(serializers.ModelSerializer):
#     translations = ExplanationTranslationSerializer(many=True, read_only=True)
#     detail = serializers.SerializerMethodField()
    
#     class Meta:
#         model = models.Explanation
#         fields = ['id', 'translations', 'detail', 'media_url', 'media_type']
    
#     def get_detail(self, obj):
#         """Get detail in requested language or English"""
#         request = self.context.get('request')
#         language = request.query_params.get('lang', 'en') if request else 'en'
        
#         translation = obj.translations.filter(language=language).first()
#         if not translation and language != 'en':
#             translation = obj.translations.filter(language='en').first()
        
#         return translation.detail if translation else ''


# class QuestionSerializer(serializers.ModelSerializer):
#     road_sign = RoadSignSerializer(read_only=True)
#     translations = QuestionTranslationSerializer(many=True, read_only=True)
#     choices = AnswerChoiceSerializer(many=True, read_only=True)
#     explanation = ExplanationSerializer(read_only=True)
#     content = serializers.SerializerMethodField()
    
#     class Meta:
#         model = models.Question
#         fields = ['id', 'road_sign', 'translations', 'content', 'is_premium', 
#                  'difficulty', 'choices', 'explanation']
    
#     def get_content(self, obj):
#         """Get content in requested language or English"""
#         request = self.context.get('request')
#         language = request.query_params.get('lang', 'en') if request else 'en'
        
#         translation = obj.translations.filter(language=language).first()
#         if not translation and language != 'en':
#             translation = obj.translations.filter(language='en').first()
        
#         return translation.content if translation else ''


# class PaymentMethodTranslationSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = models.PaymentMethodTranslation
#         fields = ['language', 'account_details', 'instruction']


# class PaymentMethodSerializer(serializers.ModelSerializer):
#     translations = PaymentMethodTranslationSerializer(many=True, read_only=True)
#     account_details = serializers.SerializerMethodField()
#     instruction = serializers.SerializerMethodField()
    
#     class Meta:
#         model = models.PaymentMethod
#         fields = ['id', 'name', 'code', 'is_active', 'order', 
#                  'translations', 'account_details', 'instruction']
    
#     def get_account_details(self, obj):
#         """Get account details in requested language or English"""
#         request = self.context.get('request')
#         language = request.query_params.get('lang', 'en') if request else 'en'
        
#         translation = obj.translations.filter(language=language).first()
#         if not translation and language != 'en':
#             translation = obj.translations.filter(language='en').first()
        
#         return translation.account_details if translation else ''
    
#     def get_instruction(self, obj):
#         """Get instruction in requested language or English"""
#         request = self.context.get('request')
#         language = request.query_params.get('lang', 'en') if request else 'en'
        
#         translation = obj.translations.filter(language=language).first()
#         if not translation and language != 'en':
#             translation = obj.translations.filter(language='en').first()
        
#         return translation.instruction if translation else ''


# class UserProgressSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = models.UserProgress
#         fields = ['id', 'question', 'selected_answer', 'is_correct',
#                  'time_taken', 'session_id', 'created_at']
#         read_only_fields = ['user', 'created_at']


# # Simplified serializers for optimized responses
# class OptimizedQuestionSerializer(serializers.ModelSerializer):
#     """Serializer optimized for frontend consumption"""
#     road_sign_code = serializers.CharField(source='road_sign.code', read_only=True)
#     road_sign_image = serializers.ImageField(source='road_sign.image', read_only=True)
#     content = serializers.SerializerMethodField()
#     choices = serializers.SerializerMethodField()
#     explanation = serializers.SerializerMethodField()
    
#     class Meta:
#         model = models.Question
#         fields = ['id', 'road_sign_code', 'road_sign_image', 'content', 
#                  'is_premium', 'difficulty', 'choices', 'explanation']
    
#     def get_content(self, obj):
#         """Get all translations as a dict"""
#         translations = obj.translations.all()
#         return {t.language: t.content for t in translations}
    
#     def get_choices(self, obj):
#         """Get all choices with their translations"""
#         choices_data = []
#         for choice in obj.choices.all():
#             choice_translations = choice.translations.all()
#             choices_data.append({
#                 'id': str(choice.id),
#                 'translations': {t.language: t.text for t in choice_translations},
#                 'is_correct': choice.is_correct,
#                 'order': choice.order
#             })
#         return choices_data
    
#     def get_explanation(self, obj):
#         """Get explanation with translations if exists"""
#         if hasattr(obj, 'explanation'):
#             explanation = obj.explanation
#             explanation_translations = explanation.translations.all()
#             return {
#                 'media_url': explanation.media_url,
#                 'media_type': explanation.media_type,
#                 'translations': {t.language: t.detail for t in explanation_translations}
#             }
#         return None




# class TelegramLoginSerializer(serializers.Serializer):
#     init_data = serializers.CharField(required=True)
    
#     def validate(self, attrs):
#         # In production, verify Telegram WebApp initData
#         # For now, we'll simulate user creation/authentication
#         init_data = attrs.get('init_data')
        
#         # Parse simulated Telegram data
#         # In real implementation, verify hash with Telegram Bot token
#         try:
#             # Simulate parsing - replace with actual Telegram verification
#             import urllib.parse
#             params = urllib.parse.parse_qs(init_data)
            
#             # Mock user data
#             telegram_id = params.get('id', ['123456'])[0]
#             username = params.get('username', ['test_user'])[0]
#             first_name = params.get('first_name', ['Test'])[0]
            
#         except Exception as e:
#             raise serializers.ValidationError(f"Invalid initData: {str(e)}")
        
#         # Get or create user
#         user, created = User.objects.get_or_create(
#             username=f"telegram_{telegram_id}",
#             defaults={
#                 'first_name': first_name,
#                 'email': f"{telegram_id}@telegram.user"
#             }
#         )
        
#         # Update or create profile
#         profile, _ = models.UserProfile.objects.get_or_create(
#             user=user,
#             defaults={
#                 'telegram_id': telegram_id,
#                 'telegram_username': username,
#                 'telegram_data': params
#             }
#         )
        
#         if not created:
#             profile.telegram_username = username
#             profile.telegram_data = params
#             profile.save()
        
#         attrs['user'] = user
#         return attrs
    
#     def create(self, validated_data):
#         # This method shouldn't be called as we're not creating a model
#         pass
