# api/views/access_control.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
import logging

from core.authentication import TelegramAuthenticationBackend
from core.models import UserProfile

logger = logging.getLogger(__name__)


class UserAccessView(APIView):
    """
    GET /api/v1/subscription/access/
    Get user's subscription access information
    """
    authentication_classes = [TelegramAuthenticationBackend]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            profile = request.user.profile
        except UserProfile.DoesNotExist:
            return Response({
                'has_active_subscription': False,
                'subscription_status': 'no_profile'
            })
        
        # Check if user has active subscription
        if not profile.has_active_subscription:
            return Response({
                'has_active_subscription': False,
                'subscription_status': 'inactive'
            })
        
        subscription = profile.active_subscription
        package = subscription.package
        
        # Check if subscription is expired
        if subscription.expires_at < timezone.now():
            return Response({
                'has_active_subscription': False,
                'subscription_status': 'expired',
                'expired_at': subscription.expires_at.isoformat()
            })
        
        # Build feature access object
        features = {
            'smart_search': subscription.has_feature('smart_search'),
            'ai_chat': subscription.has_feature('ai_chat'),
            'exam_simulation': subscription.has_feature('exam_simulation'),
            'offline_access': subscription.has_feature('offline_access'),
            'premium_questions': subscription.has_feature('premium_questions'),
        }
        
        # Build quota information
        quotas = {
            'ai_chat': {
                'total': package.max_api_chats if package.max_api_chats > 0 else 'Unlimited',
                'used': subscription.api_chats_used,
                'remaining': subscription.quota_remaining('api_chats')
            },
            'exam_simulation': {
                'total': package.max_exams if package.max_exams > 0 else 'Unlimited',
                'used': subscription.exams_taken,
                'remaining': subscription.quota_remaining('exams')
            }
        }
        
        response_data = {
            'has_active_subscription': True,
            'subscription_status': 'active',
            'subscription': {
                'id': str(subscription.id),
                'package_name': package.name,
                'package_type': package.package_type,
                'starts_at': subscription.starts_at.isoformat(),
                'expires_at': subscription.expires_at.isoformat(),
                'days_remaining': subscription.days_remaining,
                'auto_renew': subscription.auto_renew
            },
            'features': features,
            'quotas': quotas,
            'limits': {
                'max_questions_per_exam': package.max_questions_per_exam,
                'exam_time_limit': request.user.profile.exam_time_limit
            }
        }
        
        return Response(response_data)


class FeatureAccessView(APIView):
    """
    POST /api/v1/subscription/check-access/
    Check access to specific feature
    """
    authentication_classes = [TelegramAuthenticationBackend]
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        feature_name = request.data.get('feature')
        check_quota = request.data.get('check_quota', True)
        
        if not feature_name:
            return Response({
                'error': 'Feature name is required'
            }, status=400)
        
        try:
            profile = request.user.profile
        except UserProfile.DoesNotExist:
            return Response({
                'has_access': False,
                'reason': 'no_profile'
            })
        
        # Check access
        has_access = profile.check_access(feature_name, check_quota)
        
        response_data = {
            'has_access': has_access,
            'feature': feature_name,
            'requires_subscription': True
        }
        
        if has_access:
            # Add quota info if applicable
            if feature_name in ['ai_chat', 'exam_simulation']:
                quota_type = 'api_chats' if feature_name == 'ai_chat' else 'exams'
                remaining = profile.get_quota_remaining(quota_type)
                
                response_data['quota'] = {
                    'remaining': remaining,
                    'has_quota': remaining > 0 if isinstance(remaining, int) else True
                }
        
        return Response(response_data)


class UseFeatureView(APIView):
    """
    POST /api/v1/subscription/use-feature/
    Use a feature (consume quota)
    """
    authentication_classes = [TelegramAuthenticationBackend]
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        feature_name = request.data.get('feature')
        amount = request.data.get('amount', 1)
        
        if not feature_name:
            return Response({
                'error': 'Feature name is required'
            }, status=400)
        
        try:
            profile = request.user.profile
        except UserProfile.DoesNotExist:
            return Response({
                'success': False,
                'error': 'User profile not found'
            })
        
        # Check access first
        if not profile.check_access(feature_name, check_quota=True):
            return Response({
                'success': False,
                'error': 'Access denied or quota exhausted'
            }, status=403)
        
        # Use the feature (consume quota)
        success = profile.use_feature(feature_name, amount)
        
        if success:
            # Get updated quota info
            quota_type = 'api_chats' if feature_name == 'ai_chat' else 'exams' if feature_name == 'exam_simulation' else None
            
            response_data = {
                'success': True,
                'feature': feature_name,
                'amount_used': amount
            }
            
            if quota_type:
                remaining = profile.get_quota_remaining(quota_type)
                response_data['quota_remaining'] = remaining
            
            return Response(response_data)
        else:
            return Response({
                'success': False,
                'error': 'Failed to use feature'
            }, status=400)