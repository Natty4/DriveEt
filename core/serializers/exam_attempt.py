# core/serializers/exam_attempt.py

from rest_framework import serializers
from core.models import Question, AnswerChoice
from core.serializers.question import (
    QuestionSerializer,
    AnswerChoiceSerializer
)
from users.models import ExamAttempt
from core.serializers.exam import ExamDetailSerializer

class ExamAttemptDetailSerializer(serializers.ModelSerializer):
    exam = ExamDetailSerializer(read_only=True)
    user_answers = serializers.SerializerMethodField()

    class Meta:
        model = ExamAttempt
        fields = [
            'id', 'exam', 'start_time', 'end_time', 'timestamp',
            'score', 'is_passed', 'status', 'user_answers'
        ]

    def get_user_answers(self, obj):
        """
        Returns list of user's answers with correctness.
        Frontend can match choice_id to exam.questions[].choices[]
        """
        answers = []
        raw = obj.raw_answers_json or {}
        for q_id, c_id in raw.items():
            try:
                choice = AnswerChoice.objects.get(id=c_id)
                answers.append({
                    "question_id": str(q_id),
                    "choice_id": str(c_id),
                    "is_correct": choice.is_correct
                })
            except AnswerChoice.DoesNotExist:
                answers.append({
                    "question_id": str(q_id),
                    "choice_id": str(c_id),
                    "is_correct": False
                })
        return answers
    