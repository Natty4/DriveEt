# core/viewsets/subscription.py

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from users.models import SubscriptionTier
from core.serializers.subscription import (
    SubscriptionTierSerializer, 
    UserProfileSerializer
)
from core.permissions import IsTelegramAuthenticated
from core.responses import APIResponse

from django.contrib.auth import get_user_model
class SubscriptionViewSet(viewsets.ViewSet):
    permission_classes = [IsTelegramAuthenticated]

    @action(detail=False, methods=['get'])
    def tiers(self, request):
        tiers = SubscriptionTier.objects.filter(is_free=False).prefetch_related('translations')
        serializer = SubscriptionTierSerializer(tiers, many=True, context={'request': request})
        return APIResponse.success(data=serializer.data)

    @action(detail=False, methods=['get'])
    def my_subscription(self, request):
        profile = request.user.profile
        serializer = UserProfileSerializer(profile, context={'request': request})
        return APIResponse.success(data=serializer.data)
    
    
    
    