from django.utils import timezone
from django.core.cache import cache
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


class SubscriptionManager:
    """
    Manager for subscription-related operations
    """
    
    @staticmethod
    def get_user_subscription_status(user):
        """Get comprehensive subscription status for user"""
        cache_key = f'user_subscription_{user.id}'
        cached_status = cache.get(cache_key)
        
        if cached_status:
            return cached_status
        
        try:
            profile = user.profile
            subscription = profile.current_subscription
            
            status = {
                'has_active_subscription': False,
                'package_type': 'free',
                'expires_at': None,
                'days_remaining': 0,
                'features': {},
                'quotas': {},
                'usage': {}
            }
            
            if subscription and subscription.is_active and not subscription.is_expired:
                status['has_active_subscription'] = True
                status['package_type'] = subscription.package.package_type
                status['expires_at'] = subscription.expires_at.isoformat()
                status['days_remaining'] = subscription.days_remaining
                
                # Feature flags
                status['features'] = {
                    'smart_search': subscription.has_smart_search_access,
                    'ai_chat': subscription.has_ai_chat_access,
                    'offline_access': subscription.has_offline_access,
                    'premium_content': subscription.package.has_premium_content,
                }
                
                # Quotas
                status['quotas'] = {
                    'api_chats': {
                        'max': subscription.package.max_api_chats,
                        'used': subscription.api_chats_used,
                        'remaining': max(0, subscription.package.max_api_chats - subscription.api_chats_used)
                    },
                    'exams': {
                        'max': subscription.package.max_exams,
                        'used': subscription.exams_taken,
                        'remaining': max(0, subscription.package.max_exams - subscription.exams_taken)
                    },
                    'questions': {
                        'max': subscription.package.max_questions,
                        'used': subscription.questions_accessed,
                        'remaining': max(0, subscription.package.max_questions - subscription.questions_accessed)
                    }
                }
            
            # Cache for 5 minutes
            cache.set(cache_key, status, 300)
            return status
            
        except Exception as e:
            logger.error(f"Error getting subscription status: {str(e)}")
            return None
    
    @staticmethod
    def check_access(user, feature=None, quota_type=None):
        """Check if user has access to specific feature/quota"""
        status = SubscriptionManager.get_user_subscription_status(user)
        
        if not status or not status['has_active_subscription']:
            return False
        
        if feature and not status['features'].get(feature, False):
            return False
        
        if quota_type:
            quota = status['quotas'].get(quota_type, {})
            if quota.get('remaining', 0) <= 0:
                return False
        
        return True
    
    @staticmethod
    def reset_monthly_usage():
        """Reset monthly usage for all active subscriptions"""
        from core.models import UserSubscription
        from django.utils import timezone
        
        try:
            active_subscriptions = UserSubscription.objects.filter(
                is_active=True,
                expires_at__gte=timezone.now()
            )
            
            for subscription in active_subscriptions:
                # Reset on 1st of every month
                if timezone.now().day == 1:
                    subscription.reset_monthly_usage()
                    logger.info(f"Reset monthly usage for {subscription.user.username}")
            
            return True
        except Exception as e:
            logger.error(f"Error resetting monthly usage: {str(e)}")
            return False