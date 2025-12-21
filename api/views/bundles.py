# api/views/bundles.py

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from django.utils import timezone
import logging

from core.authentication import TelegramAuthenticationBackend
from core.models import BundleDefinition, UserBundle, BundlePurchase, BundleOrder
from core.serializers import (
    BundleDefinitionSerializer, UserBundleSerializer,
    BundlePurchaseSerializer, BundlePurchaseRequestSerializer,
    BundleOrderSerializer, CreateOrderRequestSerializer,
    VerifyPaymentRequestSerializer, AcceptSuggestionRequestSerializer,
    PaymentVerificationResponseSerializer
)
from core.services import BundleService, BundleOrderService
from core.permissions import IsTelegramAuthenticated



logger = logging.getLogger(__name__)


class BundleDefinitionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET /api/v1/bundles/definitions/
    Get available bundle definitions
    """
    permission_classes = [IsAuthenticated]
    serializer_class = BundleDefinitionSerializer
    queryset = BundleDefinition.objects.filter(is_active=True).order_by('order')
    
    def list(self, request, *args, **kwargs):
        """Get bundle definitions with user's current bundle info"""
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        
        # Get user's current bundle status
        bundle_info = BundleService.get_user_resources(request.user)
        
        return Response({
            'bundles': serializer.data,
            'current_bundle': bundle_info
        })


class UserBundleViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET /api/v1/bundles/my/
    Get user's bundles
    """
    permission_classes = [IsAuthenticated]
    serializer_class = UserBundleSerializer
    
    def get_queryset(self):
        return UserBundle.objects.filter(user=self.request.user).order_by('-purchase_date')
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get active bundle"""
        bundle = BundleService.get_active_bundle(request.user)
        if not bundle:
            return Response({
                'has_active_bundle': False,
                'message': 'No active bundle'
            })
        
        serializer = self.get_serializer(bundle)
        return Response({
            'has_active_bundle': True,
            'bundle': serializer.data,
            'remaining_resources': bundle.get_remaining_resources()
        })


class BundlePurchaseViewSet(viewsets.ModelViewSet):
    """
    POST /api/v1/bundles/purchase/
    Purchase a new bundle
    """
    permission_classes = [IsAuthenticated]
    serializer_class = BundlePurchaseSerializer
    
    def get_queryset(self):
        return BundlePurchase.objects.filter(user=self.request.user).order_by('-created_at')
    
    def create(self, request, *args, **kwargs):
        """Purchase a bundle"""
        serializer = BundlePurchaseRequestSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Prepare payment data
        payment_data = {
            'reference_number': serializer.validated_data['reference_number'],
            'transaction_id': serializer.validated_data.get('transaction_id', ''),
            'amount': serializer.validated_data.get('amount'),
            'payment_method': serializer.validated_data.get('payment_method_id'),
            'auto_complete': True  # Auto-complete for demo
        }
        
        # Purchase bundle
        success, purchase, error = BundleService.purchase_bundle(
            user=request.user,
            bundle_definition_id=serializer.validated_data['bundle_definition_id'],
            payment_data=payment_data
        )
        
        if not success:
            return Response({
                'error': error
            }, status=status.HTTP_400_BAD_REQUEST)
        
        purchase_serializer = self.get_serializer(purchase)
        
        return Response({
            'success': True,
            'message': 'Bundle purchased successfully',
            'purchase': purchase_serializer.data,
            'resources': BundleService.get_user_resources(request.user)
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['get'])
    def resources(self, request):
        """Get user's resource status"""
        resources = BundleService.get_user_resources(request.user)
        return Response(resources)
    
    
    


class BundleOrderViewSet(viewsets.ModelViewSet):
    """
    Bundle order management with payment verification flow
    """
    permission_classes = [IsAuthenticated, IsTelegramAuthenticated]
    serializer_class = BundleOrderSerializer
    

    def get_queryset(self):
        return BundleOrder.objects.filter(user=self.request.user).order_by('-created_at')
    
    def create(self, request, *args, **kwargs):
        """
        POST /api/v1/bundles/orders/
        Create a new bundle order (Step 1)
        """
        serializer = CreateOrderRequestSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Create order
        success, order, error = BundleOrderService.create_order(
            user=request.user,
            bundle_definition_id=serializer.validated_data['bundle_definition_id'],
            payment_method_id=serializer.validated_data['payment_method_id']
        )
        
        if not success:
            return Response({
                'error': error
            }, status=status.HTTP_400_BAD_REQUEST)
        
        order_serializer = self.get_serializer(order)
        
        return Response({
            'success': True,
            'message': 'Order created successfully. Please make payment and verify.',
            'order': order_serializer.data,
            'payment_instructions': self._get_payment_instructions(order.payment_method),
            'expires_at': order.expires_at.isoformat()
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['post'])
    def verify_payment(self, request):
        """
        POST /api/v1/bundles/orders/verify_payment/
        Verify payment for an order (Step 2)
        """
        
        serializer = VerifyPaymentRequestSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Verify payment
        result = BundleOrderService.verify_payment(
            order_id=serializer.validated_data['order_id'],
            reference_number=serializer.validated_data['reference_number']
        )
        
        response_serializer = PaymentVerificationResponseSerializer(data=result)
        if response_serializer.is_valid():
            return Response(response_serializer.data)
        else:
            return Response(result, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['post'])
    def accept_suggestion(self, request):
        """
        POST /api/v1/bundles/orders/accept_suggestion/
        Accept a suggested bundle (for insufficient funds)
        """
        serializer = AcceptSuggestionRequestSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Accept suggestion
        result = BundleOrderService.accept_suggestion(
            order_id=serializer.validated_data['order_id'],
            suggested_bundle_id=serializer.validated_data['suggested_bundle_id']
        )
        
        if result['success']:
            return Response({
                'success': True,
                'message': 'Bundle purchased successfully!',
                'bundle': UserBundleSerializer(result['bundle']).data,
                'remaining_resources': result['remaining_resources']
            })
        else:
            return Response({
                'error': result['message']
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def cancel(self, request):
        """
        POST /api/v1/bundles/orders/cancel/
        Cancel a pending order
        """
        order_id = request.data.get('order_id')
        if not order_id:
            return Response({
                'error': 'order_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        result = BundleOrderService.cancel_order(order_id)
        
        if result['success']:
            return Response({
                'success': True,
                'message': result['message']
            })
        else:
            return Response({
                'error': result['message']
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """
        GET /api/v1/bundles/orders/active/
        Get user's active orders
        """
        active_orders = self.get_queryset().filter(
            status__in=[
                BundleOrder.OrderStatus.PENDING,
                BundleOrder.OrderStatus.PAYMENT_VERIFIED,
                BundleOrder.OrderStatus.INSUFFICIENT_FUNDS
            ]
        )
        
        serializer = self.get_serializer(active_orders, many=True)
        
        return Response({
            'active_orders': serializer.data,
            'count': active_orders.count()
        })
    
    def _get_payment_instructions(self, payment_method):
        """Get payment instructions for the payment method"""
        # Get instructions in user's preferred language
        language = self.request.user.profile.preferred_language
        
        translation = payment_method.translations.filter(language=language).first()
        if not translation and language != 'en':
            translation = payment_method.translations.filter(language='en').first()
        
        if translation:
            return {
                'account_details': translation.account_details,
                'instruction': translation.instruction,
                'amount': float(payment_method.amount) if payment_method.amount else None
            }
        
        return {
            'account_details': '',
            'instruction': 'Please make payment using the selected method'
        }


class BundlePurchaseFlowView(APIView):
    """
    Complete bundle purchase flow API
    Combines all steps in one endpoint for simplicity
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        POST /api/v1/bundles/purchase-flow/
        Complete purchase flow in one call
        
        Flow:
        1. Create order
        2. Verify payment
        3. Handle insufficient funds with suggestions
        """
        step = request.data.get('step', 'create_order')
        
        if step == 'create_order':
            # Step 1: Create order
            return self._create_order(request)
        elif step == 'verify_payment':
            # Step 2: Verify payment
            return self._verify_payment(request)
        elif step == 'accept_suggestion':
            # Step 3: Accept suggestion (if insufficient funds)
            return self._accept_suggestion(request)
        else:
            return Response({
                'error': 'Invalid step'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    def _create_order(self, request):
        """Step 1: Create order"""
        serializer = CreateOrderRequestSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        success, order, error = BundleOrderService.create_order(
            user=request.user,
            bundle_definition_id=serializer.validated_data['bundle_definition_id'],
            payment_method_id=serializer.validated_data['payment_method_id']
        )
        
        if not success:
            return Response({
                'error': error
            }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({
            'step': 'payment_pending',
            'success': True,
            'order_id': str(order.id),
            'message': 'Order created. Please make payment and return to verify.',
            'payment_details': {
                'amount': float(order.order_amount),
                'payment_method': order.payment_method.name,
                'account_details': self._get_account_details(order.payment_method),
                'instructions': self._get_instructions(order.payment_method),
                'reference_hint': 'Use your phone number or a unique number as reference'
            },
            'expires_in': '24 hours'
        })
    
    def _verify_payment(self, request):
        """Step 2: Verify payment"""
        serializer = VerifyPaymentRequestSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        result = BundleOrderService.verify_payment(
            order_id=serializer.validated_data['order_id'],
            reference_number=serializer.validated_data['reference_number']
        )
        
        if result['status'] == 'completed':
            # Payment successful, bundle activated
            return Response({
                'step': 'completed',
                'success': True,
                'message': result['message'],
                'bundle': UserBundleSerializer(result['bundle']).data,
                'remaining_resources': result['remaining_resources']
            })
        elif result['status'] == 'insufficient_funds':
            # Insufficient funds, show suggestions
            return Response({
                'step': 'insufficient_funds',
                'success': False,
                'message': result['message'],
                'verified_amount': float(result['verified_amount']),
                'required_amount': float(result['required_amount']),
                'deficit': float(result['deficit']),
                'suggestions': [
                    {
                        'bundle_id': str(suggestion['bundle'].id),
                        'bundle_name': suggestion['bundle'].name,
                        'price': float(suggestion['bundle'].price_etb),
                        'reason': suggestion['reason'],
                        'remaining_budget': float(suggestion.get('remaining_budget', 0)),
                        'deficit': float(suggestion.get('deficit', 0))
                    }
                    for suggestion in result['suggestions']
                ],
                'can_upgrade_existing': result.get('can_upgrade_existing')
            })
        else:
            # Other errors
            return Response({
                'step': 'error',
                'success': False,
                'message': result['message']
            })
    
    def _accept_suggestion(self, request):
        """Step 3: Accept suggestion"""
        serializer = AcceptSuggestionRequestSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        result = BundleOrderService.accept_suggestion(
            order_id=serializer.validated_data['order_id'],
            suggested_bundle_id=serializer.validated_data['suggested_bundle_id']
        )
        
        if result['success']:
            return Response({
                'step': 'completed',
                'success': True,
                'message': 'Bundle purchased successfully!',
                'bundle': UserBundleSerializer(result['bundle']).data,
                'remaining_resources': result['remaining_resources']
            })
        else:
            return Response({
                'step': 'error',
                'success': False,
                'message': result['message']
            })
    
    def _get_account_details(self, payment_method):
        """Get account details for payment method"""
        language = self.request.user.profile.preferred_language
        translation = payment_method.translations.filter(language=language).first()
        if not translation and language != 'en':
            translation = payment_method.translations.filter(language='en').first()
        return translation.account_details if translation else ''
    
    def _get_instructions(self, payment_method):
        """Get instructions for payment method"""
        language = self.request.user.profile.preferred_language
        translation = payment_method.translations.filter(language=language).first()
        if not translation and language != 'en':
            translation = payment_method.translations.filter(language='en').first()
        return translation.instruction if translation else ''