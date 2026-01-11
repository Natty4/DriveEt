# core/viewsets/content.py

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Q, Prefetch

from core.models import (
    Exam, Question, 
    AnswerChoice
)
from users.models import ExamAttempt
from core.serializers.exam import (
    ExamMetadataSerializer, 
    ExamDetailSerializer, 
    ExamAttemptSerializer
)
from core.serializers.question import QuestionSerializer
from core.serializers.exam_attempt import ExamAttemptDetailSerializer
from core.permissions import (
    IsTelegramAuthenticated,
    HasActiveSubscription,
    CanAccessFullRoadSignQuiz
)
from core.utils.exam_utils import get_exams_for_user
from core.utils.subscription_utils import can_access_exam
from core.responses import APIResponse
from django.contrib.auth import get_user_model


class ContentViewSet(viewsets.ViewSet):
    permission_classes = [IsTelegramAuthenticated]

    def get_serializer_context(self):
        return {'request': self.request}

    # 1. Dashboard: List of available exams
    @action(detail=False, methods=['get'])
    def my_exams(self, request):
        exams_qs = get_exams_for_user(request.user.profile)
        serializer = ExamMetadataSerializer(
            exams_qs,
            many=True,
            context=self.get_serializer_context()
        )
        return APIResponse.success(data=serializer.data)

    # 2. Single Exam Detail — Fixed & Improved
    @action(detail=True, methods=['get'], url_path='exam')
    def exam_detail(self, request, pk=None):
        profile = request.user.profile
        exam = get_object_or_404(Exam, id=pk)

        # Use unified access checker
        if not can_access_exam(profile, exam):
            return APIResponse.forbidden(
                message="""You do not have access to this exam. 
                It may require an active subscription or 
                be unavailable in your tier.
                """
            )

        # Optimized prefetch for all nested translated + related data
        exam = Exam.objects.prefetch_related(
            'translations',
            Prefetch(
                'questions',
                queryset=Question.objects.prefetch_related(
                    'translations',
                    'choices__translations',
                    'choices__road_sign_option__translations',
                    'explanation__translations',
                    'associated_road_sign__translations',
                    'category__translations'
                )
            )
        ).get(id=pk)

        serializer = ExamDetailSerializer(exam, context=self.get_serializer_context())
        return APIResponse.success(data=serializer.data)

    # 3. Offline Sync: All Exams
    @action(detail=False, methods=['get'], url_path='exams/all')
    def all_exams_offline(self, request):
        if not request.user.profile.is_subscribed():
            return APIResponse.forbidden("Active subscription required for offline sync.")

        profile = request.user.profile
        exams = Exam.objects.filter(
            tiers__subscription__user_profile=profile,
            tiers__subscription__expiry_date__gt=timezone.now()
        ).distinct().prefetch_related(
            'translations',
            'questions__translations',
            'questions__choices__translations',
            'questions__choices__road_sign_option__translations',
            'questions__explanation__translations',
            'questions__associated_road_sign__translations',
            'questions__category__translations'
        )

        if not exams.exists():
            return APIResponse.success(data={"exams": []}, message="No exams available in your subscription.")

        serializer = ExamDetailSerializer(exams, many=True, context=self.get_serializer_context())
        return APIResponse.success(data={"exams": serializer.data})

    # 4. Road Sign Quiz (Client-side)
    @action(detail=False, methods=['get'], url_path='roadsign-quiz')
    def roadsign_quiz(self, request):
        base_qs = Question.objects.filter(
            Q(category__code='SIGN') | Q(associated_road_sign__isnull=False)
        ).distinct()

        profile = request.user.profile
        is_full_access = (
            profile.is_subscribed() and
            profile.active_subscription.tier.full_road_sign_quiz
        )

        if not is_full_access:
            # Limit free/basic users — customize as needed
            base_qs = base_qs.filter(
                Q(category__code='SIGN', is_premium=False)
            )[:30]  # Example limit

        qs = base_qs.prefetch_related(
            'translations',
            'choices__translations',
            'choices__road_sign_option__translations',
            'explanation__translations',
            'associated_road_sign__translations',
            'category__translations'
        )

        serializer = QuestionSerializer(qs, many=True, context=self.get_serializer_context())
        return APIResponse.success(data=serializer.data)

    # 5. Submit Exam Attempt
    @action(detail=False, methods=['post'])
    def submissions(self, request):
        exam_id = request.data.get('exam_id')
        answers = request.data.get('answers', {})

        if not exam_id or not isinstance(answers, dict) or not answers:
            return APIResponse.error(
                message="exam_id and non-empty answers dictionary are required.",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        exam = get_object_or_404(Exam, id=exam_id)
        profile = request.user.profile

        if not can_access_exam(profile, exam):
            return APIResponse.forbidden(
                message="You cannot submit this exam. Access denied."
            )

        attempt, created = ExamAttempt.objects.get_or_create(
            user_profile=profile,
            exam=exam,
            defaults={'raw_answers_json': answers, 'status': ExamAttempt.Status.STARTED}
        )

        if not created:
            attempt.raw_answers_json = answers
            attempt.status = ExamAttempt.Status.STARTED
            attempt.score = None
            attempt.is_passed = None
            attempt.start_time = timezone.now()
            attempt.end_time = None

        with transaction.atomic():
            attempt.calculate_score()

        correct_count = sum(
            AnswerChoice.objects.filter(id=choice_id, is_correct=True).exists()
            for choice_id in answers.values()
            # if isinstance(choice_id, str) and choice_id.isalnum()
        )
        return APIResponse.success(data={
            "score": round(attempt.score, 2) if attempt.score else 0.0,
            "is_passed": attempt.is_passed,
            "correct_count": correct_count,
            "total_questions": len(answers),
            "attempt_id": str(attempt.id)
        })
    
    # 6. Reset Exam Attempts    
    @action(detail=False, methods=['delete'], url_path='reset_attempt')
    def reset_attempt(self, request):
        """
        Reset (soft delete) exam attempts.
        Payload options:
        1. Single: { "exam_id": "uuid" }
        2. Bulk: { "all": true }  OR empty body
        """
        profile = request.user.profile
        exam_id = request.data.get('exam_id')
        reset_all = request.data.get('all', False) or exam_id is None
        exams_qs = get_exams_for_user(request.user.profile)
        
        if reset_all:
            # Bulk reset: all non-deleted attempts for this user
            
            attempts_qs = ExamAttempt.filter(
                user_profile=request.user.profile,
                deleted_at__isnull=True
            )

            if not attempts_qs.exists():
                return APIResponse.success(
                    message="No active attempts to reset.",
                    data={"reset_count": 0}
                )

            with transaction.atomic():
                reset_count = attempts_qs.update(
                    deleted_at=timezone.now(),
                    status=ExamAttempt.Status.ABANDONED,
                )

            return APIResponse.success(
                message=f"Successfully reset {reset_count} exam attempt(s).",
                data={
                    "reset_count": reset_count,
                    "reset_at": timezone.now().isoformat()
                }
            )
        else:
            # Single reset
            if not exam_id:
                return APIResponse.error(
                    message="exam_id is required for single reset, or use 'all: true' for bulk.",
                    status_code=status.HTTP_400_BAD_REQUEST
                )

            attempt = get_object_or_404(
                ExamAttempt,
                user_profile=profile,
                exam_id=exam_id,
                deleted_at__isnull=True
            )

            with transaction.atomic():
                attempt.deleted_at = timezone.now()
                attempt.status = ExamAttempt.Status.ABANDONED
                attempt.save()

            return APIResponse.success(
                message="Exam attempt reset successfully.",
                data={
                    "exam_id": str(attempt.exam.id),
                    "reset_at": timezone.now().isoformat()
                }
            )    
    
    # 7. Exam Attempts list
    @action(detail=False, methods=['get'], url_path='my_exam_attempts')
    def my_exam_attempts(self, request):
        """
        Get detailed exam attempts.
        - ?exam_id=<uuid>: Single attempt for that exam
        - No param: All attempts for user's active subscription
        Only non-deleted attempts
        """
        # profile = request.user.profile
        profile = request.user.profile
        exam_id = request.query_params.get('exam_id')

        if not profile.is_subscribed():
            return APIResponse.error(
                message="Active subscription required to view attempts.",
                status_code=status.HTTP_403_FORBIDDEN
            )

        # Base QS: User's attempts for active subscription exams
        attempts_qs = ExamAttempt.objects.filter(
            user_profile=profile,
            deleted_at__isnull=True,
            exam__tiers__subscription__user_profile=profile,
            exam__tiers__subscription__expiry_date__gt=timezone.now()
        ).select_related('exam').prefetch_related(
            'exam__questions', 'exam__questions__choices'
        ).distinct()

        if exam_id:
            # Single exam attempt
            attempt = get_object_or_404(attempts_qs, exam_id=exam_id)
            serializer = ExamAttemptDetailSerializer(attempt, context=self.get_serializer_context())
            return APIResponse.success(data=serializer.data)

        else:
            # All attempts
            serializer = ExamAttemptDetailSerializer(
                attempts_qs.order_by('-start_time'),
                many=True,
                context=self.get_serializer_context()
            )
            return APIResponse.success(data=serializer.data)

