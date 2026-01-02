# core/viewsets/auth.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status
from rest_framework_simplejwt.views import TokenRefreshView

from users.authentication import TelegramAuthenticationBackend
from core.serializers.subscription import TelegramAuthResponseSerializer
from core.permissions import IsTelegramAuthenticated
from users.models import (
    SubscriptionTier, 
    Subscription, 
    SubscriptionTierTranslation
)
from django.utils import timezone


class TelegramLoginView(APIView):
    """
    Telegram Mini App authentication endpoint.
    Header:
        Authorization: TMA <init_data>

    On first successful login:
        - Automatically grants the Free Subscription Tier (price=0)
        - Creates a permanent Subscription (no expiry)
        - Sets as active subscription
    """
    permission_classes = [AllowAny]

    def post(self, request):
        user = request.user
        if not user or not user.is_authenticated:
            return Response(
                {"detail": "Invalid Telegram authentication"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Check if this is a new user (first login)
        profile = user.profile
        created = getattr(user, '_fresh_login', False)  # Set by authentication backend if user just created

        if created or not profile.active_subscription:
            # Find or ensure Free Tier exists (price=0)
            free_tier = SubscriptionTier.objects.filter(price=0).first()
            if not free_tier:
                # Optional: Create free tier if missing (admin should have one)
                free_tier = SubscriptionTier.objects.create(
                    price=0,
                    duration_days=0,  # Permanent
                    max_exam_number=1,
                    full_road_sign_quiz=False,
                    ai_assistance_enabled=False,
                    personalized_feedback_enabled=False
                )
                # Add translations for free tier
                from core.models import Language
                free_names = {
                    'en': "Free Plan",
                    'am': "ነጻ ፓኬጅ",
                    'ti': "ፕላን ብዝክፈለ",
                    'or': "Paakeejii Bilisaa"
                }
                for lang_code in ['en', 'am', 'ti', 'or']:
                    SubscriptionTierTranslation.objects.create(
                        tier=free_tier,
                        language=lang_code,
                        name=free_names.get(lang_code, "Free Plan"),
                        description="Free access with limited features"
                    )

            # Create permanent free subscription if not exists
            subscription, sub_created = Subscription.objects.get_or_create(
                user_profile=profile,
                tier=free_tier,
                is_active=True,
                defaults={
                    'expiry_date': None  # Permanent
                }
            )

            # Activate it
            profile.active_subscription = subscription
            profile.expiry_date = None  # Free users have no expiry
            profile.save(update_fields=['active_subscription', 'expiry_date'])

        # Build JWT response
        data = TelegramAuthResponseSerializer.build(user)
        return Response(data, status=status.HTTP_200_OK)


class TelegramTokenRefreshView(TokenRefreshView):
    """
    Refresh JWT access token.
    """
    pass