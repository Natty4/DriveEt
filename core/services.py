# core/services.py

from django.db import transaction
from django.db.models import F
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from django.core.cache import cache
import logging
from datetime import timedelta
from decimal import Decimal

from core.models import (
    UserBundle, ResourceTransaction, BundleDefinition,
    BundlePurchase, UserProfile, BundleOrder, OrderBundleSuggestion,
    PaymentMethod,
)

logger = logging.getLogger(__name__)


class BundleService:
    """Service for managing prepaid bundles and resource consumption"""
    
    @staticmethod
    def get_active_bundle(user):
        """Get user's active bundle"""
        try:
            profile = user.profile
            if profile.active_bundle and profile.has_active_bundle:
                return profile.active_bundle
        except UserProfile.DoesNotExist:
            pass
        return None
    
    @staticmethod
    def consume_resource(user, resource_type, quantity=1, description=""):
        """
        Consume a resource from user's active bundle
        Uses atomic updates to prevent race conditions
        
        Args:
            user: User object
            resource_type: 'exam', 'chat', 'search', 'road_sign'
            quantity: Number of units to consume (default: 1)
            description: Optional description for audit
        
        Returns:
            tuple: (success: bool, bundle: UserBundle or None, error_message: str)
        """
        from core.models import ResourceTransaction
        
        # Get active bundle
        bundle = BundleService.get_active_bundle(user)
        if not bundle:
            return False, None, "No active bundle found"
        
        # Check if resource type is valid for the bundle
        if resource_type == ResourceTransaction.ResourceType.EXAM:
            if not bundle.can_use_exam:
                return False, bundle, "Exam quota exhausted or bundle expired"
            if not bundle.bundle_definition.is_unlimited_exams and bundle.exams_remaining < quantity:
                return False, bundle, f"Insufficient exam attempts. Remaining: {bundle.exams_remaining}"
        
        elif resource_type == ResourceTransaction.ResourceType.CHAT:
            if not bundle.can_use_chat:
                return False, bundle, "Chat quota exhausted or daily limit reached"
            if not bundle.bundle_definition.is_unlimited_chats and bundle.chats_remaining < quantity:
                return False, bundle, f"Insufficient chat messages. Remaining: {bundle.chats_remaining}"
        
        elif resource_type == ResourceTransaction.ResourceType.SEARCH:
            if not bundle.can_use_search:
                return False, bundle, "Search quota exhausted or bundle expired"
            if not bundle.bundle_definition.is_unlimited_search and bundle.search_remaining < quantity:
                return False, bundle, f"Insufficient search quota. Remaining: {bundle.search_remaining}"
        
        elif resource_type == ResourceTransaction.ResourceType.ROAD_SIGN:
            if not bundle.has_unlimited_road_sign_quiz:
                return False, bundle, "Road sign quiz not included in bundle"
            # Unlimited resource - no consumption needed
            return True, bundle, ""
        
        else:
            return False, bundle, f"Invalid resource type: {resource_type}"
        
        # Perform atomic update
        try:
            with transaction.atomic():
                # Lock the bundle row for update
                bundle = UserBundle.objects.select_for_update().get(pk=bundle.pk)
                
                # Get current balances for audit
                exams_before = bundle.exams_remaining
                chats_before = bundle.chats_remaining
                search_before = bundle.search_remaining
                daily_chats_before = bundle.daily_chats_used
                total_chats_before = bundle.total_chats_consumed
                
                # Update balances based on resource type
                if resource_type == ResourceTransaction.ResourceType.EXAM:
                    if not bundle.bundle_definition.is_unlimited_exams:
                        bundle.exams_remaining = F('exams_remaining') - quantity
                
                elif resource_type == ResourceTransaction.ResourceType.CHAT:
                    if not bundle.bundle_definition.is_unlimited_chats:
                        bundle.chats_remaining = F('chats_remaining') - quantity
                    bundle.total_chats_consumed = F('total_chats_consumed') + quantity
                    bundle.daily_chats_used = F('daily_chats_used') + quantity
                
                elif resource_type == ResourceTransaction.ResourceType.SEARCH:
                    if not bundle.bundle_definition.is_unlimited_search:
                        bundle.search_remaining = F('search_remaining') - quantity
                
                # Save bundle with updated balances
                bundle.save(update_fields=[
                    'exams_remaining', 'chats_remaining', 'search_remaining',
                    'total_chats_consumed', 'daily_chats_used', 'updated_at'
                ])
                
                # Refresh bundle to get updated values
                bundle.refresh_from_db()
                
                # Create transaction record
                ResourceTransaction.objects.create(
                    user=user,
                    user_bundle=bundle,
                    transaction_type=ResourceTransaction.TransactionType.CONSUME,
                    resource_type=resource_type,
                    quantity=-quantity,  # Negative for consumption
                    exams_before=exams_before,
                    exams_after=bundle.exams_remaining,
                    chats_before=chats_before,
                    chats_after=bundle.chats_remaining,
                    search_before=search_before,
                    search_after=bundle.search_remaining,
                    description=description,
                    ip_address=BundleService.get_client_ip(),
                    user_agent=BundleService.get_user_agent()
                )
                
                logger.info(f"Resource consumed: user={user.id}, type={resource_type}, quantity={quantity}")
                return True, bundle, ""
                
        except Exception as e:
            logger.error(f"Error consuming resource: {str(e)}")
            return False, None, f"Internal error: {str(e)}"
    
    @staticmethod
    def check_resource_access(user, resource_type):
        """
        Check if user can access a resource without consuming it
        
        Returns:
            tuple: (can_access: bool, bundle: UserBundle or None, error_message: str)
        """
        bundle = BundleService.get_active_bundle(user)
        if not bundle:
            return False, None, "No active bundle"
        
        if resource_type == ResourceTransaction.ResourceType.EXAM:
            if not bundle.can_use_exam:
                return False, bundle, "Exam quota exhausted or bundle expired"
        
        elif resource_type == ResourceTransaction.ResourceType.CHAT:
            if not bundle.can_use_chat:
                return False, bundle, "Chat quota exhausted or daily limit reached"
        
        elif resource_type == ResourceTransaction.ResourceType.SEARCH:
            if not bundle.can_use_search:
                return False, bundle, "Search quota exhausted or bundle expired"
        
        elif resource_type == ResourceTransaction.ResourceType.ROAD_SIGN:
            if not bundle.has_unlimited_road_sign_quiz:
                return False, bundle, "Road sign quiz not included in bundle"
        
        else:
            return False, bundle, f"Invalid resource type: {resource_type}"
        
        return True, bundle, ""
    
    @staticmethod
    def purchase_bundle(user, bundle_definition_id, payment_data):
        """
        Purchase a new bundle
        
        Returns:
            tuple: (success: bool, purchase: BundlePurchase or None, error_message: str)
        """
        try:
            bundle_definition = BundleDefinition.objects.get(
                id=bundle_definition_id,
                is_active=True
            )
            
            with transaction.atomic():
                # Create purchase record
                purchase = BundlePurchase.objects.create(
                    user=user,
                    bundle_definition=bundle_definition,
                    amount_paid=payment_data.get('amount', bundle_definition.price_etb),
                    payment_method=payment_data.get('payment_method'),
                    reference_number=payment_data.get('reference_number', ''),
                    transaction_id=payment_data.get('transaction_id', ''),
                    payment_status=BundlePurchase.PaymentStatus.PENDING,
                    ip_address=BundleService.get_client_ip(),
                    user_agent=BundleService.get_user_agent()
                )
                
                # In production, this would wait for payment verification
                # For now, auto-complete if amount matches
                if payment_data.get('auto_complete', True):
                    purchase.payment_status = BundlePurchase.PaymentStatus.COMPLETED
                    purchase.verified_at = timezone.now()
                    purchase.save()
                    
                    # Create user bundle
                    user_bundle = purchase.create_user_bundle()
                    
                    # Activate the bundle for user
                    profile = user.profile
                    profile.activate_bundle(user_bundle)
                    
                    # Create transaction record for purchase
                    ResourceTransaction.objects.create(
                        user=user,
                        user_bundle=user_bundle,
                        transaction_type=ResourceTransaction.TransactionType.PURCHASE,
                        resource_type=None,
                        quantity=bundle_definition.exam_quota,
                        exams_before=0,
                        exams_after=user_bundle.exams_remaining,
                        chats_before=0,
                        chats_after=user_bundle.chats_remaining,
                        search_before=0,
                        search_after=user_bundle.search_remaining,
                        description=f"Purchased {bundle_definition.name}",
                        ip_address=purchase.ip_address,
                        user_agent=purchase.user_agent
                    )
                
                return True, purchase, ""
                
        except BundleDefinition.DoesNotExist:
            return False, None, "Bundle definition not found"
        except Exception as e:
            logger.error(f"Error purchasing bundle: {str(e)}")
            return False, None, f"Internal error: {str(e)}"
    
    @staticmethod
    def get_user_resources(user):
        """Get user's resource status"""
        bundle = BundleService.get_active_bundle(user)
        if not bundle:
            return {
                'has_active_bundle': False,
                'message': 'No active bundle'
            }
        
        resources = bundle.get_remaining_resources()
        resources['bundle_name'] = bundle.bundle_definition.name
        resources['bundle_code'] = bundle.bundle_definition.code
        resources['has_unlimited_road_sign_quiz'] = bundle.has_unlimited_road_sign_quiz
        
        return resources
    
    @staticmethod
    def reset_daily_chats():
        """Reset daily chat counters for all bundles (cron job)"""
        from django.db import connection
        from django.utils import timezone
        
        try:
            with transaction.atomic():
                now = timezone.now()
                updated = UserBundle.objects.filter(
                    is_active=True,
                    last_chat_reset__lt=now.replace(hour=0, minute=0, second=0, microsecond=0)
                ).update(
                    daily_chats_used=0,
                    last_chat_reset=now
                )
                
                # Create reset transactions
                reset_bundles = UserBundle.objects.filter(
                    is_active=True,
                    daily_chats_used=0,
                    last_chat_reset=now
                )
                
                for bundle in reset_bundles:
                    ResourceTransaction.objects.create(
                        user=bundle.user,
                        user_bundle=bundle,
                        transaction_type=ResourceTransaction.TransactionType.RESET,
                        resource_type=ResourceTransaction.ResourceType.CHAT,
                        quantity=0,
                        description="Daily chat reset",
                        ip_address="system",
                        user_agent="cron"
                    )
                
                logger.info(f"Reset daily chats for {updated} bundles")
                return updated
                
        except Exception as e:
            logger.error(f"Error resetting daily chats: {str(e)}")
            return 0
    
    @staticmethod
    def expire_bundles():
        """Expire bundles that have passed expiry date (cron job)"""
        from django.utils import timezone
        
        try:
            with transaction.atomic():
                now = timezone.now()
                expired_bundles = UserBundle.objects.filter(
                    is_active=True,
                    expiry_date__lt=now
                )
                
                expired_count = expired_bundles.count()
                
                for bundle in expired_bundles:
                    bundle.is_active = False
                    bundle.save(update_fields=['is_active', 'updated_at'])
                    
                    # Create expiry transaction
                    ResourceTransaction.objects.create(
                        user=bundle.user,
                        user_bundle=bundle,
                        transaction_type=ResourceTransaction.TransactionType.EXPIRY,
                        resource_type=None,
                        quantity=0,
                        description="Bundle expired",
                        ip_address="system",
                        user_agent="cron"
                    )
                    
                    # Clear active bundle from user profile
                    try:
                        profile = bundle.user.profile
                        if profile.active_bundle == bundle:
                            profile.active_bundle = None
                            profile.save(update_fields=['active_bundle', 'updated_at'])
                    except UserProfile.DoesNotExist:
                        pass
                
                logger.info(f"Expired {expired_count} bundles")
                return expired_count
                
        except Exception as e:
            logger.error(f"Error expiring bundles: {str(e)}")
            return 0
    
    @staticmethod
    def get_client_ip():
        """Get client IP address from request context"""
        import inspect
        for frame_record in inspect.stack():
            frame = frame_record[0]
            request = frame.f_locals.get('request')
            if request:
                x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
                if x_forwarded_for:
                    return x_forwarded_for.split(',')[0]
                return request.META.get('REMOTE_ADDR', '')
        return ''
    
    @staticmethod
    def get_user_agent():
        """Get user agent from request context"""
        import inspect
        for frame_record in inspect.stack():
            frame = frame_record[0]
            request = frame.f_locals.get('request')
            if request:
                return request.META.get('HTTP_USER_AGENT', '')
        return ''


class BundleOrderService:
    """Service for managing bundle purchase orders"""
    
    @staticmethod
    def create_order(user, bundle_definition_id, payment_method_id):
        """
        Create a new order for bundle purchase
        
        Returns:
            tuple: (success: bool, order: BundleOrder or None, error_message: str)
        """
        try:
            bundle_definition = BundleDefinition.objects.get(
                id=bundle_definition_id,
                is_active=True
            )
            
            payment_method = PaymentMethod.objects.get(
                id=payment_method_id,
                is_active=True
            )
            
            with transaction.atomic():
                order = BundleOrder.objects.create(
                    user=user,
                    bundle_definition=bundle_definition,
                    order_amount=bundle_definition.price_etb,
                    payment_method=payment_method,
                    ip_address=BundleService.get_client_ip(),
                    user_agent=BundleService.get_user_agent()
                )
                
                logger.info(f"Created order {order.id} for user {user.id}")
                return True, order, ""
                
        except BundleDefinition.DoesNotExist:
            return False, None, "Bundle definition not found or inactive"
        except PaymentMethod.DoesNotExist:
            return False, None, "Payment method not found or inactive"
        except Exception as e:
            logger.error(f"Error creating order: {str(e)}")
            return False, None, f"Internal error: {str(e)}"
    
    @staticmethod
    def verify_payment(order_id, reference_number):
        """
        Verify payment for an order and process accordingly
        
        Returns:
            dict: Result with status, suggestions, etc.
        """
        try:
            order = BundleOrder.objects.get(
                id=order_id,
                status=BundleOrder.OrderStatus.PENDING
            )
            
            if order.is_expired:
                order.status = BundleOrder.OrderStatus.EXPIRED
                order.save()
                return {
                    'success': False,
                    'status': 'expired',
                    'message': 'Order has expired. Please create a new order.'
                }
            
            # Verify payment using PaymentVerifier
            from payments.verification import PaymentVerifier
            verifier = PaymentVerifier(mock_mode=True)
            
            payment_method_code = order.payment_method.code
            result = verifier.verify_payment(payment_method_code, reference_number)
            
            if not result.success:
                return {
                    'success': False,
                    'status': 'verification_failed',
                    'message': result.error or 'Payment verification failed'
                }
            
            # Update order with verified amount
            order.reference_number = reference_number
            order.verified_amount = result.amount
            order.verified_at = result.date or timezone.now()
            
            # Check if amount is sufficient
            if result.amount >= order.order_amount:
                order.status = BundleOrder.OrderStatus.PAYMENT_VERIFIED
                order.save()
                
                # Complete the order (create bundle)
                completion_result = BundleOrderService.complete_order(order.id)
                
                return {
                    'success': True,
                    'status': 'completed',
                    'message': 'Payment verified and bundle activated!',
                    'order': order,
                    'bundle': completion_result.get('bundle'),
                    'remaining_resources': completion_result.get('remaining_resources')
                }
            else:
                # Insufficient funds - suggest alternatives
                order.status = BundleOrder.OrderStatus.INSUFFICIENT_FUNDS
                order.save()
                
                # Get budget-friendly suggestions
                suggestions = BundleOrderService.get_budget_suggestions(
                    budget=result.amount,
                    current_bundle=order.bundle_definition
                )
                
                # Save suggestions to order
                for suggestion in suggestions:
                    OrderBundleSuggestion.objects.create(
                        order=order,
                        bundle_definition=suggestion['bundle'],
                        reason=suggestion['reason'],
                        order_score=suggestion['score']
                    )
                
                return {
                    'success': False,
                    'status': 'insufficient_funds',
                    'message': f'Payment verified but amount ({result.amount} ETB) is insufficient for {order.bundle_definition.name} ({order.order_amount} ETB)',
                    'verified_amount': result.amount,
                    'required_amount': order.order_amount,
                    'deficit': order.order_amount - result.amount,
                    'suggestions': suggestions,
                    'can_upgrade_existing': BundleOrderService.can_upgrade_existing_bundle(
                        user=order.user,
                        additional_amount=result.amount
                    )
                }
                
        except BundleOrder.DoesNotExist:
            return {
                'success': False,
                'status': 'not_found',
                'message': 'Order not found or already processed'
            }
        except Exception as e:
            logger.error(f"Error verifying payment: {str(e)}")
            return {
                'success': False,
                'status': 'error',
                'message': f'Internal error: {str(e)}'
            }
    
    @staticmethod
    def complete_order(order_id):
        """
        Complete an order by creating the bundle
        
        Returns:
            dict: Result with bundle and resources
        """
        try:
            order = BundleOrder.objects.get(
                id=order_id,
                status=BundleOrder.OrderStatus.PAYMENT_VERIFIED
            )
            
            with transaction.atomic():
                # Create user bundle
                user_bundle = UserBundle.objects.create(
                    user=order.user,
                    bundle_definition=order.bundle_definition,
                    expiry_date = timezone.now() + timedelta(days=order.bundle_definition.validity_days)
                )
                
                # Update order
                order.resulting_bundle = user_bundle
                order.status = BundleOrder.OrderStatus.COMPLETED
                order.save()
                
                # Activate bundle for user
                profile = order.user.profile
                profile.activate_bundle(user_bundle)
                
                # Create final purchase record
                BundlePurchase.objects.create(
                    user=order.user,
                    bundle_definition=order.bundle_definition,
                    amount_paid=order.verified_amount,
                    payment_method=order.payment_method,
                    reference_number=order.reference_number,
                    payment_status=BundlePurchase.PaymentStatus.COMPLETED,
                    user_bundle=user_bundle,
                    verified_at=order.verified_at,
                    order=order,
                    ip_address=order.ip_address,
                    user_agent=order.user_agent
                )
                
                # Create resource transaction
                ResourceTransaction.objects.create(
                    user=order.user,
                    user_bundle=user_bundle,
                    transaction_type=ResourceTransaction.TransactionType.PURCHASE,
                    resource_type=None,
                    quantity=order.bundle_definition.exam_quota,
                    exams_before=0,
                    exams_after=user_bundle.exams_remaining,
                    chats_before=0,
                    chats_after=user_bundle.chats_remaining,
                    search_before=0,
                    search_after=user_bundle.search_remaining,
                    description=f"Purchased {order.bundle_definition.name} via order",
                    ip_address=order.ip_address,
                    user_agent=order.user_agent
                )
                
                logger.info(f"Completed order {order.id}, created bundle {user_bundle.id}")
                
                return {
                    'success': True,
                    'bundle': user_bundle,
                    'remaining_resources': user_bundle.get_remaining_resources()
                }
                
        except Exception as e:
            logger.error(f"Error completing order: {str(e)}")
            raise
    
    @staticmethod
    def get_budget_suggestions(budget, current_bundle=None):
        """
        Get bundle suggestions within budget
        
        Returns:
            list: Suggested bundles with reasons and scores
        """
        suggestions = []
        
        # Get all active bundles within budget
        affordable_bundles = BundleDefinition.objects.filter(
            is_active=True,
            price_etb__lte=budget
        ).order_by('-price_etb')
        
        if not affordable_bundles.exists():
            # No bundles within budget, suggest cheapest
            cheapest = BundleDefinition.objects.filter(
                is_active=True
            ).order_by('price_etb').first()
            
            if cheapest:
                deficit = cheapest.price_etb - budget
                suggestions.append({
                    'bundle': cheapest,
                    'reason': f'Cheapest available bundle. Need additional {deficit} ETB',
                    'score': 0.5,
                    'deficit': deficit
                })
            
            return suggestions
        
        for bundle in affordable_bundles:
            score = 0.0
            reason = ""
            
            # Score based on value for money
            value_score = (bundle.exam_quota + bundle.total_chat_quota + bundle.search_quota) / float(bundle.price_etb)
            score += value_score * 0.4
            
            # Bonus if it's similar to requested bundle
            if current_bundle and bundle.id == current_bundle.id:
                score += 0.3  # Highest priority for exact match
            
            # Bonus for bundles close to budget
            budget_utilization = float(bundle.price_etb) / float(budget)
            if 0.8 <= budget_utilization <= 1.0:
                score += 0.2
                reason = "Good budget utilization"
            elif budget_utilization > 1.0:
                reason = "Slightly over budget"
            else:
                reason = f"Within budget (saves {budget - bundle.price_etb} ETB)"
            
            # Bonus for popular bundles (could use purchase count in future)
            if bundle.order >= 50:
                score += 0.1
            
            suggestions.append({
                'bundle': bundle,
                'reason': reason,
                'score': score,
                'remaining_budget': budget - bundle.price_etb
            })
        
        # Sort by score
        suggestions.sort(key=lambda x: x['score'], reverse=True)
        return suggestions[:3]  # Return top 3 suggestions
    
    @staticmethod
    def can_upgrade_existing_bundle(user, additional_amount):
        """
        Check if user can upgrade existing bundle with additional amount
        """
        try:
            profile = user.profile
            if not profile.active_bundle or profile.active_bundle.is_expired:
                return False
            
            current_bundle = profile.active_bundle.bundle_definition
            
            # Find upgrade options (more expensive bundles)
            upgrade_bundles = BundleDefinition.objects.filter(
                is_active=True,
                price_etb__lte=current_bundle.price_etb + additional_amount,
                price_etb__gt=current_bundle.price_etb
            ).order_by('price_etb')
            
            return {
                'can_upgrade': upgrade_bundles.exists(),
                'current_bundle': current_bundle,
                'upgrade_options': upgrade_bundles[:3],
                'additional_needed': None if upgrade_bundles.exists() else 
                    (upgrade_bundles.first().price_etb - current_bundle.price_etb - additional_amount)
            }
        except:
            return False
    
    @staticmethod
    def accept_suggestion(order_id, suggested_bundle_id):
        """
        Accept a suggested bundle and update order
        """
        try:
            order = BundleOrder.objects.get(id=order_id)
            suggested_bundle = BundleDefinition.objects.get(id=suggested_bundle_id)
            
            # Verify the suggestion exists for this order
            suggestion = OrderBundleSuggestion.objects.get(
                order=order,
                bundle_definition=suggested_bundle
            )
            
            with transaction.atomic():
                # Update order with new bundle
                order.bundle_definition = suggested_bundle
                order.order_amount = suggested_bundle.price_etb
                order.status = BundleOrder.OrderStatus.PAYMENT_VERIFIED
                order.save()
                
                # Complete the order
                return BundleOrderService.complete_order(order.id)
                
        except (BundleOrder.DoesNotExist, BundleDefinition.DoesNotExist, 
                OrderBundleSuggestion.DoesNotExist) as e:
            return {
                'success': False,
                'message': 'Invalid suggestion or order'
            }
        except Exception as e:
            logger.error(f"Error accepting suggestion: {str(e)}")
            return {
                'success': False,
                'message': f'Internal error: {str(e)}'
            }
    
    @staticmethod
    def cancel_order(order_id):
        """Cancel a pending order"""
        try:
            order = BundleOrder.objects.get(
                id=order_id,
                status__in=[BundleOrder.OrderStatus.PENDING, BundleOrder.OrderStatus.INSUFFICIENT_FUNDS]
            )
            
            order.status = BundleOrder.OrderStatus.CANCELLED
            order.save()
            
            return {
                'success': True,
                'message': 'Order cancelled successfully'
            }
        except BundleOrder.DoesNotExist:
            return {
                'success': False,
                'message': 'Order not found or cannot be cancelled'
            }