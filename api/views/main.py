# api/views/main.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status
from django.conf import settings
from django.db.models import Count, Q
from django.utils import timezone
from django.core.cache import cache
from collections import defaultdict

from core.models import (
    RoadSignCategory, RoadSign, Question, QuestionTranslation,
    RoadSignTranslation, PaymentMethod, UserProfile,
    Article, ArticleCategory, ExamSession, RoadSignCategoryTranslation,
    QuestionCategory, BundleDefinition,
)
from core.serializers import (
    RoadSignCategorySerializer, QuestionSerializer,
    PaymentMethodSerializer,
    ArticleCategorySerializer, ArticleSerializer,
    QuestionCategorySerializer, BundleDefinitionSerializer,
)
from core.authentication import TelegramAuthenticationBackend
import logging

logger = logging.getLogger(__name__)


class LandingView(APIView):
    """
    GET /api/v1/home/
    Enhanced landing/home API - returns all data needed for initial app load.
    Includes metadata, subscription plans, statistics, payment methods, and ALL FREE questions.
    Accessible to everyone (no auth required). Pro users identified for status only.
    """
    authentication_classes = [TelegramAuthenticationBackend]
    permission_classes = [AllowAny]

    def get(self, request):
        # Generate cache key based on language and user status
        language = request.query_params.get('lang', 'en')
        is_authenticated = request.user.is_authenticated
        is_pro = False
        user_id = None
        
        if is_authenticated:
            try:
                is_pro = request.user.profile.is_subscription_active
                user_id = request.user.id
            except (AttributeError, UserProfile.DoesNotExist):
                pass
        
        cache_key = f'landing_{language}_{user_id}_{is_pro}'
        
        # Try to get from cache
        cached_data = cache.get(cache_key, None)
        if cached_data:
            logger.info(f"Serving cached landing data for user {user_id}")
            return Response(cached_data)
        
        try:
            # Get user status info
            user_status = self._get_user_status(request.user)

            # Get available bundles (replaces subscription plans)
            bundles = BundleDefinition.objects.filter(
                is_active=True
            ).order_by('order', 'price_etb')
            
            bundle_serializer = BundleDefinitionSerializer(
                bundles,
                many=True,
                context={'request': request}
            )
            
            # Categories with translations
            categories = QuestionCategory.objects.prefetch_related('translations').all()
            category_serializer = QuestionCategorySerializer(
                categories,
                many=True,
                context={'request': request}
            )
            # Categories with translations
            road_sign_categories = RoadSignCategory.objects.prefetch_related('translations').all()
            sub_category_serializer = RoadSignCategorySerializer(
                road_sign_categories,
                many=True,
                context={'request': request}
            )
            
            
            # Available languages
            available_languages = self._get_available_languages()
            available_categories = self._get_available_categories()
            
            # Payment methods / paywall info
            payment_methods = PaymentMethod.objects.filter(
                is_active=True
            ).prefetch_related('translations').order_by('order')
            
            payment_serializer = PaymentMethodSerializer(
                payment_methods, 
                many=True, 
                context={'request': request}
            )
            
            # Free articles (preview)
            free_articles = Article.objects.filter(
                is_premium=False,
                category__is_active=True
            ).select_related('category').order_by('-views', '-created_at')[:5]
            
            article_serializer = ArticleSerializer(
                free_articles,
                many=True,
                context={'request': request}
            )
            
            # Article categories
            article_categories = ArticleCategory.objects.filter(
                is_active=True
            ).order_by('order')[:5]
            
            article_category_serializer = ArticleCategorySerializer(
                article_categories,
                many=True,
                context={'request': request}
            )
            
            # Featured free questions for road sign quiz
            featured_questions = self._get_featured_free_questions()
            
            # ALL FREE questions (full data, same structure as QuestionSerializer)
            free_questions_qs = Question.objects.select_related(
                'road_sign_context', 'road_sign_context__category', 'explanation'
            ).prefetch_related(
                'translations',
                'choices__translations',
                'choices__road_sign_option',
                'explanation__translations',
            ).filter(is_premium=False).order_by('difficulty', 'created_at')[:50]  # Limit to 50 for landing
            
            question_serializer = QuestionSerializer(
                free_questions_qs,
                many=True,
                context={'request': request}  
            )
            
            # User testimonials/achievements (mock data - can be replaced with real data)
            achievements = self._get_achievements_stats()
            
            # Exam simulation preview
            exam_preview = {
                'total_questions': 50,
                'time_limit': 3600,  # 60 minutes
                'passing_score': 80,
                'categories_count': categories.count(),
                'question_types': ['IT', 'TI']
            }
            
            # AI features preview
            ai_features = {
                'available': True,
                'description': 'Ask questions about Ethiopian driving laws',
                'example_questions': [
                    'What is the speed limit in Addis Ababa?',
                    'How to handle roundabouts in Ethiopia?',
                    'What documents do I need for driving license?'
                ]
            }
            
            # Build response
            response_data = {
                'metadata': {
                    'available_languages': available_languages,
                    'categories': available_categories,
                    'road_sign_categories': sub_category_serializer.data,
                    'article_categories': article_category_serializer.data,
                    'quiz_config': {
                        'max_questions_per_quiz': 50,
                        'time_limits': {'easy': 30, 'medium': 45, 'hard': 60},
                        'exam_time_limit': 3600,
                        'passing_score': 74
                    },
                    'miniapp_link': settings.MINIAPP_LINK,
                    'signin_qr_url': settings.MINIAPP_LINK,
                    'version': '1.0',
                    'last_updated': timezone.now().isoformat()
                },
                'bundles': {  # Changed from 'subscription'
                    'available_bundles': bundle_serializer.data,
                    'recommended_bundle': self._get_recommended_bundle(bundles),
                    'features_comparison': self._get_features_comparison(),
                    'paywall': {
                        'payment_methods': payment_serializer.data,
                        'description': 'Purchase a bundle to access premium features',
                    }
                },
                'content': {
                    'free_questions': question_serializer.data,
                    'featured_questions': featured_questions,
                    'free_articles': article_serializer.data,
                    'articles_count': Article.objects.filter(is_premium=False).count(),
                    'premium_articles_count': Article.objects.filter(is_premium=True).count(),
                },
                'features': {
                    'exam_simulation': exam_preview,
                    'ai_chat': ai_features,
                    'offline_access': True,
                    'progress_tracking': True,
                    'detailed_explanations': True,
                },
                'achievements': achievements,
                'user': user_status,
                'call_to_action': {
                    'free_trial': {
                        'title': 'Try Free Road Sign Quiz',
                        'description': '10 questions to test your knowledge',
                        'action': 'start_free_quiz',
                        'icon': '🚦'
                    },
                    'upgrade': {
                        'title': 'Become Pro Driver',
                        'description': 'Access full 700+ question bank and exam mode',
                        'action': 'view_plans',
                        'icon': '⭐'
                    },
                    'demo_exam': {
                        'title': 'Exam Simulation Demo',
                        'description': 'Experience the real exam format',
                        'action': 'try_demo',
                        'icon': '📝'
                    }
                }
            }
            
            # Cache for 1 hour
            cache.set(cache_key, response_data, 3600)
            
            return Response(response_data)
            
        except Exception as e:
            logger.error(f"Error generating landing data: {str(e)}")
            return Response(
                {'error': 'Failed to load landing data', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _get_user_status(self, user):
        """Get user status with bundle info"""
        if not user or not user.is_authenticated:
            return {
                'is_authenticated': False,
                'has_active_bundle': False,
                'message': 'Sign in to access your bundle'
            }
        
        try:
            profile = user.profile
            has_active_bundle = profile.has_active_bundle
            
            user_data = {
                'is_authenticated': True,
                'has_active_bundle': has_active_bundle,
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'accuracy': round(profile.accuracy, 2),
                'total_exam_attempts': profile.total_exam_attempts,
                'highest_exam_score': profile.highest_exam_score,
                'offline_cache_enabled': has_active_bundle,
            }
            
            if has_active_bundle and profile.active_bundle:
                bundle = profile.active_bundle
                user_data['current_bundle'] = {
                    'name': bundle.bundle_definition.name,
                    'remaining_resources': bundle.get_remaining_resources(),
                    'expires_at': bundle.expiry_date.isoformat() if bundle.expiry_date else None,
                }
                user_data['days_remaining'] = profile.days_remaining
            
            # Get recent exam attempts
            recent_exams = ExamSession.objects.filter(
                user=user
            ).order_by('-start_time')[:3]
            
            user_data['recent_exams'] = [
                {
                    'id': str(exam.id),
                    'score': exam.score,
                    'passed': exam.passed,
                    'date': exam.start_time.strftime('%Y-%m-%d'),
                    'time_taken': exam.time_taken
                }
                for exam in recent_exams
            ]
            
            return user_data
            
        except UserProfile.DoesNotExist:
            return {
                'is_authenticated': True,
                'has_active_bundle': False,
                'username': user.username,
                'message': 'Complete your profile'
            }
    
    # def _get_system_statistics(self):
    #     """Get system-wide statistics"""
    #     total_questions = Question.objects.count()
    #     free_questions_count = Question.objects.filter(is_premium=False).count()
    #     premium_questions_count = total_questions - free_questions_count
    #     total_road_signs = RoadSign.objects.count()
        
    #     question_types_count = {
    #         'IT': Question.objects.filter(question_type='IT').count(),
    #         'TI': Question.objects.filter(question_type='TI').count(),
    #     }
        
    #     difficulty_distribution = {
    #         'easy': Question.objects.filter(difficulty=1).count(),
    #         'medium': Question.objects.filter(difficulty=2).count(),
    #         'hard': Question.objects.filter(difficulty=3).count(),
    #     }
        
    #     # User statistics
    #     total_users = UserProfile.objects.count()
    #     # pro_users = UserProfile.objects.filter(is_pro_user=True).count()
        
    #     # Exam statistics
    #     total_exams = ExamSession.objects.filter(
    #         status=ExamSession.ExamStatus.COMPLETED
    #     ).count()
        
    #     passed_exams = ExamSession.objects.filter(
    #         status=ExamSession.ExamStatus.COMPLETED,
    #         passed=True
    #     ).count()
        
    #     pass_rate = (passed_exams / total_exams * 100) if total_exams > 0 else 0
        
    #     return {
    #         'questions': {
    #             'total': total_questions,
    #             'free': free_questions_count,
    #             'premium': premium_questions_count,
    #             'road_signs': total_road_signs,
    #             'types': question_types_count,
    #             'difficulty': difficulty_distribution
    #         },
    #         'users': {
    #             'total': total_users,
    #             'pro_users': pro_users,
    #             'pro_percentage': round((pro_users / total_users * 100), 2) if total_users > 0 else 0
    #         },
    #         'exams': {
    #             'total_attempts': total_exams,
    #             'passed': passed_exams,
    #             'pass_rate': round(pass_rate, 2),
    #             'average_score': self._get_average_exam_score()
    #         },
    #         'content': {
    #             'articles': Article.objects.count(),
    #             'categories': RoadSignCategory.objects.count(),
    #             'article_categories': ArticleCategory.objects.count()
    #         }
    #     }
    
    def _get_average_exam_score(self):
        """Calculate average exam score"""
        from django.db.models import Avg
        result = ExamSession.objects.filter(
            status=ExamSession.ExamStatus.COMPLETED
        ).aggregate(avg_score=Avg('score'))
        
        return round(result['avg_score'] or 0, 2)
    
    def _get_available_languages(self):
        """Get list of available languages in the system"""
        languages = set()
        
        # Check from all relevant translation tables
        translation_tables = [
            (RoadSignTranslation, 'language'),
            (QuestionTranslation, 'language'),
            (RoadSignCategoryTranslation, 'language'),
        ]
        
        for model, field in translation_tables:
            try:
                langs = model.objects.values_list(field, flat=True).distinct()
                languages.update(langs)
            except:
                continue
        
        language_names = {
            'en': {'code': 'en', 'name': 'English', 'native': 'English'},
            'am': {'code': 'am', 'name': 'Amharic', 'native': 'አማርኛ'},
            'ti': {'code': 'ti', 'name': 'Tigrigna', 'native': 'ትግርኛ'},
            'or': {'code': 'or', 'name': 'Afan Oromo', 'native': 'Afaan Oromoo'}
        }
        
        # Return sorted by code
        return [
            language_names.get(lang, {'code': lang, 'name': lang, 'native': lang})
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
                    "id": str(category.id),
                    "code": category.code,
                    "order": category.order,
                    "translations": translations,
                    "question_count": category_question_count[category]
                }
            )
        
        # Return sorted categories by code
        return sorted(category_data, key=lambda x: x['code'])
    
    def _get_featured_free_questions(self):
        """Get featured free questions for landing page quiz"""
        try:
            # Get questions from different categories and difficulties
            featured_qs = Question.objects.filter(
                is_premium=False,
                road_sign_context__category__isnull=False
            ).select_related(
                'road_sign_context', 'road_sign_context__category'
            ).order_by('?')[:10]  # Random 10 questions
            
            featured_data = []
            for question in featured_qs:
                # Get basic info for preview
                translation = question.translations.filter(language='en').first()
                if translation:
                    featured_data.append({
                        'id': str(question.id),
                        'question_type': question.question_type,
                        'difficulty': question.difficulty,
                        'content_preview': translation.content[:100] + '...' if len(translation.content) > 100 else translation.content,
                        'category': question.road_sign_context.category.code if question.road_sign_context.category else None,
                        'has_explanation': hasattr(question, 'explanation')
                    })
            
            return featured_data
            
        except Exception as e:
            logger.error(f"Error getting featured questions: {str(e)}")
            return []
    
    def _get_recommended_plan(self, subscription_plans):
        """Get the recommended subscription plan"""
        try:
            basic_plan = subscription_plans.filter(plan_type='3months').first()
            if basic_plan:
                return {
                    'id': str(basic_plan.id),
                    'name': basic_plan.name,
                    'price_etb': float(basic_plan.price_etb),
                    'recommended_reason': 'Best value - Basic Booster'
                }
                
            # For now, recommend the lifetime plan if exists, else the longest duration
            lifetime_plan = subscription_plans.filter(plan_type='lifetime').first()
            if lifetime_plan:
                return {
                    'id': str(lifetime_plan.id),
                    'name': lifetime_plan.name,
                    'price_etb': float(lifetime_plan.price_etb),
                    'recommended_reason': 'Best value - One time payment'
                }
            
            # Otherwise, recommend yearly plan
            yearly_plan = subscription_plans.filter(plan_type='yearly').first()
            if yearly_plan:
                return {
                    'id': str(yearly_plan.id),
                    'name': yearly_plan.name,
                    'price_etb': float(yearly_plan.price_etb),
                    'recommended_reason': 'Great value - Full year access'
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting recommended plan: {str(e)}")
            return None
    
    def _get_features_comparison(self):
        """Get features comparison between free and pro"""
        return {
            'free': {
                'road_sign_quiz': True,
                'limited_questions': True,
                'question_limit': 10,
                'basic_progress': True,
                'exam_simulation': False,
                'ai_chat': False,
                'offline_access': False,
                'detailed_explanations': False,
                'all_languages': False,
                'premium_articles': False,
                'search_function': False
            },
            'pro': {
                'road_sign_quiz': True,
                'limited_questions': False,
                'question_limit': 'Unlimited',
                'basic_progress': True,
                'exam_simulation': True,
                'ai_chat': True,
                'offline_access': True,
                'detailed_explanations': True,
                'all_languages': True,
                'premium_articles': True,
                'search_function': True,
                'exam_statistics': True,
                'custom_quizzes': True,
                'priority_support': True
            }
        }
    
    def _get_achievements_stats(self):
        """Get achievement statistics (mock data - can be replaced with real achievements)"""
        try:
            # Top users by score
            top_users = UserProfile.objects.filter(
                highest_exam_score__gt=0
            ).order_by('-highest_exam_score')[:5]
            
            top_users_data = []
            for profile in top_users:
                top_users_data.append({
                    'username': profile.user.username,
                    'score': profile.highest_exam_score,
                    'accuracy': round(profile.accuracy, 2)
                })
            
            # Recent achievements
            recent_achievements = [
                {
                    'user': 'Abebe',
                    'achievement': 'Scored 100% on Exam',
                    'date': '2024-01-15',
                    'icon': '🏆'
                },
                {
                    'user': 'Meron',
                    'achievement': 'Completed 500 Questions',
                    'date': '2024-01-14',
                    'icon': '✅'
                },
                {
                    'user': 'Tesfaye',
                    'achievement': '10 Day Streak',
                    'date': '2024-01-13',
                    'icon': '🔥'
                }
            ]
            
            # Community stats
            total_correct_answers = UserProfile.objects.aggregate(
                total=Count('correct_answers')
            )['total'] or 0
            
            total_questions_attempted = UserProfile.objects.aggregate(
                total=Count('total_practice_questions')
            )['total'] or 0
            
            return {
                'top_users': top_users_data,
                'recent_achievements': recent_achievements,
                'community_stats': {
                    'total_correct_answers': total_correct_answers,
                    'total_questions_attempted': total_questions_attempted,
                    'average_accuracy': self._get_average_user_accuracy()
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting achievements: {str(e)}")
            return {
                'top_users': [],
                'recent_achievements': [],
                'community_stats': {
                    'total_correct_answers': 0,
                    'total_questions_attempted': 0,
                    'average_accuracy': 0
                }
            }
    
    def _get_average_user_accuracy(self):
        """Calculate average user accuracy"""
        from django.db.models import Avg
        
        result = UserProfile.objects.filter(
            total_practice_questions__gt=0
        ).aggregate(
            avg_accuracy=Avg('correct_answers') * 100.0 / Avg('total_practice_questions')
        )
        
        return round(result['avg_accuracy'] or 0, 2)

    def _get_recommended_bundle(self, bundles):
        """Get recommended bundle (e.g., best value)"""
        try:
            # Example: Recommend the bundle with most features per ETB
            if bundles.exists():
                # Simple logic: recommend the first active bundle
                recommended = bundles.first()
                return {
                    'id': str(recommended.id),
                    'name': recommended.name,
                    'price_etb': float(recommended.price_etb),
                    'recommended_reason': 'Popular choice with balanced features'
                }
            return None
        except Exception as e:
            logger.error(f"Error getting recommended bundle: {str(e)}")
            return None

# class FreeRoadSignQuizView(APIView):
#     """
#     GET /api/v1/main/free-quiz/
#     Returns 10 random free road sign questions for non-authenticated users
#     """
#     authentication_classes = [TelegramAuthenticationBackend]
#     permission_classes = [AllowAny]
    
#     def get(self, request):
#         try:
#             # Get 10 random free questions
#             free_questions = Question.objects.filter(
#                 is_premium=False
#             ).select_related(
#                 'road_sign_context', 'road_sign_context__category'
#             ).prefetch_related(
#                 'translations',
#                 'choices__translations',
#                 'choices__road_sign_option',
#             ).order_by('?')[:10]  # Random 10 questions
            
#             question_serializer = QuestionSerializer(
#                 free_questions,
#                 many=True,
#                 context={'request': request}
#             )
            
#             return Response({
#                 'quiz': {
#                     'title': 'Free Road Sign Quiz',
#                     'description': 'Test your knowledge with 10 random road sign questions',
#                     'question_count': len(free_questions),
#                     'time_limit': 300,  # 5 minutes
#                     'passing_score': 60,
#                     'is_pro_required': False
#                 },
#                 'questions': question_serializer.data,
#                 'instructions': {
#                     '1': 'Answer all 10 questions',
#                     '2': 'You have 5 minutes to complete',
#                     '3': 'Score 60% or higher to pass',
#                     '4': 'Get detailed explanations after quiz (Pro feature)'
#                 },
#                 'upgrade_prompt': {
#                     'show_after_quiz': True,
#                     'message': 'Unlock full question bank and detailed explanations by upgrading to Pro!',
#                     'cta_text': 'View Pro Plans'
#                 }
#             })
            
#         except Exception as e:
#             logger.error(f"Error generating free quiz: {str(e)}")
#             return Response(
#                 {'error': 'Failed to generate quiz', 'detail': str(e)},
#                 status=status.HTTP_500_INTERNAL_SERVER_ERROR
#             )


# class ExamDemoView(APIView):
#     """
#     GET /api/v1/main/exam-demo/
#     Returns demo exam with 5 questions (no authentication required)
#     """
#     authentication_classes = [TelegramAuthenticationBackend]
#     permission_classes = [AllowAny]
    
#     def get(self, request):
#         try:
#             # Get 5 demo questions (mix of types and difficulties)
#             demo_questions = Question.objects.filter(
#                 is_premium=False,
#                 difficulty__in=[1, 2]  # Easy and medium only for demo
#             ).select_related(
#                 'road_sign_context', 'road_sign_context__category'
#             ).prefetch_related(
#                 'translations',
#                 'choices__translations',
#                 'choices__road_sign_option',
#             ).order_by('?')[:5]  # Random 5 questions
            
#             question_serializer = QuestionSerializer(
#                 demo_questions,
#                 many=True,
#                 context={'request': request}
#             )
            
#             return Response({
#                 'demo': {
#                     'title': 'Exam Simulation Demo',
#                     'description': 'Experience the real Ethiopian driving exam format',
#                     'question_count': len(demo_questions),
#                     'time_limit': 300,  # 5 minutes for demo
#                     'is_full_exam': False,
#                     'note': 'Full exam has 50 questions and 60 minute time limit'
#                 },
#                 'questions': question_serializer.data,
#                 'features_preview': {
#                     'timer': 'Real-time countdown timer',
#                     'progress_bar': 'Visual question progress',
#                     'navigation': 'Skip and review questions',
#                     'results': 'Immediate scoring and feedback',
#                     'explanations': 'Detailed explanations (Pro feature)'
#                 },
#                 'upgrade_cta': {
#                     'title': 'Ready for the Real Exam?',
#                     'description': 'Upgrade to Pro for full 50-question exam simulation with timer and detailed results',
#                     'features': [
#                         'Full 50-question exams',
#                         '30 minute time limit',
#                         'Detailed explanations',
#                         'Performance analytics',
#                         'Unlimited attempts'
#                     ]
#                 }
#             })
            
#         except Exception as e:
#             logger.error(f"Error generating exam demo: {str(e)}")
#             return Response(
#                 {'error': 'Failed to generate demo', 'detail': str(e)},
#                 status=status.HTTP_500_INTERNAL_SERVER_ERROR
#             )


# class QuickStatsView(APIView):
#     """
#     GET /api/v1/main/quick-stats/
#     Returns quick statistics for dashboard display
#     """
#     authentication_classes = [TelegramAuthenticationBackend]
#     permission_classes = [AllowAny]
    
#     def get(self, request):
#         try:
#             stats = {
#                 'total_questions': Question.objects.count(),
#                 'free_questions': Question.objects.filter(is_premium=False).count(),
#                 'road_signs': RoadSign.objects.count(),
#                 'categories': RoadSignCategory.objects.count(),
#                 'active_users': UserProfile.objects.filter(
#                     last_active__gte=timezone.now() - timezone.timedelta(days=7)
#                 ).count(),
#                 'exams_today': ExamSession.objects.filter(
#                     start_time__date=timezone.now().date()
#                 ).count(),
#             }
            
#             return Response({
#                 'stats': stats,
#                 'updated_at': timezone.now().isoformat(),
#                 'cache_duration': 300  # 5 minutes
#             })
            
#         except Exception as e:
#             logger.error(f"Error getting quick stats: {str(e)}")
#             return Response(
#                 {'error': 'Failed to get statistics'},
#                 status=status.HTTP_500_INTERNAL_SERVER_ERROR
#             )


# class AdminStatsView(APIView):
#     """
#     GET /api/v1/main/admin-stats/
#     Admin statistics for Telegram bot admin panel
#     Requires admin permissions
#     """
#     authentication_classes = [TelegramAuthenticationBackend]
#     permission_classes = [AllowAny]  # In production, use IsAdminUser
    
#     def get(self, request):
#         try:
#             # User growth (last 30 days)
#             thirty_days_ago = timezone.now() - timezone.timedelta(days=30)
#             new_users = UserProfile.objects.filter(
#                 created_at__gte=thirty_days_ago
#             ).count()
            
#             # Revenue stats (mock - integrate with payment system)
#             active_subscriptions = UserSubscription.objects.filter(
#                 is_active=True,
#                 payment_status='completed'
#             ).count()
            
#             # Today's activity
#             today = timezone.now().date()
#             exams_today = ExamSession.objects.filter(
#                 start_time__date=today
#             ).count()
            
#             questions_answered_today = ExamSession.objects.filter(
#                 start_time__date=today
#             ).aggregate(
#                 total_questions=Count('examquestion')
#             )['total_questions'] or 0
            
#             # Most popular categories
#             popular_categories = RoadSignCategory.objects.annotate(
#                 question_count=Count('road_signs__questions')
#             ).order_by('-question_count')[:5]
            
#             popular_categories_data = [
#                 {
#                     'category': cat.code,
#                     'question_count': cat.question_count,
#                     'translation': cat.translations.filter(language='en').first().name if cat.translations.exists() else cat.code
#                 }
#                 for cat in popular_categories
#             ]
            
#             # System health
#             from django.db import connection
#             with connection.cursor() as cursor:
#                 cursor.execute("SELECT 1")
#                 db_status = cursor.fetchone()[0] == 1
            
#             return Response({
#                 'user_stats': {
#                     'total_users': UserProfile.objects.count(),
#                     'new_users_last_30_days': new_users,
#                     'pro_users': UserProfile.objects.filter(is_pro_user=True).count(),
#                     'active_users_today': UserProfile.objects.filter(
#                         last_active__date=today
#                     ).count()
#                 },
#                 'revenue_stats': {
#                     'active_subscriptions': active_subscriptions,
#                     'total_revenue': active_subscriptions * 150,  # Mock calculation
#                     'conversion_rate': '2.5%'  # Mock
#                 },
#                 'activity_stats': {
#                     'exams_today': exams_today,
#                     'questions_answered_today': questions_answered_today,
#                     'average_exam_score': self._get_average_exam_score(),
#                     'pass_rate_today': self._get_today_pass_rate()
#                 },
#                 'content_stats': {
#                     'popular_categories': popular_categories_data,
#                     'most_difficult_questions': self._get_most_difficult_questions(),
#                     'most_viewed_articles': self._get_most_viewed_articles()
#                 },
#                 'system_health': {
#                     'database': 'OK' if db_status else 'ERROR',
#                     'cache': 'OK',
#                     'api_response_time': '45ms',  # Mock
#                     'last_backup': (timezone.now() - timezone.timedelta(hours=6)).isoformat()
#                 },
#                 'notifications': [
#                     {
#                         'type': 'info',
#                         'message': f'{new_users} new users in last 30 days',
#                         'priority': 'low'
#                     },
#                     {
#                         'type': 'warning',
#                         'message': f'{5} questions have no translations',
#                         'priority': 'medium'
#                     }
#                 ]
#             })
            
#         except Exception as e:
#             logger.error(f"Error getting admin stats: {str(e)}")
#             return Response(
#                 {'error': 'Failed to get admin statistics', 'detail': str(e)},
#                 status=status.HTTP_500_INTERNAL_SERVER_ERROR
#             )
    
#     def _get_average_exam_score(self):
#         """Calculate average exam score"""
#         from django.db.models import Avg
#         result = ExamSession.objects.filter(
#             status=ExamSession.ExamStatus.COMPLETED
#         ).aggregate(avg_score=Avg('score'))
        
#         return round(result['avg_score'] or 0, 2)
    
#     def _get_today_pass_rate(self):
#         """Calculate today's exam pass rate"""
#         today = timezone.now().date()
#         today_exams = ExamSession.objects.filter(
#             start_time__date=today,
#             status=ExamSession.ExamStatus.COMPLETED
#         )
        
#         total = today_exams.count()
#         passed = today_exams.filter(passed=True).count()
        
#         return round((passed / total * 100) if total > 0 else 0, 2)
    
#     def _get_most_difficult_questions(self):
#         """Get most frequently missed questions"""
#         from django.db.models import Count
        
#         difficult_questions = Question.objects.annotate(
#             incorrect_count=Count(
#                 'user_progress',
#                 filter=Q(user_progress__is_correct=False)
#             )
#         ).filter(incorrect_count__gt=0).order_by('-incorrect_count')[:5]
        
#         return [
#             {
#                 'id': str(q.id),
#                 'incorrect_count': q.incorrect_count,
#                 'difficulty': q.get_difficulty_display(),
#                 'category': q.road_sign_context.category.code if q.road_sign_context.category else 'N/A'
#             }
#             for q in difficult_questions
#         ]
    
#     def _get_most_viewed_articles(self):
#         """Get most viewed articles"""
#         popular_articles = Article.objects.order_by('-views')[:5]
        
#         return [
#             {
#                 'title': article.title,
#                 'views': article.views,
#                 'category': article.category.name if article.category else 'Uncategorized',
#                 'is_premium': article.is_premium
#             }
#             for article in popular_articles
#         ]






















































# # api/views/main.py
# from rest_framework.views import APIView
# from rest_framework.response import Response
# from rest_framework.permissions import AllowAny
# from django.conf import settings
# from django.db.models import Count
# from core.models import (
#     RoadSignCategory, RoadSign, Question, QuestionTranslation,
#     RoadSignTranslation, PaymentMethod, UserProfile
# )
# from core.serializers import (
#     RoadSignCategorySerializer, QuestionSerializer,
#     PaymentMethodSerializer
# )
# from core.authentication import TelegramAuthenticationBackend


# class LandingView(APIView):
#     """
#     GET /api/v1/main/
#     Main landing/home API - returns all data needed for initial app load.
#     Includes metadata, categories, statistics, payment methods, and ALL FREE questions.
#     Accessible to everyone (no auth required). Pro users identified for status only.
#     """
#     authentication_classes = [TelegramAuthenticationBackend]
#     permission_classes = [AllowAny]

#     def get(self, request):
#         # Check if user is pro (for status info only - free questions served to all)
#         is_pro_user = False
#         if request.user.is_authenticated:
#             try:
#                 is_pro_user = request.user.profile.is_pro_user
#             except (AttributeError, UserProfile.DoesNotExist):
#                 pass

#         # Categories with translations
#         categories = RoadSignCategory.objects.prefetch_related('translations').all()
#         category_serializer = RoadSignCategorySerializer(
#             categories,
#             many=True,
#             context={'request': request}
#         )

#         # Statistics
#         total_questions = Question.objects.count()
#         free_questions_count = Question.objects.filter(is_premium=False).count()
#         premium_questions_count = total_questions - free_questions_count
#         total_road_signs = RoadSign.objects.count()

#         question_types_count = {
#             'IT': Question.objects.filter(question_type='IT').count(),
#             'TI': Question.objects.filter(question_type='TI').count(),
#         }

#         difficulty_distribution = {
#             'easy': Question.objects.filter(difficulty=1).count(),
#             'medium': Question.objects.filter(difficulty=2).count(),
#             'hard': Question.objects.filter(difficulty=3).count(),
#         }

#         # Available languages (from translations)
#         languages = set()
#         for model in [RoadSignTranslation, QuestionTranslation]:
#             languages.update(model.objects.values_list('language', flat=True).distinct())

#         language_names = {
#             'en': 'English',
#             'am': 'Amharic',
#             'ti': 'Tigrigna',
#             'or': 'Afan Oromo',
#         }

#         # Sort language codes and build list
#         available_languages = [
#             {'code': lang, 'name': language_names.get(lang, lang.title())}
#             for lang in sorted(languages)
#         ]

#         # Payment methods / paywall info
#         payment_methods = PaymentMethod.objects.filter(is_active=True).prefetch_related('translations').order_by('order')
#         payment_serializer = PaymentMethodSerializer(payment_methods, many=True, context={'request': request})

#         paywall_data = {
#             'payment_methods': payment_serializer.data,
#             'required_amount': settings.PAYMENT_AMOUNT,
#             'currency': settings.PAYMENT_CURRENCY,
#             'description': 'Unlock all premium content and offline access',
#         }

#         # ALL FREE questions (full data, same structure as QuestionSerializer)
#         free_questions_qs = Question.objects.select_related(
#             'road_sign_context', 'road_sign_context__category', 'explanation'
#         ).prefetch_related(
#             'translations',
#             'choices__translations',
#             'choices__road_sign_option',
#             'explanation__translations',
#         ).filter(is_premium=False).order_by('difficulty', 'created_at')

#         question_serializer = QuestionSerializer(
#             free_questions_qs,
#             many=True,
#             context={'request': request}  
#         )

#         # Final response
#         return Response({
#             'metadata': {
#                 'total_questions': total_questions,
#                 'free_questions': free_questions_count,
#                 'premium_questions': premium_questions_count,
#                 'total_road_signs': total_road_signs,
#                 'available_languages': available_languages,
#                 'categories': category_serializer.data,
#                 'question_types': question_types_count,
#                 'difficulty_distribution': difficulty_distribution,
#                 'quiz_config': {
#                     'max_questions_per_quiz': 50,
#                     'time_limits': {'easy': 30, 'medium': 45, 'hard': 60},
#                 },
#                 'miniapp_link': settings.MINIAPP_LINK,
#                 'signin_qr_url': settings.MINIAPP_LINK
#             },
#             'paywall': paywall_data,
#             'free_questions': question_serializer.data,
#             'user': {
#                 'is_authenticated': request.user.is_authenticated,
#                 'is_pro_user': is_pro_user,
#             },
#         })