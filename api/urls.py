# api/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    search, payments, questions, auth, main,
    exam, articles, ai_chat, bundles
)

# Routers

# Bundle routers
bundle_router = DefaultRouter()
bundle_router.register(r'definitions', bundles.BundleDefinitionViewSet, basename='bundle-definition')
bundle_router.register(r'my', bundles.UserBundleViewSet, basename='user-bundle')
bundle_router.register(r'purchase', bundles.BundlePurchaseViewSet, basename='bundle-purchase')

# Order router
order_router = DefaultRouter()
order_router.register(r'orders', bundles.BundleOrderViewSet, basename='bundle-order')
  

question_router = DefaultRouter()
question_router.register(r'', questions.QuestionViewSet, basename='question')

payment_router = DefaultRouter()
payment_router.register(r'methods', payments.PaymentMethodViewSet, basename='payment-method')


article_category_router = DefaultRouter()
article_category_router.register(r'', articles.ArticleCategoryViewSet, basename='article-category')

article_router = DefaultRouter()
article_router.register(r'', articles.ArticleViewSet, basename='article')

exam_router = DefaultRouter()
exam_router.register(r'', exam.ExamViewSet, basename='exam')

urlpatterns = [
    # Landing
    path('meta/', main.LandingView.as_view(), name='landing-home'),
    
    # Authentication endpoints
    path("auth/telegram/login/", auth.TelegramLoginView.as_view(), name="telegram-login"),
    path("auth/token/refresh/", auth.TelegramTokenRefreshView.as_view(), name="token-refresh"),
    path("auth/me/", auth.MeView.as_view(), name="auth-me"),
    
    # Bundle endpoints
    path('bundles/', include(bundle_router.urls)),
    path('bundles/', include(order_router.urls)),
    path('bundles/resources/', bundles.BundlePurchaseViewSet.as_view({'get': 'resources'}), name='bundle-resources'),
    # Complete purchase flow
    path('bundles/purchase-flow/', bundles.BundlePurchaseFlowView.as_view(), name='bundle-purchase-flow'),
    
    
    # Questions endpoints
    path('questions/', include(question_router.urls)),
    path('questions/all/', questions.AllDataView.as_view(), name='all-data'),
    path('questions/all/refresh_token/', questions.RefreshCacheTokenView.as_view(), name='refresh-cache-token'),
    path('questions/metadata/', questions.QuestionViewSet.as_view({'get': 'metadata'}), name='questions-metadata'),

    # Payment endpoints
    path('payment/', include(payment_router.urls)),
    path('payment/verify/', payments.PaymentVerificationView.as_view(), name='payment-verify'),


    # Exam endpoints
    path('exam/', include(exam_router.urls)),
    path('exam/start_exam/', exam.ExamViewSet.as_view({'post': 'start_exam'}), name='start-exam'),

    # Articles endpoints
    path('articles/categories/', include(article_category_router.urls)),
    path('articles/', include(article_router.urls)),

    # AI Chat endpoints
    path('ai/chat/', ai_chat.AIChatView.as_view(), name='ai-chat'),

    # Search endpoint
    path('search/', search.SearchView.as_view(), name='search'),
    
    # Admin endpoints (for Telegram bot admin)
    # path('admin/stats/', main.AdminStatsView.as_view(), name='admin-stats'),
]

