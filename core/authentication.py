# core/authentication.py
import json
import hmac
import hashlib
import urllib.parse
import base64
from datetime import datetime
from typing import Dict, Optional, Tuple
from django.conf import settings
from django.contrib.auth.models import User
from rest_framework import authentication
from rest_framework.exceptions import AuthenticationFailed
import logging

logger = logging.getLogger(__name__)


class TelegramAuthenticationBackend(authentication.BaseAuthentication):
    """
    Custom DRF Authentication Backend for Telegram Mini App
    Validates Telegram WebApp init_data passed via Authorization header
    """
    
    def authenticate(self, request) -> Optional[Tuple[User, None]]:
        """
        Authenticate user using Telegram Mini App init_data
        Header format: Authorization: TMA <init_data>
        """
        auth_header = request.headers.get('Authorization', '')
        
        # Check if it's Telegram Mini App authentication
        if not auth_header.startswith('TMA '):
            return None
        
        init_data = auth_header[4:]  # Remove 'TMA ' prefix
        
        try:
            # Parse and validate Telegram init_data
            telegram_user = self.validate_telegram_init_data(init_data)
            if not telegram_user:
                raise AuthenticationFailed('Invalid Telegram authentication data')
            
            # Get or create user
            user, created = self.get_or_create_user(telegram_user)
            
            if created:
                logger.info(f"New user created via Telegram: {telegram_user.get('username')}")
            else:
                logger.debug(f"User authenticated via Telegram: {user.username}")
            
            return (
                    user,
                    {
                        "source": "telegram",
                        "telegram_id": telegram_user["id"],
                    }
                )
        
        except AuthenticationFailed:
            raise
        except Exception as e:
            logger.exception("Unexpected Telegram auth error")
            return None
        
        # except Exception as e:
        #     logger.error(f"Telegram authentication error: {str(e)}")
        #     raise AuthenticationFailed(f'Authentication failed: {str(e)}')
    
    def validate_telegram_init_data(self, init_data: str) -> Optional[Dict]:
        """
        Validate Telegram WebApp initData and extract user info
        """
        if not settings.TELEGRAM_BOT_TOKEN:
            if settings.DEBUG:
                return self._mock_validate_telegram_init_data(init_data)
            raise AuthenticationFailed("Telegram auth misconfigured")
        
        try:
            # Parse init_data
            parsed_data = dict(urllib.parse.parse_qsl(init_data))
            
            # Check if hash exists
            received_hash = parsed_data.pop('hash', None)
            if not received_hash:
                logger.error("No hash found in init_data")
                return None
            
            # Check auth_date (should be within 24 hours)
            auth_date = int(parsed_data.get('auth_date', 0))
            current_time = int(datetime.now().timestamp())
            if abs(current_time - auth_date) > 86400:  # 24 hours
                logger.error("Telegram auth data expired")
                return None
            
            # Create data check string
            data_check_string = '\n'.join(
                f'{key}={value}' for key, value in sorted(parsed_data.items())
            )
            
            # Create secret key
            secret_key = hmac.new(
                key=b"WebAppData",
                msg=settings.TELEGRAM_BOT_TOKEN.encode(),
                digestmod=hashlib.sha256
            ).digest()
            
            # Compute hash
            computed_hash = hmac.new(
                key=secret_key,
                msg=data_check_string.encode(),
                digestmod=hashlib.sha256
            ).hexdigest()
            
            # Compare hashes
            if not hmac.compare_digest(computed_hash, received_hash):
                logger.error("Telegram hash verification failed")
                return None
            
            # Extract user data
            user_json = parsed_data.get('user')
            if not user_json:
                logger.error("No user data in init_data")
                return None
            
            user_data = json.loads(user_json)
            return {
                'id': user_data['id'],
                'username': user_data.get('username'),
                'first_name': user_data.get('first_name', ''),
                'last_name': user_data.get('last_name', ''),
                'language_code': user_data.get('language_code', 'en'),
                'photo_url': user_data.get('photo_url'),
                'is_premium': user_data.get('is_premium', False),
            }
        
        except Exception as e:
            logger.error(f"Error validating Telegram init_data: {str(e)}")
            return None
    
    def _mock_validate_telegram_init_data(self, init_data: str) -> Dict:
        """
        Mock validation for development/testing
        In production, always use real Telegram validation
        """
        try:
            # Try to parse as base64 encoded JSON for mock data
            decoded = base64.b64decode(init_data).decode('utf-8')
            user_data = json.loads(decoded)
            
            if 'id' not in user_data:
                user_data = {
                    'id': 123456789,
                    'username': 'test_user',
                    'first_name': 'Test',
                    'last_name': 'User',
                    'language_code': 'en',
                    'is_premium': False,
                }
            
            return user_data
        except:
            # Return mock data if parsing fails
            return {
                'id': 123456789,
                'username': 'test_user',
                'first_name': 'Test',
                'last_name': 'User',
                'language_code': 'en',
                'is_premium': False,
            }
    
    def get_or_create_user(self, telegram_user: Dict) -> Tuple[User, bool]:
        """
        Get or create Django user from Telegram user data
        """
        telegram_id = telegram_user['id']
        
        try:
            # Try to find existing user by telegram_id in profile
            from core.models import UserProfile
            profile = UserProfile.objects.select_related('user').get(telegram_id=telegram_id)
            
            # Update profile if needed
            update_fields = []
            username = telegram_user.get('username') or f"tg_{telegram_id}"
            if profile.telegram_username != username:
                profile.telegram_username = username
                update_fields.append('telegram_username')
            
            if update_fields:
                profile.save(update_fields=update_fields)
            
            return profile.user, False
            
        except UserProfile.DoesNotExist:
            # Create new user
            username = telegram_user.get('username') or f"telegram_{telegram_id}"
            first_name = telegram_user.get('first_name', '')
            last_name = telegram_user.get('last_name', '')
            
            # Create Django User
            user = User.objects.create(
                username=username,
                first_name=first_name,
                last_name=last_name,
                is_active=True
            )
            
            # Create UserProfile
            from core.models import UserProfile
            UserProfile.objects.create(
                user=user,
                telegram_id=telegram_id,
                telegram_username=telegram_user.get('username'),
                telegram_data=telegram_user
            )
            
            return user, True
        
        