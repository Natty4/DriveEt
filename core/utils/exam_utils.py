# core/utils/exam_utils.py

from django.utils import timezone
from django.db import models
from django.db.models import Case, When, Max, Q, Value, CharField
from django.db.models.functions import Round
from core.models import Exam
from users.models import ExamAttempt

def get_exams_for_user(user_profile):
    """
    Returns exams the user can access:
    - If subscribed: exams linked to any of their active subscriptions
    - If not subscribed: only free exams
    Includes annotations for status and best_score
    """
    
    if user_profile.is_subscribed():
        exams_qs = Exam.objects.filter(
            is_active=True,
            tiers__subscription__user_profile=user_profile,
            tiers__subscription__expiry_date__gt=timezone.now(),
            tiers__subscription__is_active=True,
            attempts__deleted_at__isnull=True
        ).distinct()
    else:
        exams_qs = Exam.objects.filter(is_active=True, is_free=True)
        
    return exams_qs.annotate(
            status=Case(
                When(
                    attempts__user_profile=user_profile,
                    attempts__status=ExamAttempt.Status.COMPLETED,
                    then=Value('completed')
                ),
                When(
                    attempts__user_profile=user_profile,
                    attempts__status=ExamAttempt.Status.STARTED,
                    then=Value('started')
                ),
                default=Value('not_started'),
                output_field=CharField()
            ),
            
            # Attempt status
            completed=Case(
                When(
                    attempts__user_profile=user_profile,
                    attempts__status=ExamAttempt.Status.COMPLETED,
                    then=Value(True)
                ),
                default=Value(False),
                output_field=models.BooleanField()
            ),
            in_progress=Case(
                When(
                    attempts__user_profile=user_profile,
                    attempts__status=ExamAttempt.Status.STARTED,
                    then=Value(True)
                ),
                default=Value(False),
                output_field=models.BooleanField()
            ),
            last_score=Round(
                Max(
                    'attempts__score',
                    filter=Q(attempts__user_profile=user_profile)
                ),
                1
            ),
            premium=Case(
                When(is_free=False, then=Value(True)),
                default=Value(False),
                output_field=models.BooleanField()
            ),
            timestamp = Max(
                'attempts__end_time',
                filter=Q(attempts__user_profile=user_profile)
            )
        )
    
    