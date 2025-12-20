# core/middleware/tier_access.py
from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse
from rest_framework import status
import re


class TierAccessMiddleware(MiddlewareMixin):
    """
    Middleware to enforce authentication and Pro tier access across API endpoints.
    Applied globally but skips static/admin/media.
    """

    # Endpoints that require Pro subscription
    PRO_REQUIRED_ENDPOINTS = [
        r'^/api/v1/questions/$',
        r'^/api/v1/questions/all/$',
        r'^/api/v1/questions/all/refresh_token/$',
        r'^/api/v1/search/$',
        r'^/api/v1/exam/$',
        r'^/api/v1/exam/exam_start/$',
        
    ]

    # Endpoints that are completely public (no auth required)
    PUBLIC_ENDPOINTS = [
        r'^/api/v1/home/$',
        r'^/api/v1/payment/$',
        r'^/api/v1/payment/methods/',
        r'^/media/.*',
        
    ]

    # Endpoints that require authentication but NOT necessarily Pro
    AUTH_REQUIRED_ENDPOINTS = [
        r'^/api/v1/auth/me/$',
        r'^/api/v1/payment/verify/$',
        r'^/api/v1/subscription/status/$',
        r'^/api/v1/auth/token/refresh/$',
    ]

    def process_view(self, request, view_func, view_args, view_kwargs):
        path = request.path

        # Always skip admin, static, and media
        if path.startswith(('/admin/', '/static/', '/media/')):
            return None

        # 1. Public endpoints — allow everyone
        for pattern in self.PUBLIC_ENDPOINTS:
            if re.match(pattern, path):
                return None  # Proceed normally

        # 2. Pro-only endpoints
        for pattern in self.PRO_REQUIRED_ENDPOINTS:
            if re.match(pattern, path):
                if not request.user.is_authenticated:
                    return JsonResponse(
                        {'error': 'Authentication required'},
                        status=status.HTTP_401_UNAUTHORIZED
                    )
                if not (hasattr(request.user, 'profile') and request.user.profile.is_pro_user):
                    return JsonResponse(
                        {'error': 'Premium subscription required for this feature'},
                        status=status.HTTP_403_FORBIDDEN
                    )
                return None  # User is Pro → allow

        # 3. Auth-required endpoints (but not necessarily Pro)
        for pattern in self.AUTH_REQUIRED_ENDPOINTS:
            if re.match(pattern, path):
                if not request.user.is_authenticated:
                    return JsonResponse(
                        {'error': 'Authentication required'},
                        status=status.HTTP_401_UNAUTHORIZED
                    )
                return None  # Authenticated → allow

        # 4. All other /api/v1/ endpoints: require authentication
        if path.startswith('/api/v1/'):
            if not request.user.is_authenticated:
                return JsonResponse(
                    {'error': 'Authentication required'},
                    status=status.HTTP_401_UNAUTHORIZED
                )

        # If none of the above, proceed (e.g., root, favicon, etc.)
        return None