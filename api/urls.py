# api/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from core.viewsets.content import ContentViewSet
from core.viewsets.subscription import SubscriptionViewSet
from core.viewsets.payment import PaymentViewSet
from core.viewsets.auth import TelegramLoginView

router = DefaultRouter()
router.register(r'content', ContentViewSet, basename='content')
router.register(r'subscription', SubscriptionViewSet, basename='subscription')
router.register(r'payment', PaymentViewSet, basename='payment')

urlpatterns = [
    path('auth/telegram-login/', TelegramLoginView.as_view(), name='telegram-login'),
    path('', include(router.urls)),
]