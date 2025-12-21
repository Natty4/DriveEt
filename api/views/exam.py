# api/views/exam.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db import transaction
import random
import logging

from core.models import (
    ExamSession, ExamQuestion, Question, 
    UserProfile, ResourceTransaction
)
from core.authentication import TelegramAuthenticationBackend
from core.serializers import ExamSessionSerializer, QuestionSerializer
from core.services import BundleService
from core.permissions import IsTelegramAuthenticated

logger = logging.getLogger(__name__)


class ExamViewSet(viewsets.ModelViewSet):
    """
    API for exam simulation with bundle consumption
    """
    permission_classes = [IsAuthenticated, IsTelegramAuthenticated]
    serializer_class = ExamSessionSerializer
    queryset = ExamSession.objects.all()
    
    def get_queryset(self):
        """Users can only see their own exams"""
        return self.queryset.filter(user=self.request.user)
    
    @action(detail=False, methods=['post'])
    def start_exam(self, request):
        """
        Start a new exam session - consumes 1 exam attempt
        POST /api/v1/exam/start_exam/
        """
        user = request.user
        
        # Check if user has an active exam
        active_exam = ExamSession.objects.filter(
            user=user,
            status=ExamSession.ExamStatus.IN_PROGRESS
        ).first()
        
        if active_exam:
            return Response({
                'error': 'You have an active exam in progress',
                'exam_id': str(active_exam.id),
                'resume_url': f'/api/v1/exam/{active_exam.id}/resume/'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Consume exam resource
        success, bundle, error = BundleService.consume_resource(
            user=user,
            resource_type=ResourceTransaction.ResourceType.EXAM,
            quantity=1,
            description="Started new exam"
        )
        
        if not success:
            return Response({
                'error': 'Cannot start exam',
                'detail': error,
                'remaining_resources': bundle.get_remaining_resources() if bundle else None
            }, status=status.HTTP_402_PAYMENT_REQUIRED)
        
        # Get exam configuration
        profile = user.profile
        question_count = request.data.get('question_count', profile.questions_per_exam)
        time_limit = request.data.get('time_limit', profile.exam_time_limit)
        categories = request.data.get('categories', [])
        
        # Select questions based on bundle search quota
        searchable_limit = None
        if bundle and not bundle.bundle_definition.is_unlimited_search:
            searchable_limit = bundle.search_remaining
        
        questions_qs = Question.objects.all()
        
        # Apply search quota limit
        if searchable_limit is not None:
            questions_qs = questions_qs[:searchable_limit]
        
        if categories:
            questions_qs = questions_qs.filter(
                road_sign_context__category__code__in=categories
            )
        
        # Get random questions
        available_questions = list(questions_qs)
        if len(available_questions) < question_count:
            return Response({
                'error': f'Not enough questions available. Need {question_count}, have {len(available_questions)}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        selected_questions = random.sample(available_questions, question_count)
        
        # Create exam session
        with transaction.atomic():
            exam_session = ExamSession.objects.create(
                user=user,
                status=ExamSession.ExamStatus.IN_PROGRESS
            )
            
            # Add questions to exam
            for i, question in enumerate(selected_questions, 1):
                ExamQuestion.objects.create(
                    exam_session=exam_session,
                    question=question,
                    order=i
                )
        
        # Update user stats
        profile.total_exam_attempts += 1
        profile.save()
        
        serializer = self.get_serializer(exam_session)
        return Response({
            'message': 'Exam started successfully',
            'exam': serializer.data,
            'config': {
                'question_count': question_count,
                'time_limit': time_limit,
                'start_time': timezone.now().isoformat()
            },
            'remaining_exams': bundle.exams_remaining if bundle else 0
        })
        
    @action(detail=True, methods=['post'])
    def submit_answer(self, request, pk=None):
        """
        Submit answer for a question in the exam
        POST /api/v1/exam/{id}/submit_answer/
        """
        try:
            exam = self.get_object()
            if exam.status != ExamSession.ExamStatus.IN_PROGRESS:
                return Response({
                    'error': 'Exam is not in progress'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            question_id = request.data.get('question_id')
            answer_id = request.data.get('answer_id')
            time_spent = request.data.get('time_spent')
            
            # Find the exam question
            exam_question = ExamQuestion.objects.get(
                exam_session=exam,
                question_id=question_id
            )
            
            # Get selected answer
            selected_answer = exam_question.question.choices.get(id=answer_id)
            exam_question.selected_answer = selected_answer
            exam_question.is_correct = selected_answer.is_correct
            exam_question.time_spent = time_spent
            exam_question.save()
            
            return Response({
                'success': True,
                'is_correct': selected_answer.is_correct,
                'correct_answer_id': str(exam_question.question.choices.filter(is_correct=True).first().id)
            })
            
        except ExamQuestion.DoesNotExist:
            return Response({
                'error': 'Question not found in this exam'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error submitting answer: {str(e)}")
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def submit_exam(self, request, pk=None):
        """
        Submit the entire exam
        POST /api/v1/exam/{id}/submit_exam/
        """
        try:
            exam = self.get_object()
            if exam.status != ExamSession.ExamStatus.IN_PROGRESS:
                return Response({
                    'error': 'Exam is not in progress'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Calculate score
            exam_questions = ExamQuestion.objects.filter(exam_session=exam)
            total_questions = exam_questions.count()
            correct_answers = exam_questions.filter(is_correct=True).count()
            score = (correct_answers / total_questions) * 100 if total_questions > 0 else 0
            
            # Calculate time taken
            time_taken = (timezone.now() - exam.start_time).seconds
            
            # Update exam
            exam.status = ExamSession.ExamStatus.COMPLETED
            exam.end_time = timezone.now()
            exam.score = score
            exam.time_taken = time_taken
            exam.passed = score >= 80  # 80% passing score
            exam.save()
            
            # Update user profile
            profile = request.user.profile
            profile.correct_answers += correct_answers
            if score > profile.highest_exam_score:
                profile.highest_exam_score = score
            profile.save()
            
            serializer = self.get_serializer(exam)
            return Response({
                'message': 'Exam submitted successfully',
                'exam': serializer.data,
                'results': {
                    'score': score,
                    'correct_answers': correct_answers,
                    'total_questions': total_questions,
                    'passed': exam.passed,
                    'time_taken': time_taken
                }
            })
            
        except Exception as e:
            logger.error(f"Error submitting exam: {str(e)}")
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def review(self, request, pk=None):
        """
        Get exam review with explanations
        GET /api/v1/exam/{id}/review/
        """
        exam = self.get_object()
        
        # Get exam questions with explanations
        exam_questions = ExamQuestion.objects.filter(
            exam_session=exam
        ).select_related(
            'question__explanation',
            'selected_answer'
        ).order_by('order')
        
        review_data = []
        for eq in exam_questions:
            question_data = QuestionSerializer(eq.question).data
            
            # Get explanation if available
            explanation = None
            if hasattr(eq.question, 'explanation'):
                explanation = {
                    'detail': eq.question.explanation.translations.filter(
                        language=request.user.profile.preferred_language
                    ).first().detail if eq.question.explanation.translations.exists() else '',
                    'media_url': eq.question.explanation.media_url,
                    'media_type': eq.question.explanation.media_type
                }
            
            review_data.append({
                'question': question_data,
                'selected_answer': AnswerChoiceSerializer(eq.selected_answer).data if eq.selected_answer else None,
                'is_correct': eq.is_correct,
                'time_spent': eq.time_spent,
                'explanation': explanation
            })
        
        return Response({
            'exam_id': str(exam.id),
            'score': exam.score,
            'passed': exam.passed,
            'review_questions': review_data
        })
        
        