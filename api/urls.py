from rest_framework.routers import DefaultRouter
from core.viewsets.content import ContentViewSet
from core.viewsets.subscription import SubscriptionViewSet
from core.viewsets.payment import PaymentViewSet

router = DefaultRouter()
router.register(r'content', ContentViewSet, basename='content')
router.register(r'subscription', SubscriptionViewSet, basename='subscription')
router.register(r'payment', PaymentViewSet, basename='payment')

urlpatterns = router.urls