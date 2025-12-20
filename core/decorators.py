from functools import wraps
from django.http import JsonResponse
from rest_framework import status
from django.utils import timezone
from django.core.cache import cache


def require_subscription(feature=None, quota_type=None):
    """
    Decorator to check subscription access for specific features
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # Check authentication
            if not request.user.is_authenticated:
                return JsonResponse(
                    {'error': 'Authentication required'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            # Check user profile
            if not hasattr(request.user, 'profile'):
                return JsonResponse(
                    {'error': 'User profile not found'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            profile = request.user.profile
            
            # Check subscription expiry
            if profile.current_subscription and profile.current_subscription.is_expired:
                return JsonResponse(
                    {
                        'error': 'Subscription expired',
                        'message': 'Please renew your subscription'
                    },
                    status=status.HTTP_402_PAYMENT_REQUIRED
                )
            
            # Check specific feature access
            if feature and not profile.has_feature(feature):
                return JsonResponse(
                    {
                        'error': f'Feature not available',
                        'message': f'This feature requires {feature} package'
                    },
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Check quota
            if quota_type and profile.remaining_quota(quota_type) <= 0:
                return JsonResponse(
                    {
                        'error': f'Quota exceeded',
                        'message': f'You have reached your monthly limit for {quota_type}'
                    },
                    status=status.HTTP_402_PAYMENT_REQUIRED
                )
            
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


def track_usage(quota_type, increment=1):
    """
    Decorator to track feature usage
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            response = view_func(request, *args, **kwargs)
            
            # Only track successful requests
            if response.status_code in [200, 201] and request.user.is_authenticated:
                profile = request.user.profile
                
                if profile.current_subscription:
                    if quota_type == 'api_chats':
                        profile.current_subscription.increment_api_chat_usage()
                    elif quota_type == 'exams':
                        profile.current_subscription.increment_exam_usage()
                    elif quota_type == 'questions':
                        profile.current_subscription.increment_question_usage(increment)
            
            return response
        return _wrapped_view
    return decorator