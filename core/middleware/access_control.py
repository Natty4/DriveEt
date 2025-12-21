# core/middleware/access_control.py
from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse
from rest_framework import status
import re
from django.utils import timezone
from core.models import ResourceTransaction
from core.services import BundleService






class AccessControlMiddleware:
    """
    Middleware to enforce bundle-based access control
    Replaces the old TierAccessMiddleware
    """
    
    # Endpoints that require specific resources
    RESOURCE_REQUIRED_ENDPOINTS = {
        r'^/api/v1/exam/$': ResourceTransaction.ResourceType.EXAM,
        r'^/api/v1/exam/exam_start/$': ResourceTransaction.ResourceType.EXAM,
        r'^/api/v1/ai/chat/$': ResourceTransaction.ResourceType.CHAT,
        r'^/api/v1/search/$': ResourceTransaction.ResourceType.SEARCH,
        r'^/api/v1/questions/$': ResourceTransaction.ResourceType.SEARCH,  # For searchable questions
    }
    
    # Endpoints that are completely public (no bundle required)
    PUBLIC_ENDPOINTS = [
        r'^/api/v1/meta/$',
        r'^/api/v1/payment/$',
        r'^/api/v1/payment/methods/',
        r'^/media/.*',
        r'^/api/v1/auth/.*',
        r'^/api/v1/subscription/status/$',  # Now shows bundle status
    ]
    
    # Endpoints that require authentication but NOT bundle
    AUTH_REQUIRED_ENDPOINTS = [
        r'^/api/v1/auth/me/$',
        r'^/api/v1/payment/verify/$',
        r'^/api/v1/bundles/.*',
    ]
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        return self.get_response(request)
    
    def process_view(self, request, view_func, view_args, view_kwargs):
        path = request.path
        
        # Always skip admin, static, and media
        if path.startswith(('/admin/', '/static/', '/media/')):
            return None
        
        import re
        
        # 1. Public endpoints — allow everyone
        for pattern in self.PUBLIC_ENDPOINTS:
            if re.match(pattern, path):
                return None
        
        # 2. Resource-required endpoints
        for pattern, resource_type in self.RESOURCE_REQUIRED_ENDPOINTS.items():
            if re.match(pattern, path):
                if not request.user.is_authenticated:
                    return self._json_response(
                        {'error': 'Authentication required'},
                        status=401
                    )
                
                # Check if road sign quiz endpoint
                if 'road_sign' in path and resource_type == ResourceTransaction.ResourceType.ROAD_SIGN:
                    bundle = BundleService.get_active_bundle(request.user)
                    if bundle and bundle.has_unlimited_road_sign_quiz:
                        return None
                
                # Check resource access
                can_access, bundle, error = BundleService.check_resource_access(
                    request.user, resource_type
                )
                
                if not can_access:
                    if bundle and bundle.is_expired:
                        return self._json_response(
                            {
                                'error': 'Bundle expired',
                                'code': 'BUNDLE_EXPIRED',
                                'message': 'Your bundle has expired. Please purchase a new one.'
                            },
                            status=403
                        )
                    else:
                        return self._json_response(
                            {
                                'error': 'Resource limit reached',
                                'code': 'RESOURCE_LIMIT',
                                'message': error,
                                'remaining_resources': bundle.get_remaining_resources() if bundle else None
                            },
                            status=402  # Payment Required
                        )
                return None
        
        # 3. Auth-required endpoints (but not bundle)
        for pattern in self.AUTH_REQUIRED_ENDPOINTS:
            if re.match(pattern, path):
                if not request.user.is_authenticated:
                    return self._json_response(
                        {'error': 'Authentication required'},
                        status=401
                    )
                return None
        
        # 4. All other /api/v1/ endpoints: require authentication
        if path.startswith('/api/v1/'):
            if not request.user.is_authenticated:
                return self._json_response(
                    {'error': 'Authentication required'},
                    status=401
                )
        
        return None
    
    def _json_response(self, data, status=200):
        from django.http import JsonResponse
        return JsonResponse(data, status=status)











# class SubscriptionAccessMiddleware(MiddlewareMixin):
#     """
#     Middleware to enforce subscription-based access control
#     """
    
#     # Feature-specific endpoints
#     FEATURE_ENDPOINTS = {
#         'smart_search': [
#             r'^/api/v1/search/$',
#         ],
#         'ai_chat': [
#             r'^/api/v1/ai/chat/$',
#         ],
#         'exam_simulation': [
#             r'^/api/v1/exam/$',
#             r'^/api/v1/exam/exam_start/$',
#         ],
#         'offline_access': [
#             r'^/api/v1/questions/all/$',
#             r'^/api/v1/questions/all/refresh_token/$',
#         ],
#         'premium_questions': [
#             r'^/api/v1/questions/$',  # All questions endpoint
#         ]
#     }
    
#     # Endpoints that are completely public (no auth required)
#     PUBLIC_ENDPOINTS = [
#         r'^/api/v1/home/$',
#         r'^/api/v1/payment/$',
#         r'^/api/v1/payment/methods/',
#         r'^/media/.*',
#     ]
    
#     # Endpoints that require authentication but NOT subscription
#     AUTH_REQUIRED_ENDPOINTS = [
#         r'^/api/v1/auth/me/$',
#         r'^/api/v1/payment/verify/$',
#         r'^/api/v1/subscription/status/$',
#         r'^/api/v1/auth/token/refresh/$',
#     ]
    
#     def process_view(self, request, view_func, view_args, view_kwargs):
#         path = request.path
        
#         # Always skip admin, static, and media
#         if path.startswith(('/admin/', '/static/', '/media/')):
#             return None
        
#         # 1. Public endpoints — allow everyone
#         for pattern in self.PUBLIC_ENDPOINTS:
#             if re.match(pattern, path):
#                 return None
        
#         # Check if user is authenticated
#         if not request.user.is_authenticated:
#             return JsonResponse(
#                 {'error': 'Authentication required'},
#                 status=status.HTTP_401_UNAUTHORIZED
#             )
        
#         # 2. Auth-required endpoints (but not necessarily subscription)
#         for pattern in self.AUTH_REQUIRED_ENDPOINTS:
#             if re.match(pattern, path):
#                 return None
        
#         # 3. Check feature-specific endpoints
#         for feature, patterns in self.FEATURE_ENDPOINTS.items():
#             for pattern in patterns:
#                 if re.match(pattern, path):
#                     # Check if user has access to this feature
#                     if not self._check_feature_access(request, feature, path):
#                         return self._get_feature_error_response(feature)
#                     return None
        
#         # 4. All other /api/v1/ endpoints: require basic authentication
#         if path.startswith('/api/v1/'):
#             # Basic check - user must be authenticated
#             return None
        
#         # If none of the above, proceed
#         return None
    
#     def _check_feature_access(self, request, feature_name, path):
#         """Check if user has access to a specific feature"""
#         try:
#             profile = request.user.profile
#         except AttributeError:
#             return False
        
#         # Check if user has active subscription
#         if not profile.has_active_subscription:
#             return False
        
#         # Check if subscription has expired
#         if profile.active_subscription.expires_at < timezone.now():
#             # Deactivate expired subscription
#             profile.active_subscription.is_active = False
#             profile.active_subscription.save()
#             profile.active_subscription = None
#             profile.save()
#             return False
        
#         # Check feature access
#         if not profile.check_access(feature_name):
#             return False
        
#         # Check quota for specific features
#         if feature_name == 'ai_chat':
#             # Check if API chats quota is available
#             return profile.get_quota_remaining('api_chats') > 0
#         elif feature_name == 'exam_simulation':
#             # Check if exams quota is available
#             return profile.get_quota_remaining('exams') > 0
        
#         return True
    
#     def _get_feature_error_response(self, feature_name):
#         """Get appropriate error response for feature access denial"""
#         error_messages = {
#             'smart_search': 'Smart Search requires a premium subscription',
#             'ai_chat': 'AI Chat feature requires a premium subscription',
#             'exam_simulation': 'Exam simulation requires a premium subscription',
#             'offline_access': 'Offline access requires a premium subscription',
#             'premium_questions': 'Premium questions require a premium subscription',
#         }
        
#         error_message = error_messages.get(feature_name, 'Subscription required for this feature')
        
#         # Check if it's a quota issue
#         if feature_name in ['ai_chat', 'exam_simulation']:
#             return JsonResponse(
#                 {
#                     'error': f'Quota exhausted for {feature_name.replace("_", " ").title()}',
#                     'code': 'QUOTA_EXHAUSTED',
#                     'message': 'Please upgrade your plan or wait for quota reset'
#                 },
#                 status=status.HTTP_402_PAYMENT_REQUIRED
#             )
        
#         return JsonResponse(
#             {
#                 'error': error_message,
#                 'code': 'SUBSCRIPTION_REQUIRED',
#                 'message': 'Please upgrade your subscription to access this feature'
#             },
#             status=status.HTTP_402_PAYMENT_REQUIRED
#         )





















# from django.utils.deprecation import MiddlewareMixin
# from django.http import JsonResponse
# from rest_framework import status
# import re
# from django.utils import timezone
# from django.core.cache import cache


# class SubscriptionAccessMiddleware(MiddlewareMixin):
#     """
#     Middleware to enforce subscription-based access control
#     """
    
#     # Feature-specific endpoints with required permissions
#     FEATURE_ENDPOINTS = {
#         'smart_search': [
#             r'^/api/v1/search/$',
#         ],
#         'ai_chat': [
#             r'^/api/v1/ai/chat/$',
#         ],
#         'offline_access': [
#             r'^/api/v1/questions/all/$',
#             r'^/api/v1/questions/all/refresh_token/$',
#         ],
#         'premium_content': [
#             r'^/api/v1/questions/premium/$',
#             r'^/api/v1/articles/premium/$',
#         ]
#     }
    
#     # Endpoints that require quota checks
#     QUOTA_ENDPOINTS = {
#         'api_chats': r'^/api/v1/ai/chat/$',
#         'exams': r'^/api/v1/exam/start_exam/$',
#         'questions': r'^/api/v1/questions/(?!metadata|categories).*$',
#     }
    
#     # Public endpoints
#     PUBLIC_ENDPOINTS = [
#         r'^/api/v1/home/$',
#         r'^/api/v1/payment/methods/$',
#         r'^/media/.*',
#         r'^/api/v1/auth/.*',
#     ]
    
#     def process_view(self, request, view_func, view_args, view_kwargs):
#         path = request.path
        
#         # Always skip admin, static, and media
#         if path.startswith(('/admin/', '/static/', '/media/')):
#             return None
        
#         # 1. Public endpoints - allow everyone
#         for pattern in self.PUBLIC_ENDPOINTS:
#             if re.match(pattern, path):
#                 return None
        
#         # 2. Check authentication
#         if not request.user.is_authenticated:
#             return JsonResponse(
#                 {'error': 'Authentication required'},
#                 status=status.HTTP_401_UNAUTHORIZED
#             )
        
#         # 3. Check if user has active subscription
#         if not hasattr(request.user, 'profile'):
#             return JsonResponse(
#                 {'error': 'User profile not found'},
#                 status=status.HTTP_400_BAD_REQUEST
#             )
        
#         profile = request.user.profile
        
#         # 4. Check subscription expiry
#         if profile.current_subscription and profile.current_subscription.is_expired:
#             # Revoke premium access
#             profile.is_pro_user = False
#             profile.save()
            
#             # Clear cache
#             cache_key = f'user_subscription_{request.user.id}'
#             cache.delete(cache_key)
            
#             return JsonResponse(
#                 {
#                     'error': 'Subscription expired',
#                     'message': 'Please renew your subscription to access premium features'
#                 },
#                 status=status.HTTP_402_PAYMENT_REQUIRED
#             )
        
#         # 5. Check feature access
#         for feature, patterns in self.FEATURE_ENDPOINTS.items():
#             for pattern in patterns:
#                 if re.match(pattern, path):
#                     if not profile.has_feature(feature):
#                         return JsonResponse(
#                             {
#                                 'error': f'{feature.replace("_", " ").title()} not available',
#                                 'message': f'Upgrade to a higher package to access {feature}'
#                             },
#                             status=status.HTTP_403_FORBIDDEN
#                         )
        
#         # 6. Check quota limits
#         for quota_type, pattern in self.QUOTA_ENDPOINTS.items():
#             if re.match(pattern, path):
#                 if profile.remaining_quota(quota_type) <= 0:
#                     return JsonResponse(
#                         {
#                             'error': f'{quota_type.replace("_", " ").title()} quota exceeded',
#                             'message': f'You have reached your monthly limit for {quota_type}. Upgrade for more.'
#                         },
#                         status=status.HTTP_402_PAYMENT_REQUIRED
#                     )
        
#         return None


# class UsageTrackingMiddleware(MiddlewareMixin):
#     """
#     Middleware to track feature usage and update quotas
#     """
    
#     def process_response(self, request, response):
#         # Only track successful requests for authenticated users
#         if (request.user.is_authenticated and 
#             hasattr(request.user, 'profile') and 
#             response.status_code in [200, 201]):
            
#             profile = request.user.profile
#             path = request.path
            
#             # Track API chat usage
#             if re.match(r'^/api/v1/ai/chat/$', path) and request.method == 'POST':
#                 if profile.current_subscription:
#                     profile.current_subscription.increment_api_chat_usage()
            
#             # Track exam usage
#             elif re.match(r'^/api/v1/exam/start_exam/$', path) and request.method == 'POST':
#                 if profile.current_subscription:
#                     profile.current_subscription.increment_exam_usage()
            
#             # Track question access
#             elif re.match(r'^/api/v1/questions/', path) and request.method == 'GET':
#                 # Count questions in response if it's a list
#                 if hasattr(response, 'data') and isinstance(response.data, list):
#                     count = len(response.data)
#                     if profile.current_subscription:
#                         profile.current_subscription.increment_question_usage(count)
        
#         return response