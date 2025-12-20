# api/views/articles.py
from rest_framework import viewsets, filters
from rest_framework.permissions import AllowAny, IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
import logging

from core.models import Article, ArticleCategory, AIChatHistory, UserProfile
from core.serializers import ArticleSerializer, ArticleCategorySerializer
from core.authentication import TelegramAuthenticationBackend
from core.permissions import IsProUser

logger = logging.getLogger(__name__)


class ArticleCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Article categories
    """
    authentication_classes = [TelegramAuthenticationBackend]
    permission_classes = [AllowAny]
    serializer_class = ArticleCategorySerializer
    queryset = ArticleCategory.objects.filter(is_active=True).order_by('order')
    
    def get_queryset(self):
        queryset = super().get_queryset()
        # For non-pro users, only show categories with free articles
        if self.request.user.is_authenticated and not self.request.user.profile.is_pro_user:
            # Get categories that have at least one free article
            categories_with_free = Article.objects.filter(
                is_premium=False
            ).values_list('category_id', flat=True).distinct()
            queryset = queryset.filter(id__in=categories_with_free)
        return queryset


class ArticleViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Articles and legal documents
    """
    authentication_classes = [TelegramAuthenticationBackend]
    permission_classes = [AllowAny]  # Changed to check in get_queryset
    serializer_class = ArticleSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['title', 'content', 'tags']
    filterset_fields = ['category', 'is_premium']
    
    def get_queryset(self):
        queryset = Article.objects.filter(is_premium=False).order_by('order', '-created_at')
        
        # Check if user is authenticated and pro
        user = self.request.user
        if user.is_authenticated:
            try:
                if user.profile.is_pro_user:
                    # Pro users can see all articles
                    queryset = Article.objects.all().order_by('order', '-created_at')
            except UserProfile.DoesNotExist:
                pass
        
        # Filter by category if provided
        category_slug = self.request.query_params.get('category')
        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)
        
        return queryset
    
    def retrieve(self, request, *args, **kwargs):
        """Get article and increment views"""
        instance = self.get_object()
        
        # Check if premium article for non-pro users
        if instance.is_premium and not request.user.profile.is_pro_user:
            return Response({
                'error': 'Premium content requires Pro subscription'
            }, status=403)
        
        # Increment views
        instance.views += 1
        instance.save(update_fields=['views'])
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

