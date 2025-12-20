# api/views/search.py
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
import logging

from core.authentication import TelegramAuthenticationBackend
from core.models import (
    RoadSign, RoadSignTranslation, Question, QuestionTranslation,
    ResourceTransaction
)
from core.serializers import (
    RoadSignSerializer, QuestionSerializer, SearchResultSerializer
)
from core.services import BundleService

logger = logging.getLogger(__name__)


class SearchView(APIView):
    """
    GET /api/v1/search/
    Perform search with bundle consumption
    """
    authentication_classes = [TelegramAuthenticationBackend]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        query = request.query_params.get('q', '').strip()
        
        if not query or len(query) < 2:
            return Response(
                {'error': 'Search query must be at least 2 characters'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Consume search resource
        success, bundle, error = BundleService.consume_resource(
            user=request.user,
            resource_type=ResourceTransaction.ResourceType.SEARCH,
            quantity=1,
            description=f"Search: {query[:50]}..."
        )
        
        if not success:
            return Response({
                'error': 'Cannot perform search',
                'detail': error,
                'remaining_resources': bundle.get_remaining_resources() if bundle else None
            }, status=status.HTTP_402_PAYMENT_REQUIRED)
        
        try:
            # Apply search quota limit
            searchable_limit = None
            if bundle and not bundle.bundle_definition.is_unlimited_search:
                searchable_limit = bundle.search_remaining
            
            results = []
            
            # Search with limit
            road_sign_qs = RoadSignTranslation.objects.filter(
                Q(name__icontains=query) |
                Q(meaning__icontains=query) |
                Q(detailed_explanation__icontains=query)
            )
            
            if searchable_limit:
                road_sign_qs = road_sign_qs[:searchable_limit]
            
            road_sign_ids = road_sign_qs.values_list('road_sign_id', flat=True).distinct()
            road_signs = RoadSign.objects.filter(
                id__in=road_sign_ids
            ).select_related('category').prefetch_related('translations')
            


            for road_sign in road_signs:
                # Get ALL translations for this road sign
                road_sign_data = RoadSignSerializer(
                    road_sign,
                    context={'request': request}
                ).data
                
                # Find which translations contain the search query
                matching_translations = []
                for translation in road_sign.translations.all():
                    if (query.lower() in translation.name.lower() or
                        query.lower() in translation.meaning.lower() or
                        query.lower() in translation.detailed_explanation.lower()):
                        
                        match_field = 'name' if query.lower() in translation.name.lower() else \
                                    'meaning' if query.lower() in translation.meaning.lower() else \
                                    'detailed_explanation'
                        
                        match_text = getattr(translation, match_field)
                        
                        matching_translations.append({
                            'language': translation.language,
                            'match_field': match_field,
                            'match_text': self._extract_context(match_text, query),
                            'relevance': self._calculate_relevance(query, match_text)
                        })
                
                if matching_translations:
                    # Get related questions
                    related_questions = Question.objects.filter(
                        road_sign_context=road_sign
                    ).prefetch_related('translations')
                    
                    question_data = QuestionSerializer(
                        related_questions,
                        many=True,
                        context={'request': request}
                    ).data
                    
                    results.append({
                        'type': 'road_sign',
                        'id': str(road_sign.id),
                        'data': road_sign_data,
                        'matching_translations': matching_translations,
                        'related_questions': question_data,
                        'highest_relevance': max([t['relevance'] for t in matching_translations])
                    })
            
            # Search in ALL question translations across ALL languages
            question_qs = QuestionTranslation.objects.filter(
                content__icontains=query
            )
            
            # Get unique questions
            question_ids = question_qs.values_list('question_id', flat=True).distinct()
            questions = Question.objects.filter(
                id__in=question_ids
            ).select_related('road_sign_context', 'explanation').prefetch_related(
                'translations', 'choices__translations', 'explanation__translations'
            )
            
            for question in questions:
                # Get ALL translations for this question
                question_data = QuestionSerializer(
                    question,
                    context={'request': request}
                ).data
                
                # Find which translations contain the search query
                matching_translations = []
                for translation in question.translations.all():
                    if query.lower() in translation.content.lower():
                        match_text = translation.content
                        matching_translations.append({
                            'language': translation.language,
                            'match_field': 'content',
                            'match_text': self._extract_context(match_text, query),
                            'relevance': self._calculate_relevance(query, match_text)
                        })
                
                if matching_translations:
                    # Get related road sign
                    road_sign_data = RoadSignSerializer(
                        question.road_sign_context,
                        context={'request': request}
                    ).data
                    
                    results.append({
                        'type': 'question',
                        'id': str(question.id),
                        'data': question_data,
                        'matching_translations': matching_translations,
                        'related_road_sign': road_sign_data,
                        'highest_relevance': max([t['relevance'] for t in matching_translations])
                    })
            
            # Sort by highest relevance
            results.sort(key=lambda x: x['highest_relevance'], reverse=True)
            
            # Add search metadata
            search_metadata = {
                'query': query,
                'total_results': len(results),
                'search_quota_used': 1,
                'search_remaining': bundle.search_remaining if bundle else 0,
                'results_by_type': {
                    'road_signs': len([r for r in results if r['type'] == 'road_sign']),
                    'questions': len([r for r in results if r['type'] == 'question'])
                },
                'languages_found': self._get_languages_from_results(results),
                'search_suggestions': self._generate_suggestions(query)
            }
            
            
            
            return Response({
                'metadata': search_metadata,
                'results': results[:50]
            })
            
        except Exception as e:
            logger.error(f"Search error: {str(e)}")
            return Response(
                {'error': 'Search failed', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )








































# from rest_framework import status
# from rest_framework.response import Response
# from rest_framework.views import APIView
# from rest_framework.permissions import AllowAny
# from django.db.models import Q, Value, CharField
# from django.db.models.functions import Concat
# import logging

# from core.authentication import TelegramAuthenticationBackend
# from core.models import (
#     RoadSign, RoadSignTranslation, Question, QuestionTranslation
# )
# from core.serializers import (
#     RoadSignSerializer, QuestionSerializer, SearchResultSerializer
# )

# logger = logging.getLogger(__name__)

# class SearchView(APIView):
#     """
#     GET /api/v1/search/
#     Perform full-text search across ALL language translations
#     Returns matches with ALL translations - frontend filters by language
#     """
#     authentication_classes = [TelegramAuthenticationBackend]
#     permission_classes = [AllowAny]
    
#     def get(self, request):
#         query = request.query_params.get('q', '').strip()
        
#         if not query or len(query) < 2:
#             return Response(
#                 {'error': 'Search query must be at least 2 characters'},
#                 status=status.HTTP_400_BAD_REQUEST
#             )
        
#         try:
#             results = []
            
#             # Search in ALL road sign translations across ALL languages
#             road_sign_qs = RoadSignTranslation.objects.filter(
#                 Q(name__icontains=query) |
#                 Q(meaning__icontains=query) |
#                 Q(detailed_explanation__icontains=query)
#             )
            
#             # Get unique road signs
#             road_sign_ids = road_sign_qs.values_list('road_sign_id', flat=True).distinct()
#             road_signs = RoadSign.objects.filter(
#                 id__in=road_sign_ids
#             ).select_related('category').prefetch_related('translations')
            
#             for road_sign in road_signs:
#                 # Get ALL translations for this road sign
#                 road_sign_data = RoadSignSerializer(
#                     road_sign,
#                     context={'request': request}
#                 ).data
                
#                 # Find which translations contain the search query
#                 matching_translations = []
#                 for translation in road_sign.translations.all():
#                     if (query.lower() in translation.name.lower() or
#                         query.lower() in translation.meaning.lower() or
#                         query.lower() in translation.detailed_explanation.lower()):
                        
#                         match_field = 'name' if query.lower() in translation.name.lower() else \
#                                     'meaning' if query.lower() in translation.meaning.lower() else \
#                                     'detailed_explanation'
                        
#                         match_text = getattr(translation, match_field)
                        
#                         matching_translations.append({
#                             'language': translation.language,
#                             'match_field': match_field,
#                             'match_text': self._extract_context(match_text, query),
#                             'relevance': self._calculate_relevance(query, match_text)
#                         })
                
#                 if matching_translations:
#                     # Get related questions
#                     related_questions = Question.objects.filter(
#                         road_sign_context=road_sign
#                     ).prefetch_related('translations')
                    
#                     question_data = QuestionSerializer(
#                         related_questions,
#                         many=True,
#                         context={'request': request}
#                     ).data
                    
#                     results.append({
#                         'type': 'road_sign',
#                         'id': str(road_sign.id),
#                         'data': road_sign_data,
#                         'matching_translations': matching_translations,
#                         'related_questions': question_data,
#                         'highest_relevance': max([t['relevance'] for t in matching_translations])
#                     })
            
#             # Search in ALL question translations across ALL languages
#             question_qs = QuestionTranslation.objects.filter(
#                 content__icontains=query
#             )
            
#             # Get unique questions
#             question_ids = question_qs.values_list('question_id', flat=True).distinct()
#             questions = Question.objects.filter(
#                 id__in=question_ids
#             ).select_related('road_sign_context', 'explanation').prefetch_related(
#                 'translations', 'choices__translations', 'explanation__translations'
#             )
            
#             for question in questions:
#                 # Get ALL translations for this question
#                 question_data = QuestionSerializer(
#                     question,
#                     context={'request': request}
#                 ).data
                
#                 # Find which translations contain the search query
#                 matching_translations = []
#                 for translation in question.translations.all():
#                     if query.lower() in translation.content.lower():
#                         match_text = translation.content
#                         matching_translations.append({
#                             'language': translation.language,
#                             'match_field': 'content',
#                             'match_text': self._extract_context(match_text, query),
#                             'relevance': self._calculate_relevance(query, match_text)
#                         })
                
#                 if matching_translations:
#                     # Get related road sign
#                     road_sign_data = RoadSignSerializer(
#                         question.road_sign_context,
#                         context={'request': request}
#                     ).data
                    
#                     results.append({
#                         'type': 'question',
#                         'id': str(question.id),
#                         'data': question_data,
#                         'matching_translations': matching_translations,
#                         'related_road_sign': road_sign_data,
#                         'highest_relevance': max([t['relevance'] for t in matching_translations])
#                     })
            
#             # Sort by highest relevance
#             results.sort(key=lambda x: x['highest_relevance'], reverse=True)
            
#             # Add search metadata
#             search_metadata = {
#                 'query': query,
#                 'total_results': len(results),
#                 'results_by_type': {
#                     'road_signs': len([r for r in results if r['type'] == 'road_sign']),
#                     'questions': len([r for r in results if r['type'] == 'question'])
#                 },
#                 'languages_found': self._get_languages_from_results(results),
#                 'search_suggestions': self._generate_suggestions(query)
#             }
            
#             return Response({
#                 'metadata': search_metadata,
#                 'results': results[:50]  # Limit results
#             })
            
#         except Exception as e:
#             logger.error(f"Search error: {str(e)}")
#             return Response(
#                 {'error': 'Search failed', 'detail': str(e)},
#                 status=status.HTTP_500_INTERNAL_SERVER_ERROR
#             )
    
#     def _extract_context(self, text, query, context_chars=100):
#         """Extract context around the match"""
#         query_lower = query.lower()
#         text_lower = text.lower()
        
#         idx = text_lower.find(query_lower)
#         if idx == -1:
#             return text[:context_chars] + '...' if len(text) > context_chars else text
        
#         start = max(0, idx - context_chars)
#         end = min(len(text), idx + len(query) + context_chars)
        
#         result = text[start:end]
#         if start > 0:
#             result = '...' + result
#         if end < len(text):
#             result = result + '...'
        
#         return result
    
#     def _calculate_relevance(self, query, text):
#         """Calculate relevance score"""
#         query_lower = query.lower()
#         text_lower = text.lower()
        
#         if text_lower.startswith(query_lower):
#             return 1.0
#         elif query_lower in text_lower:
#             occurrences = text_lower.count(query_lower)
#             return min(0.9, 0.5 + (occurrences * 0.1))
#         else:
#             return 0.3
    
#     def _get_languages_from_results(self, results):
#         """Get unique languages from search results"""
#         languages = set()
#         for result in results:
#             for translation in result.get('matching_translations', []):
#                 languages.add(translation['language'])
#         return sorted(list(languages))
    
#     def _generate_suggestions(self, query):
#         """Generate search suggestions"""
#         suggestions = []
        
#         # Common search terms
#         common_terms = ['stop', 'parking', 'speed', 'yield', 'warning', 'traffic']
        
#         for term in common_terms:
#             if term.startswith(query.lower()):
#                 suggestions.append(term)
        
#         return suggestions[:5]





















































# from rest_framework.views import APIView
# from rest_framework.response import Response
# from rest_framework import status
# from rest_framework.permissions import AllowAny
# from django.db.models import Q
# from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank

# from core.models import Question
# from core.serializers import QuestionSerializer


# class SearchView(APIView):
#     """Unified search across content"""
#     permission_classes = [AllowAny]
    
#     def get(self, request):
#         query = request.query_params.get('q', '').strip()
#         language = request.query_params.get('lang', 'en')
        
#         if not query or len(query) < 2:
#             return Response(
#                 {'error': 'Search query must be at least 2 characters'},
#                 status=status.HTTP_400_BAD_REQUEST
#             )
        
#         user = request.user
#         user_tier = getattr(user, 'tier', 'ANONYMOUS') if user else 'ANONYMOUS'
#         is_premium = user_tier == 'PREMIUM' and user.is_premium() if user else False
        
#         # Base queryset
#         qs = Question.objects.filter(is_active=True)
        
#         if not is_premium:
#             qs = qs.filter(is_premium=False)
        
#         # Build search query
#         search_query = Q()
        
#         # Search in question text
#         search_query |= Q(**{f'question_text__{language}__icontains': query})
        
#         # Search in road sign names
#         search_query |= Q(**{f'standard_name__{language}__icontains': query})
        
#         # Search in sign codes
#         if query.isalnum():
#             search_query |= Q(sign_code__icontains=query)
        
#         # Search in explanations
#         search_query |= Q(**{f'explanation__text__{language}__icontains': query})
        
#         # Apply search
#         results = qs.filter(search_query).distinct()[:20]
        
#         serializer = QuestionSerializer(results, many=True, context={'request': request})
        
#         return Response({
#             'query': query,
#             'count': len(serializer.data),
#             'results': serializer.data,
#             'access_info': {
#                 'user_tier': user_tier,
#                 'is_premium': is_premium,
#                 'can_access_all': is_premium
#             }
#         })
        
        
        
        