# core/utils/subscription_utils.py
from django.utils import timezone
from django.db.models import Q
from core.models import Exam


def can_access_exam(user_profile, exam: Exam) -> bool:
    """
    Centralized function to check if a user can access a specific exam.
    Returns True if access is granted, False otherwise.
    """
    if exam.is_free:
        return True

    if not user_profile.is_subscribed():
        return False

    # Check if the exam is linked to the user's active subscription tier
    return exam.tiers.filter(
        subscription__user_profile=user_profile,
        subscription__expiry_date__gt=timezone.now(),
        subscription__is_active=True
    ).exists()