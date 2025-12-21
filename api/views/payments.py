# api/views/payments.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.utils import timezone
import logging

from core.authentication import TelegramAuthenticationBackend
from core.models import PaymentMethod, UserProfile
from core.permissions import IsTelegramAuthenticated
from core.services import BundleService
from core.serializers import BundleDefinitionSerializer
from core.serializers import PaymentMethodSerializer, PaymentVerificationSerializer
from payments.verification import PaymentVerifier

logger = logging.getLogger(__name__)


class PaymentMethodViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET /api/v1/payment/
    Returns paywall content: active payment methods, instructions, and required amount
    """
    authentication_classes = [TelegramAuthenticationBackend]
    permission_classes = [AllowAny]
    serializer_class = PaymentMethodSerializer
    queryset = PaymentMethod.objects.filter(is_active=True).order_by('order')
    
    def list(self, request, *args, **kwargs):
        """
        Get all active payment methods with translations
        """
        queryset = self.filter_queryset(self.get_queryset())
        
        # Get language from request
        language = request.query_params.get('lang', 'en')
        
        serializer = self.get_serializer(queryset, many=True)
        
        response_data = {
            'payment_methods': serializer.data,
            'required_amount': 150.00,  # ETB for Pro subscription
            'currency': 'ETB',
            'description': 'Unlock all premium content and offline access'
        }
        
        return Response(response_data)

class PaymentVerificationView(APIView):
    """
    POST /api/v1/payment/verify/
    Handle payment verification for bundle purchase
    """
    authentication_classes = [TelegramAuthenticationBackend]
    permission_classes = [IsAuthenticated, IsTelegramAuthenticated]
    
    def post(self, request):
        serializer = PaymentVerificationSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        reference_number = serializer.validated_data['reference_number']
        payment_method = serializer.validated_data['payment_method']
        sender_last_5_digits = serializer.validated_data.get('sender_last_5_digits')
        
        # Get user profile
        try:
            profile = UserProfile.objects.get(user=request.user)
        except UserProfile.DoesNotExist:
            return Response(
                {'error': 'User profile not found'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Initialize payment verifier
        verifier = PaymentVerifier(mock_mode=True)
        
        try:
            # Verify payment
            result = verifier.verify_payment(payment_method, reference_number)
            
            if not result.success:
                logger.warning(
                    f"Payment verification failed for user {request.user.id}: {result.error}"
                )
                return Response({
                    'success': False,
                    'error': result.error,
                    'message': 'Payment verification failed.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Determine which bundle to purchase based on amount
            # You can add logic here to map amounts to specific bundles
            bundle_definition = self._get_bundle_for_amount(result.amount)
            
            if not bundle_definition:
                return Response({
                    'success': False,
                    'error': f'No bundle found for amount {result.amount}',
                    'message': 'Payment amount does not match any available bundle'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Purchase bundle
            payment_data = {
                'reference_number': reference_number,
                'amount': result.amount,
                'payment_method': PaymentMethod.objects.filter(code=payment_method).first(),
                'auto_complete': True
            }
            
            success, purchase, error = BundleService.purchase_bundle(
                user=request.user,
                bundle_definition_id=bundle_definition.id,
                payment_data=payment_data
            )
            
            if not success:
                return Response({
                    'success': False,
                    'error': error,
                    'message': 'Failed to create bundle'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Update purchase with verification details
            purchase.verified_at = timezone.now()
            purchase.save()
            
            logger.info(f"User {request.user.id} purchased bundle {bundle_definition.name} via {payment_method}")
            
            return Response({
                'success': True,
                'message': f'Bundle "{bundle_definition.name}" purchased successfully!',
                'bundle': BundleDefinitionSerializer(bundle_definition).data,
                'remaining_resources': BundleService.get_user_resources(request.user),
                'verification_details': {
                    'payer_name': result.payer_name,
                    'amount': str(result.amount) if result.amount else None,
                    'reference': result.reference,
                    'date': result.date,
                    'payment_method': payment_method
                }
            })
            
        except Exception as e:
            logger.error(f"Payment verification error for user {request.user.id}: {str(e)}")
            return Response({
                'success': False,
                'error': str(e),
                'message': 'Internal server error during verification'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _get_bundle_for_amount(self, amount):
        """Find appropriate bundle for payment amount"""
        from core.models import BundleDefinition
        # Match bundle by price (you can customize this logic)
        try:
            return BundleDefinition.objects.filter(
                price_etb=amount,
                is_active=True
            ).first()
        except:
            return None
        
        

# class PaymentVerificationView(APIView):
    """
    POST /api/v1/payment/verify/
    Handle submission of transaction reference number for Pro status verification
    """
    authentication_classes = [TelegramAuthenticationBackend]
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = PaymentVerificationSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        reference_number = serializer.validated_data['reference_number']
        payment_method = serializer.validated_data['payment_method']
        sender_last_5_digits = serializer.validated_data.get('sender_last_5_digits')
        
        # Get user profile
        try:
            profile = UserProfile.objects.get(user=request.user)
        except UserProfile.DoesNotExist:
            return Response(
                {'error': 'User profile not found'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if already pro user
        if profile.is_pro_user:
            return Response({
                'success': True,
                'message': 'User is already a Pro member',
                'is_pro_user': True,
                'pro_since': profile.pro_since,
                'pro_expires': profile.pro_expires
            })
        
        # Initialize payment verifier
        # In production: set mock_mode=False
        verifier = PaymentVerifier(mock_mode=True)
        
        try:
            # Verify payment
            result = verifier.verify_payment(payment_method, reference_number)
            
            if not result.success:
                logger.warning(
                    f"Payment verification failed for user {request.user.id}: {result.error}"
                )
                return Response({
                    'success': False,
                    'error': result.error,
                    'message': 'Payment verification failed. Please check the reference number.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if amount is sufficient (150 ETB minimum)
            required_amount = 150.00
            if result.amount and result.amount < required_amount:
                return Response({
                    'success': False,
                    'error': f'Insufficient amount: {result.amount:.2f} ETB. Minimum {required_amount:.2f} ETB required.',
                    'message': 'Payment amount is insufficient'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Upgrade user to pro
            profile.is_pro_user = True
            profile.pro_since = timezone.now()
            profile.pro_expires = timezone.now() + timezone.timedelta(days=365)  # 1 year
            profile.save()
            
            # Generate new cache token for offline access
            profile.generate_new_cache_token()
            
            logger.info(f"User {request.user.id} upgraded to Pro via {payment_method}")
            
            return Response({
                'success': True,
                'message': 'Payment verified successfully! Your account has been upgraded to Pro.',
                'is_pro_user': True,
                'pro_since': profile.pro_since,
                'pro_expires': profile.pro_expires,
                'offline_cache_token': str(profile.offline_cache_token),
                'verification_details': {
                    'payer_name': result.payer_name,
                    'amount': str(result.amount) if result.amount else None,
                    'reference': result.reference,
                    'date': result.date,
                    'payment_method': payment_method
                }
            })
            
        except Exception as e:
            logger.error(f"Payment verification error for user {request.user.id}: {str(e)}")
            return Response({
                'success': False,
                'error': str(e),
                'message': 'Internal server error during verification'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)






















































# from rest_framework import viewsets, status
# from rest_framework.decorators import action
# from rest_framework.response import Response
# from rest_framework.permissions import AllowAny, IsAuthenticated
# from rest_framework.views import APIView
# from django.utils import timezone
# from core.models import PaymentMethod, UserProfile
# from core.serializers import PaymentMethodSerializer, PaymentVerificationSerializer
# from payments.verification import PaymentVerifier
# import logging

# logger = logging.getLogger(__name__)


# class PaymentMethodViewSet(viewsets.ReadOnlyModelViewSet):
#     """
#     ViewSet for listing active payment methods
#     """
#     permission_classes = [AllowAny]
#     serializer_class = PaymentMethodSerializer
#     queryset = PaymentMethod.objects.filter(is_active=True).order_by('order')


# class PaymentVerificationView(APIView):
#     """
#     View for verifying payments and upgrading users to pro
#     """
#     permission_classes = [IsAuthenticated]
    
#     def post(self, request):
#         serializer = PaymentVerificationSerializer(data=request.data)
        
#         if not serializer.is_valid():
#             return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
#         reference_number = serializer.validated_data['reference_number']
#         payment_method = serializer.validated_data['payment_method']
#         sender_last_5_digits = serializer.validated_data.get('sender_last_5_digits')
        
#         # Initialize payment verifier (use mock in development)
#         verifier = PaymentVerifier(mock_mode=True)  # Set to False in production
        
#         try:
#             # Verify payment
#             result = verifier.verify_payment(payment_method, reference_number)
            
#             if not result.success:
#                 logger.warning(f"Payment verification failed for user {request.user.id}: {result.error}")
#                 return Response({
#                     'success': False,
#                     'error': result.error,
#                     'message': 'Payment verification failed'
#                 }, status=status.HTTP_400_BAD_REQUEST)
            
#             # Check if amount is sufficient (150 ETB for premium)
#             if result.amount and result.amount < 150:
#                 return Response({
#                     'success': False,
#                     'error': f'Insufficient amount: {result.amount}. Minimum 100 ETB required.',
#                     'message': 'Payment amount is insufficient'
#                 }, status=status.HTTP_400_BAD_REQUEST)
            
#             # Update user profile to pro
#             profile, created = UserProfile.objects.get_or_create(user=request.user)
            
#             if not profile.is_pro_user:
#                 profile.is_pro_user = True
#                 profile.pro_since = timezone.now()
#                 # Set expiry to 1 year from now
#                 profile.pro_expires = timezone.now() + timezone.timedelta(days=365)
#                 profile.save()
                
#                 logger.info(f"User {request.user.id} upgraded to pro via {payment_method}")
                
#                 return Response({
#                     'success': True,
#                     'message': 'Payment verified successfully! Your account has been upgraded to Pro.',
#                     'is_pro_user': True,
#                     'pro_since': profile.pro_since,
#                     'pro_expires': profile.pro_expires,
#                     'verification_details': {
#                         'payer_name': result.payer_name,
#                         'amount': str(result.amount) if result.amount else None,
#                         'reference': result.reference,
#                         'date': result.date
#                     }
#                 })
#             else:
#                 return Response({
#                     'success': True,
#                     'message': 'Payment verified, but account is already Pro.',
#                     'is_pro_user': True,
#                     'pro_since': profile.pro_since,
#                     'pro_expires': profile.pro_expires
#                 })
                
#         except Exception as e:
#             logger.error(f"Payment verification error for user {request.user.id}: {str(e)}")
#             return Response({
#                 'success': False,
#                 'error': str(e),
#                 'message': 'Internal server error during verification'
#             }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# class SubscriptionStatusView(APIView):
#     """
#     View for checking subscription status
#     """
#     permission_classes = [IsAuthenticated]
    
#     def get(self, request):
#         if not hasattr(request.user, 'profile'):
#             return Response({
#                 'is_pro_user': False,
#                 'message': 'No profile found'
#             })
        
#         profile = request.user.profile
#         is_active = profile.is_pro_user
        
#         # Check if subscription has expired
#         if is_active and profile.pro_expires and profile.pro_expires < timezone.now():
#             profile.is_pro_user = False
#             profile.save()
#             is_active = False
        
#         response_data = {
#             'is_pro_user': is_active,
#             'pro_since': profile.pro_since,
#             'pro_expires': profile.pro_expires,
#             'days_remaining': None
#         }
        
#         if is_active and profile.pro_expires:
#             remaining = (profile.pro_expires - timezone.now()).days
#             response_data['days_remaining'] = max(0, remaining)
        
#         return Response(response_data)
    
    
    