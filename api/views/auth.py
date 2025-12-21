# api/views/auth.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status

from rest_framework_simplejwt.views import TokenRefreshView
from core.authentication import TelegramAuthenticationBackend
from core.serializers import TelegramAuthResponseSerializer, UserSerializer
from core.permissions import IsTelegramAuthenticated


class TelegramLoginView(APIView):
    """
    Telegram Mini App authentication endpoint.

    Header:
        Authorization: TMA <init_data>
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        user = request.user

        if not user or not user.is_authenticated:
            return Response(
                {"detail": "Invalid Telegram authentication"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        data = TelegramAuthResponseSerializer.build(user)
        return Response(data, status=status.HTTP_200_OK)


class TelegramTokenRefreshView(TokenRefreshView):
    """
    Refresh JWT access token.
    """
    pass


class MeView(APIView):
    """
    Verify JWT and return current user.
    """

    permission_classes = [IsAuthenticated, IsTelegramAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)





















































# # api/views/auth.py
# import hmac
# import hashlib
# import json
# from urllib.parse import parse_qsl, quote
# from datetime import timedelta

# from rest_framework.views import APIView
# from rest_framework.response import Response
# from rest_framework import status
# from rest_framework.permissions import AllowAny
# from rest_framework_simplejwt.tokens import RefreshToken
# from rest_framework_simplejwt.exceptions import TokenError
# from django.conf import settings
# from django.utils import timezone
# from django.core.cache import cache
# from django.db import transaction

# from core.models import User
# from core.serializers import UserSerializer


# class TelegramAuthView(APIView):
#     """Verify Telegram WebApp authentication"""
#     permission_classes = [AllowAny]
    
#     def post(self, request):
#         init_data = request.data.get('initData')
#         if not init_data:
#             return Response(
#                 {'error': 'No initData provided'}, 
#                 status=status.HTTP_400_BAD_REQUEST
#             )
        
#         # Verify signature
#         if not self.verify_telegram_signature(init_data):
#             return Response(
#                 {'error': 'Invalid signature'}, 
#                 status=status.HTTP_401_UNAUTHORIZED
#             )
        
#         # Parse user data
#         data_pairs = parse_qsl(init_data)
#         data_dict = dict(data_pairs)
#         user_str = data_dict.get('user')
        
#         if not user_str:
#             return Response(
#                 {'error': 'No user data'}, 
#                 status=status.HTTP_400_BAD_REQUEST
#             )
        
#         try:
#             user_data = json.loads(user_str)
#             telegram_id = str(user_data['id'])
#         except (json.JSONDecodeError, KeyError):
#             return Response(
#                 {'error': 'Invalid user data'}, 
#                 status=status.HTTP_400_BAD_REQUEST
#             )
        
#         # Create or update user
#         with transaction.atomic():
#             user, created = User.objects.update_or_create(
#                 telegram_id=telegram_id,
#                 defaults={
#                     'telegram_username': user_data.get('username'),
#                     'telegram_first_name': user_data.get('first_name'),
#                     'telegram_last_name': user_data.get('last_name'),
#                     'telegram_photo_url': user_data.get('photo_url'),
#                     'tier': 'AUTHENTICATED',
#                     'username': f"telegram_{telegram_id}",
#                     'email': f"{telegram_id}@telegram.driving.app",
#                 }
#             )
            
#             # Generate tokens
#             refresh = RefreshToken.for_user(user)
#             access_token = str(refresh.access_token)
#             refresh_token = str(refresh)
            
#             # Cache authentication
#             cache_key = f"user_auth_{telegram_id}"
#             cache.set(cache_key, {
#                 'user_id': str(user.id),
#                 'telegram_id': telegram_id,
#                 'access_token': access_token
#             }, timeout=3600)
        
#         return Response({
#             'user': UserSerializer(user).data,
#             'tokens': {
#                 'access': access_token,
#                 'refresh': refresh_token,
#             }
#         })
    
#     def verify_telegram_signature(self, init_data):
#         """Verify Telegram WebApp signature"""
#         bot_token = settings.TELEGRAM_BOT_TOKEN
        
#         # Parse data
#         data_pairs = parse_qsl(init_data)
#         data_dict = dict(data_pairs)
        
#         # Remove hash
#         received_hash = data_dict.pop('hash', '')
#         if not received_hash:
#             return False
        
#         # Create data check string
#         data_check_pairs = []
#         for key in sorted(data_dict.keys()):
#             value = data_dict[key]
#             if value:
#                 data_check_pairs.append(f"{key}={value}")
        
#         data_check_string = "\n".join(data_check_pairs)
        
#         # Generate secret key
#         secret_key = hmac.new(
#             key=b"WebAppData",
#             msg=bot_token.encode(),
#             digestmod=hashlib.sha256
#         ).digest()
        
#         # Generate expected hash
#         expected_hash = hmac.new(
#             key=secret_key,
#             msg=data_check_string.encode(),
#             digestmod=hashlib.sha256
#         ).hexdigest()
        
#         return expected_hash == received_hash


# class RefreshTokenView(APIView):
#     """Refresh JWT token"""
#     permission_classes = [AllowAny]
    
#     def post(self, request):
#         refresh_token = request.data.get('refresh')
        
#         if not refresh_token:
#             return Response(
#                 {'error': 'Refresh token required'}, 
#                 status=status.HTTP_400_BAD_REQUEST
#             )
        
#         try:
#             refresh = RefreshToken(refresh_token)
#             user_id = refresh['user_id']
            
#             user = User.objects.get(id=user_id)
#             new_refresh = RefreshToken.for_user(user)
            
#             return Response({
#                 'access': str(new_refresh.access_token),
#                 'refresh': str(new_refresh),
#             })
            
#         except (TokenError, User.DoesNotExist):
#             return Response(
#                 {'error': 'Invalid refresh token'}, 
#                 status=status.HTTP_401_UNAUTHORIZED
#             )


# class LogoutView(APIView):
#     """Logout user by blacklisting token"""
    
#     def post(self, request):
#         try:
#             refresh_token = request.data.get('refresh')
#             token = RefreshToken(refresh_token)
#             token.blacklist()
#             return Response({'success': True})
#         except Exception as e:
#             return Response(
#                 {'error': str(e)}, 
#                 status=status.HTTP_400_BAD_REQUEST
#             )


# class UserProfileView(APIView):
#     """Get current user profile"""
    
#     def get(self, request):
#         serializer = UserSerializer(request.user)
#         return Response(serializer.data)