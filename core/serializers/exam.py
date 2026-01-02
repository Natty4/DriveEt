# core/serializers/exam.py
from rest_framework import serializers
from core.models import Exam, ExamAttempt, ExamTranslation
from .base import AllTranslationsMixin
from .question import QuestionSerializer
from decimal import Decimal, ROUND_HALF_UP

class ExamTranslationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExamTranslation
        fields = ['language', 'title', 'description']

class ExamMetadataSerializer(serializers.ModelSerializer, AllTranslationsMixin):
    translations = serializers.SerializerMethodField()
    status = serializers.CharField(read_only=True)
    best_score = serializers.FloatField(source='annotated_best_score', read_only=True)
    premium = serializers.BooleanField(read_only=True)
    completed = serializers.BooleanField(read_only=True)
    inProgress = serializers.BooleanField(read_only=True, source='in_progress')
    lastScore = serializers.SerializerMethodField()

    class Meta:
        model = Exam
        fields = ['id', 'translations', 'difficulty', 'duration_minutes',
                  'question_count', 'status', 'best_score',
                  'premium', 'completed', 'inProgress', 'lastScore'
                  ]


    def get_lastScore(self, obj):
        score = obj.last_score
        if score is None:
            return None

        # Force 1 decimal place safely
        score = score.quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)

        if score % 1 == 0:
            return int(score)
        return score
    
    def get_translations(self, obj):
        return self.get_translations_dict(
            obj,
            obj.translations.all(),
            fields=['title', 'description']
        )


# class ExamMetadataSerializer(serializers.ModelSerializer, AllTranslationsMixin):
#     translations = serializers.SerializerMethodField()
#     question_count = serializers.IntegerField(read_only=True)
#     duration_minutes = serializers.IntegerField(read_only=True)
    # premium = serializers.BooleanField(read_only=True)  # Annotated
    # completed = serializers.BooleanField(read_only=True)
    # inProgress = serializers.BooleanField(read_only=True, source='in_progress')
    # lastScore = serializers.FloatField(read_only=True, source='last_score', allow_null=True)
    

#     class Meta:
#         model = Exam
#         fields = [
#             'id', 'translations', 'question_count', 'duration_minutes',
#             'premium', 'completed', 'inProgress', 'lastScore', 'difficulty',
            
#         ]

#     def get_translations(self, obj):
#         return self.get_translations_dict(
#             obj,
#             obj.translations.all(),
#             fields=['title', 'description']
#         )
        

class ExamDetailSerializer(serializers.ModelSerializer, AllTranslationsMixin):
    translations = serializers.SerializerMethodField()
    questions = QuestionSerializer(many=True, read_only=True)

    class Meta:
        model = Exam
        fields = ['id', 'translations', 'difficulty', 'duration_minutes', 'question_count', 'passing_score', 'questions']

    def get_translations(self, obj):
        return self.get_translations_dict(
            obj,
            obj.translations.all(),
            fields=['title', 'description']
        )


class ExamAttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExamAttempt
        fields = ['id', 'start_time', 'end_time', 'score', 'is_passed', 'raw_answers_json', 'status']
        
        