from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Avg, Q
from django.utils import timezone
from datetime import timedelta
from core.models import UserProgress, Question
from core.serializers import UserProgressSerializer
import logging

logger = logging.getLogger(__name__)


class UserProgressViewSet(viewsets.ModelViewSet):
    serializer_class = UserProgressSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return UserProgress.objects.filter(user=self.request.user).select_related(
            'question', 'selected_answer'
        ).order_by('-created_at')
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
        
        # Update user profile statistics
        profile = self.request.user.profile
        profile.total_attempts += 1
        if serializer.validated_data.get('is_correct'):
            profile.correct_answers += 1
        profile.save()
    
    @action(detail=False, methods=['post'])
    def bulk_save(self, request):
        """
        Save multiple progress records at once
        """
        progress_data = request.data.get('progress', [])
        
        if not isinstance(progress_data, list):
            return Response(
                {'error': 'progress must be a list'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        created_records = []
        errors = []
        
        for idx, item in enumerate(progress_data):
            serializer = self.get_serializer(data=item)
            if serializer.is_valid():
                serializer.save(user=request.user)
                created_records.append(serializer.data)
            else:
                errors.append({
                    'index': idx,
                    'errors': serializer.errors
                })
        
        # Update profile statistics
        if created_records:
            profile = request.user.profile
            correct_count = sum(1 for record in created_records if record.get('is_correct'))
            profile.total_attempts += len(created_records)
            profile.correct_answers += correct_count
            profile.save()
        
        response_data = {
            'created': len(created_records),
            'errors': errors
        }
        
        if errors:
            response_data['message'] = f"Created {len(created_records)} records with {len(errors)} errors"
            return Response(response_data, status=status.HTTP_207_MULTI_STATUS)
        
        return Response(response_data, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Get user progress statistics
        """
        # Daily statistics for the last 7 days
        seven_days_ago = timezone.now() - timedelta(days=7)
        
        daily_stats = (
            UserProgress.objects
            .filter(user=request.user, created_at__gte=seven_days_ago)
            .extra({'date': "date(created_at)"})
            .values('date')
            .annotate(
                total=Count('id'),
                correct=Count('id', filter=Q(is_correct=True)),
                avg_time=Avg('time_taken')
            )
            .order_by('date')
        )
        
        # Overall statistics
        total_attempts = self.get_queryset().count()
        correct_attempts = self.get_queryset().filter(is_correct=True).count()
        accuracy = (correct_attempts / total_attempts * 100) if total_attempts > 0 else 0
        
        # Most difficult questions (lowest accuracy)
        difficult_questions = (
            UserProgress.objects
            .filter(user=request.user)
            .values('question__id', 'question__content_en')
            .annotate(
                total=Count('id'),
                correct=Count('id', filter=Q(is_correct=True))
            )
            .filter(total__gte=3)  # At least 3 attempts
            .order_by('correct')[:5]
        )
        
        return Response({
            'overall': {
                'total_attempts': total_attempts,
                'correct_attempts': correct_attempts,
                'accuracy': round(accuracy, 2),
                'average_time': self.get_queryset().aggregate(avg=Avg('time_taken'))['avg'] or 0
            },
            'daily_stats': list(daily_stats),
            'difficult_questions': list(difficult_questions),
            'recent_activity': UserProgressSerializer(
                self.get_queryset()[:10], 
                many=True
            ).data
        })
    
    @action(detail=False, methods=['get'])
    def session_stats(self, request):
        """
        Get statistics for a specific session
        """
        session_id = request.query_params.get('session_id')
        
        if not session_id:
            return Response(
                {'error': 'session_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        session_progress = self.get_queryset().filter(session_id=session_id)
        total = session_progress.count()
        correct = session_progress.filter(is_correct=True).count()
        accuracy = (correct / total * 100) if total > 0 else 0
        
        return Response({
            'session_id': session_id,
            'total_questions': total,
            'correct_answers': correct,
            'accuracy': round(accuracy, 2),
            'average_time': session_progress.aggregate(avg=Avg('time_taken'))['avg'] or 0,
            'progress': UserProgressSerializer(session_progress, many=True).data
        })