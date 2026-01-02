# core/serializers/subscription.py
from rest_framework import serializers
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken
from users.models import (
    SubscriptionTier, 
    SubscriptionTierTranslation, 
    Subscription, UserProfile
)
from .base import AllTranslationsMixin

class SubscriptionTierSerializer(serializers.ModelSerializer, AllTranslationsMixin):
    translations = serializers.SerializerMethodField()
    features = serializers.SerializerMethodField()

    class Meta:
        model = SubscriptionTier
        fields = [
            'id', 'translations', 'price', 'duration_days', 'max_exam_number',
            'ai_assistance_enabled', 'personalized_feedback_enabled',
            'full_road_sign_quiz', 'unlimited_practice', 'offline_access',
            'priority_support', 'ad_free', 'features', 'order', 'popular', 'is_free'
        ]

    def get_translations(self, obj):
        return self.get_translations_dict(
            obj,
            obj.translations.all(),
            fields=['name', 'description']
        )
        
    def get_features(self, obj):
        features = []
        if obj.unlimited_practice:
            features.append("Unlimited Practice")
        if obj.offline_access:
            features.append("Offline Access")
        if obj.priority_support:
            features.append("Priority Support")
        if obj.ad_free:
            features.append("Ad-Free Experience")
        return features
        

    


class SubscriptionSerializer(serializers.ModelSerializer):
    tier = SubscriptionTierSerializer(read_only=True)

    class Meta:
        model = Subscription
        fields = ['id', 'tier', 'start_date', 'expiry_date', 'is_active']


class UserProfileSerializer(serializers.ModelSerializer):
    active_subscription = SubscriptionSerializer(read_only=True)

    class Meta:
        model = UserProfile
        fields = ['tg_id', 'preferred_language', 'active_subscription', 'expiry_date']
        
        

class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'profile']

 
class TelegramAuthResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()
    user = UserSerializer()

    @staticmethod
    def build(user: User):
        refresh = RefreshToken.for_user(user)

        # Telegram-only claims
        refresh["source"] = "telegram"
        refresh["tg_id"] = user.profile.tg_id

        return {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": UserSerializer(user).data,
        } 