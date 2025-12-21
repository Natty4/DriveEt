# core/permissions.py
from rest_framework import permissions
from rest_framework.permissions import BasePermission


class HasActiveBundle(BasePermission):
    """
    Custom permission to only allow users with active bundles.
    """
    
    def has_permission(self, request, view):
        # Check if user is authenticated
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Check if user has active bundle
        return hasattr(request.user, 'profile') and request.user.profile.has_active_bundle


class HasBundleResource(BasePermission):
    """
    Check if user has specific resource in their bundle.
    """
    
    def __init__(self, resource_type):
        self.resource_type = resource_type
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        from core.services import BundleService
        from core.models import ResourceTransaction
        
        can_access, _, _ = BundleService.check_resource_access(
            request.user, self.resource_type
        )
        return can_access
    
    

class IsProUser(BasePermission):
    """
    Custom permission to only allow pro users to access premium content.
    """
    
    def has_permission(self, request, view):
        # Check if user is authenticated
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Check if user has pro status
        return hasattr(request.user, 'profile') and request.user.profile.is_pro_user


class IsOwnerOrProUser(BasePermission):
    """
    Object-level permission to allow users to see their own data or pro users.
    """
    
    def has_object_permission(self, request, view, obj):
        # Pro users can access anything
        if hasattr(request.user, 'profile') and request.user.profile.is_pro_user:
            return True
        
        # Users can only access their own data
        if hasattr(obj, 'user'):
            return obj.user == request.user
        
        return False


class IsProUserForOfflineCache(BasePermission):
    """
    Permission specifically for offline cache/download endpoint.
    Pro users only.
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Must be pro user
        if not hasattr(request.user, 'profile') or not request.user.profile.is_pro_user:
            return False
        
        return True
    

class IsTelegramAuthenticated(BasePermission):
    message = "Telegram authentication required."

    def has_permission(self, request, view):
        auth = request.auth
        user = request.user

        if not auth or not user or not user.is_authenticated:
            return False

        return (
            auth.get("source") == "telegram"
            and auth.get("telegram_id") == getattr(user.profile, "telegram_id", None)
        )

        
        
        