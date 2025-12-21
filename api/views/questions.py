# api/views/questions.py
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action, authentication_classes, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.db.models import Prefetch, Q
from django.core.cache import cache
from django.utils import timezone
from collections import defaultdict
import logging

from core.authentication import TelegramAuthenticationBackend
from core.models import (
    Question, QuestionTranslation, AnswerChoice, AnswerChoiceTranslation,
    RoadSign, RoadSignTranslation, RoadSignCategory, RoadSignCategoryTranslation,
    PaymentMethod, PaymentMethodTranslation, Explanation, ExplanationTranslation,
    UserProfile, QuestionCategory
)
from core.serializers import (
    QuestionSerializer, RoadSignSerializer, RoadSignCategorySerializer,
    PaymentMethodSerializer, OptimizedQuestionSerializer, QuestionCategorySerializer
)
from core.permissions import IsTelegramAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

logger = logging.getLogger(__name__)


class QuestionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for questions with category filtering
    Returns ALL data with ALL translations - filtering is done client-side
    """
    permission_classes = [IsAuthenticated, IsTelegramAuthenticated]
    serializer_class = QuestionSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['translations__content']
    
    def get_queryset(self):
        """
        Return questions with all translations
        No filtering by premium status - return all data, client handles access
        """
        user = self.request.user
        is_pro_user = False
        
        # Check if the user is authenticated
        if user.is_authenticated:
            try:
                # Access the UserProfile's is_pro_user field
                # If the user is authenticated and is a Pro user, is_pro_user becomes True
                is_pro_user = user.profile.is_pro_user 
            except UserProfile.DoesNotExist:
                is_pro_user = False
        
        queryset = Question.objects.select_related(
            'road_sign_context', 'road_sign_context__category', 'explanation'
        ).prefetch_related(
            Prefetch('translations', queryset=QuestionTranslation.objects.all()),
            Prefetch(
                'choices',
                queryset=AnswerChoice.objects.select_related('road_sign_option').prefetch_related(
                    Prefetch('translations', queryset=AnswerChoiceTranslation.objects.all())
                )
            ),
            Prefetch('explanation__translations', queryset=ExplanationTranslation.objects.all()),
        ).order_by('difficulty', 'created_at')
        
        if not is_pro_user:
            # If the user is NOT Pro, filter the queryset to include ONLY free questions
            queryset = queryset.filter(is_premium=False)
            
        # Filter by category if provided (server-side filtering)
        category_code = self.request.query_params.get('category')
        if category_code:
            queryset = queryset.filter(
                category__code=category_code
            )
        
        # Filter by question_type if provided
        question_type = self.request.query_params.get('type')
        if question_type in ['IT', 'TI', 'TT']:
            queryset = queryset.filter(question_type=question_type)
        
        return queryset
    
    def list(self, request, *args, **kwargs):
        """
        GET /api/v1/questions/
        Returns ALL questions with ALL translations
        Client-side handles filtering based on user preferences
        """
        queryset = self.filter_queryset(self.get_queryset())
        
        # Don't filter by premium status - return everything
        # Frontend will show/hide based on user's pro status
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        
        # Add metadata about available languages
        response_data = {
            'questions': serializer.data,
            'metadata': {
                'total_count': queryset.count(),
                'available_languages': self._get_available_languages(),
                'question_types': {
                    'IT': 'Image to Text',
                    'TI': 'Text to Image',
                    'TT': 'Text to Text',
                },
                'difficulty_levels': {
                    1: 'Easy',
                    2: 'Medium', 
                    3: 'Hard'
                }
            }
        }
        
        return Response(response_data)
    
    @action(detail=False, methods=['get'])
    def metadata(self, request):
        """
        GET /api/v1/questions/metadata/
        Returns metadata about available categories, languages, etc.
        """
        # Get all categories with translations
        road_sign_categories = RoadSignCategory.objects.prefetch_related('translations').all()
        road_siign_category_serializer = RoadSignCategorySerializer(road_sign_categories, many=True)
        # categories = QuestionCategory.objects.prefetch_related('translations').all()
        # category_serializer = QuestionCategorySerializer(categories, many=True)
        
        # Get language statistics
        languages = self._get_available_languages()
        categories = self._get_available_categories()
        
        # Get question statistics
        total_questions = Question.objects.count()
        premium_count = Question.objects.filter(is_premium=True).count()
        free_count = total_questions - premium_count
        
        metadata = {
            'categories': categories,
            'road_sign_categories': road_siign_category_serializer.data,
            'languages': languages,
            'statistics': {
                'total_questions': total_questions,
                'premium_questions': premium_count,
                'free_questions': free_count,
                'question_types': {
                    'IT': Question.objects.filter(question_type='IT').count(),
                    'TI': Question.objects.filter(question_type='TI').count(),
                    'TT': Question.objects.filter(question_type='TT').count()
                },
                'difficulty_distribution': {
                    'easy': Question.objects.filter(difficulty=1).count(),
                    'medium': Question.objects.filter(difficulty=2).count(),
                    'hard': Question.objects.filter(difficulty=3).count()
                }
            },
            'quiz_config': {
                'max_questions_per_quiz': 50,
                'time_limits': {
                    'easy': 30,  # seconds
                    'medium': 45,
                    'hard': 60
                }
            }
        }
        
        return Response(metadata)
    
    def _get_available_languages(self):
        """Get list of available languages in the system"""
        # Get languages from all translation tables
        languages = set()
        
        # Check RoadSign translations
        road_sign_langs = RoadSignTranslation.objects.values_list('language', flat=True).distinct()
        languages.update(road_sign_langs)
        
        # Check Question translations
        question_langs = QuestionTranslation.objects.values_list('language', flat=True).distinct()
        languages.update(question_langs)
        
        # Sort and format
        language_names = {
            'en': 'English',
            'am': 'Amharic',
            'ti': 'Tigrigna',
            'or': 'Afan Oromo'
        }
        
        return [
            {
                'code': lang,
                'name': language_names.get(lang, lang),
                'has_road_signs': lang in road_sign_langs,
                'has_questions': lang in question_langs
            }
            for lang in sorted(languages)
        ]
    
    
    
    def _get_available_categories(self):
        """Get the number of questions for each category with translations"""
        
        # Initialize a dictionary to store the question count by category
        category_question_count = defaultdict(int)
        
        # Fetch all questions (you can add filters here if needed)
        questions = Question.objects.all()
        
        # Count how many questions belong to each category
        for question in questions:
            category_question_count[question.category] += 1
        
        # Fetch all categories and prepare data
        categories = QuestionCategory.objects.all()
        
        category_data = []
        
        for category in categories:
            # Fetch translations for each language (assuming 'en', 'am', 'or', 'ti' etc. as needed)
            translations = {}
            for translation in category.translations.all():
                translations[translation.language] = {
                    "name": translation.name,
                    "description": translation.description
                }
            
            # Add the category details including translations and question count
            category_data.append(
                {
                    "code": category.code,
                    "order": category.order,
                    "translations": translations,
                    "has_questions": category_question_count[category]
                }
            )
        
        # Return sorted categories by code
        return category_data
    


class AllDataView(APIView):
    """
    GET /api/v1/questions/all/
    Returns a complete data dump for PWA offline caching
    Includes ALL questions, road signs, categories, payment methods with ALL translations
    Pro users only
    """
    permission_classes = [IsAuthenticated, IsTelegramAuthenticated]
    
    def get(self, request):
        user = request.user
        
        # Verify pro status
        if not hasattr(user, 'profile') or not user.profile.is_pro_user:
            return Response(
                {'error': 'Premium subscription required for offline cache'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Generate cache key
        cache_token = user.profile.offline_cache_token
        cache_key = f'offline_cache_v2_{user.id}_{cache_token}'
        
        # Check cache
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.info(f"Serving cached offline data v2 for user {user.id}")
            return Response(cached_data)
        
        try:
            # Get ALL questions with ALL data
            questions = Question.objects.select_related(
                'road_sign_context', 'road_sign_context__category', 'explanation'
            ).prefetch_related(
                Prefetch('translations', queryset=QuestionTranslation.objects.all()),
                Prefetch(
                    'choices',
                    queryset=AnswerChoice.objects.select_related('road_sign_option').prefetch_related(
                        Prefetch('translations', queryset=AnswerChoiceTranslation.objects.all())
                    )
                ),
                Prefetch('explanation__translations', queryset=ExplanationTranslation.objects.all()),
            ).all()
            
            # Serialize with optimized serializer
            question_serializer = OptimizedQuestionSerializer(questions, many=True)
            
            # Get ALL road signs with translations
            road_signs = RoadSign.objects.select_related('category').prefetch_related(
                Prefetch('translations', queryset=RoadSignTranslation.objects.all())
            ).all()
            
            road_sign_data = []
            for road_sign in road_signs:
                translations = {}
                for trans in road_sign.translations.all():
                    translations[trans.language] = {
                        'name': trans.name,
                        'meaning': trans.meaning,
                        'detailed_explanation': trans.detailed_explanation
                    }
                
                road_sign_data.append({
                    'id': str(road_sign.id),
                    'code': road_sign.code,
                    'image': road_sign.image.url if road_sign.image else None,
                    'category': {
                        'id': str(road_sign.category.id) if road_sign.category else None,
                        'code': road_sign.category.code if road_sign.category else None,
                        'translations': self._get_category_translations(road_sign.category)
                    } if road_sign.category else None,
                    'translations': translations
                })
            
            # Get ALL categories with translations
            categories = RoadSignCategory.objects.prefetch_related('translations').all()
            category_data = []
            for category in categories:
                translations = {}
                for trans in category.translations.all():
                    translations[trans.language] = {
                        'name': trans.name,
                        'description': trans.description
                    }
                
                category_data.append({
                    'id': str(category.id),
                    'code': category.code,
                    'order': category.order,
                    'translations': translations
                })
            
            # Get ALL active payment methods with translations
            payment_methods = PaymentMethod.objects.filter(is_active=True).prefetch_related(
                'translations'
            ).order_by('order')
            
            payment_data = []
            for method in payment_methods:
                translations = {}
                for trans in method.translations.all():
                    translations[trans.language] = {
                        'account_details': trans.account_details,
                        'instruction': trans.instruction
                    }
                
                payment_data.append({
                    'id': str(method.id),
                    'name': method.name,
                    'code': method.code,
                    'is_active': method.is_active,
                    'order': method.order,
                    'amount': float(method.amount),
                    'translations': translations
                })
            
            # Prepare complete data dump
            offline_data = {
                'version': '2.0',
                'generated_at': timezone.now().isoformat(),
                'expires_at': (timezone.now() + timezone.timedelta(days=7)).isoformat(),
                'cache_token': str(cache_token),
                'user_id': user.id,
                'is_pro_user': True,
                
                'data': {
                    'questions': question_serializer.data,
                    'road_signs': road_sign_data,
                    'categories': category_data,
                    'payment_methods': payment_data
                },
                
                'metadata': {
                    'counts': {
                        'questions': questions.count(),
                        'road_signs': road_signs.count(),
                        'categories': categories.count(),
                        'payment_methods': payment_methods.count()
                    },
                    'available_languages': self._get_all_languages(),
                    'question_types': ['IT', 'TI', 'TT'],
                    'difficulty_levels': [1, 2, 3]
                },
                
                'client_config': {
                    'default_language': 'en',
                    'fallback_language': 'en',
                    'quiz_settings': {
                        'default_question_count': 20,
                        'max_question_count': 50,
                        'time_per_question': 30,
                        'shuffle_answers': True
                    },
                    'offline_settings': {
                        'storage_key': 'driving_exam_data',
                        'encryption_key_suffix': f'user_{user.id}',
                        'cache_duration_days': 7
                    }
                }
            }
            
            # Cache for 1 hour
            cache.set(cache_key, offline_data, 3600)
            
            logger.info(f"Generated offline cache v2 for user {user.id}")
            
            return Response(offline_data)
            
        except Exception as e:
            logger.error(f"Error generating offline cache: {str(e)}")
            return Response(
                {'error': 'Failed to generate offline cache', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _get_category_translations(self, category):
        """Get translations for a category"""
        if not category:
            return {}
        translations = {}
        for trans in category.translations.all():
            translations[trans.language] = {
                'name': trans.name,
                'description': trans.description
            }
        return translations
    
    def _get_all_languages(self):
        """Get all languages available in the system"""
        languages = set()
        
        # Collect from all translation tables
        translation_tables = [
            (RoadSignTranslation, 'language'),
            (QuestionTranslation, 'language'),
            (AnswerChoiceTranslation, 'language'),
            (ExplanationTranslation, 'language'),
            (RoadSignCategoryTranslation, 'language'),
            (PaymentMethodTranslation, 'language')
        ]
        
        for model, field in translation_tables:
            langs = model.objects.values_list(field, flat=True).distinct()
            languages.update(langs)
        
        # Language names mapping
        language_names = {
            'en': {'code': 'en', 'name': 'English', 'native': 'English'},
            'am': {'code': 'am', 'name': 'Amharic', 'native': 'አማርኛ'},
            'ti': {'code': 'ti', 'name': 'Tigrigna', 'native': 'ትግርኛ'},
            'or': {'code': 'or', 'name': 'Afan Oromo', 'native': 'Afaan Oromoo'}
        }
        
        return [
            language_names.get(lang, {'code': lang, 'name': lang, 'native': lang})
            for lang in sorted(languages)
        ]


class RefreshCacheTokenView(APIView):
    """
    POST /api/v1/questions/all/refresh_token/
    Generate new cache token for offline data
    """
    permission_classes = [IsAuthenticated, IsTelegramAuthenticated]
    
    def post(self, request):
        """
        Generate new cache token for user
        """
        user = request.user
        if not hasattr(user, 'profile'):
            return Response(
                {'error': 'User profile not found'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            profile = user.profile
            
            # Generate new token
            new_token = profile.generate_new_cache_token()
            
            # Clear old cache entries for this user
            cache_keys_to_delete = [
                f'offline_cache_v2_{user.id}_*',
                f'offline_cache_{user.id}_*',
                f'free_questions_user_{user.id}',
                f'all_questions_user_{user.id}'
            ]
            
            # Try to delete pattern, fall back to individual deletion
            for key_pattern in cache_keys_to_delete:
                try:
                    # Try pattern deletion if supported
                    cache.delete_pattern(key_pattern)
                except AttributeError:
                    # Pattern deletion not supported, delete common keys
                    if 'offline_cache_v2_' in key_pattern:
                        cache.delete(f'offline_cache_v2_{user.id}_{profile.offline_cache_token}')
            
            logger.info(f"Cache token refreshed for user {user.id}")
            
            return Response({
                'success': True,
                'new_cache_token': str(new_token),
                'message': 'Cache token refreshed successfully',
                'old_token_invalidated': True,
                'cache_cleared': True,
                'timestamp': timezone.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error refreshing cache token for user {user.id}: {str(e)}")
            return Response({
                'error': 'Failed to refresh cache token',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)











































# from rest_framework import viewsets, status
# from rest_framework.decorators import action, permission_classes
# from rest_framework.response import Response
# from rest_framework.permissions import AllowAny, IsAuthenticated
# from django.db.models import Prefetch
# from core.models import Question, QuestionTranslation, AnswerChoice, AnswerChoiceTranslation
# from core.serializers import QuestionSerializer, OptimizedQuestionSerializer
# from core.permissions import IsProUser
# from django.core.cache import cache
# import logging

# logger = logging.getLogger(__name__)


# class QuestionViewSet(viewsets.GenericViewSet):
#     queryset = Question.objects.all()
    
#     def get_serializer_class(self):
#         # Use optimized serializer for free/all endpoints
#         if self.action in ['free', 'all', 'premium']:
#             return OptimizedQuestionSerializer
#         return QuestionSerializer
    
#     def get_queryset(self):
#         # Optimize queryset with prefetching
#         return Question.objects.select_related(
#             'road_sign', 'explanation'
#         ).prefetch_related(
#             Prefetch('translations', queryset=QuestionTranslation.objects.all()),
#             Prefetch('choices', queryset=AnswerChoice.objects.all().prefetch_related(
#                 Prefetch('translations', queryset=AnswerChoiceTranslation.objects.all())
#             )),
#             'explanation__translations'
#         ).order_by('-created_at')
    
#     @action(detail=False, methods=['get'], permission_classes=[AllowAny])
#     def free(self, request):
#         """
#         Get all free questions for unauthenticated or authenticated users
#         Returns optimized JSON structure for frontend
#         """
#         cache_key = 'free_questions'
#         language = request.query_params.get('lang', 'en')
        
#         # Cache per language
#         if language != 'en':
#             cache_key = f'{cache_key}_{language}'
        
#         questions = cache.get(cache_key)
        
#         if not questions:
#             queryset = self.get_queryset().filter(is_premium=False)
#             serializer = self.get_serializer(queryset, many=True)
#             questions = serializer.data
            
        
#         return Response({
#             'questions': questions,
#             'count': len(questions),
#             'language': language,
#             'is_pro_user': request.user.is_authenticated and 
#                           hasattr(request.user, 'profile') and 
#                           request.user.profile.is_pro_user
#         })
    
#     @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated, IsProUser])
#     def all(self, request):
#         """
#         Get all questions (free and premium) for pro users only
#         Returns optimized JSON structure for frontend
#         """
#         if not hasattr(request.user, 'profile') or not request.user.profile.is_pro_user:
#             return Response(
#                 {'error': 'Premium subscription required'},
#                 status=status.HTTP_403_FORBIDDEN
#             )
        
#         cache_key = f'all_questions_user_{request.user.id}'
#         language = request.query_params.get('lang', 'en')
        
#         if language != 'en':
#             cache_key = f'{cache_key}_{language}'
        
#         questions = cache.get(cache_key)
        

        
#         return Response({
#             'questions': questions,
#             'count': len(questions),
#             'language': language,
#             'is_pro_user': True
#         })
    
#     @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
#     def premium(self, request):
#         """
#         Get premium questions for authenticated pro users
#         """
#         if not hasattr(request.user, 'profile') or not request.user.profile.is_pro_user:
#             return Response(
#                 {'error': 'Premium subscription required'},
#                 status=status.HTTP_403_FORBIDDEN
#             )
        
#         language = request.query_params.get('lang', 'en')
#         premium_questions = self.get_queryset().filter(is_premium=True)
#         serializer = self.get_serializer(premium_questions, many=True)
        
#         return Response({
#             'questions': serializer.data,
#             'count': len(serializer.data),
#             'language': language,
#             'is_pro_user': True
#         })
    
#     @action(detail=False, methods=['get'], permission_classes=[AllowAny])  
#     def count(self, request):
#         """
#         Get count of free and total questions
#         """
#         free_count = self.queryset.filter(is_premium=False).count()
#         premium_count = self.queryset.filter(is_premium=True).count()
        
#         return Response({
#             'free': free_count,
#             'premium': premium_count,
#             'total': free_count + premium_count
#         })
    
#     @action(detail=True, methods=['get'], permission_classes=[AllowAny])  
#     def detail(self, request, pk=None):
#         """
#         Get detailed view of a single question
#         """
#         try:
#             question = self.get_queryset().get(pk=pk)
            
#             # Check premium access
#             if question.is_premium and not (
#                 request.user.is_authenticated and 
#                 hasattr(request.user, 'profile') and 
#                 request.user.profile.is_pro_user
#             ):
#                 return Response(
#                     {'error': 'Premium subscription required to access this question'},
#                     status=status.HTTP_403_FORBIDDEN
#                 )
            
#             serializer = QuestionSerializer(question, context={'request': request})
#             return Response(serializer.data)
            
#         except Question.DoesNotExist:
#             return Response(
#                 {'error': 'Question not found'},
#                 status=status.HTTP_404_NOT_FOUND
#             )
            
            
            
            