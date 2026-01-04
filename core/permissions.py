# core/permissions.py

from rest_framework.permissions import BasePermission
from django.utils import timezone

class IsTelegramAuthenticated(BasePermission):
    def has_permission(self, request, view):
        auth = request.auth
        user = request.user
        if not auth or not user or not user.is_authenticated:
            return False
        return (
            auth.get("source") == "telegram"
            and auth.get("tg_id") == getattr(user.profile.tg_id, None, None)
        )


class HasActiveSubscription(BasePermission):
    message = "Active subscription required."

    def has_permission(self, request, view):
        profile = request.user.profile
        return profile.is_subscribed()


class CanAccessFullRoadSignQuiz(BasePermission):
    message = "Full road sign quiz access requires a paid subscription."

    def has_permission(self, request, view):
        profile = request.user.profile
        if not profile.is_subscribed():
            return False
        return profile.active_subscription.tier.full_road_sign_quiz
    
    
    