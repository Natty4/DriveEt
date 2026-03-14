# core/serializers/question.py

import random
from datetime import date
from rest_framework import serializers
from core.models import (
    Question,
    QuestionTranslation, 
    AnswerChoice, 
    AnswerChoiceTranslation,
    Explanation,
    ExplanationTranslation
)
from .base import AllTranslationsMixin
from .roadsign import RoadSignSerializer
from .category import QuestionCategorySerializer

class AnswerChoiceSerializer(serializers.ModelSerializer, AllTranslationsMixin):
    translations = serializers.SerializerMethodField()
    road_sign_option = RoadSignSerializer(read_only=True)

    class Meta:
        model = AnswerChoice
        fields = ['id', 'translations', 'road_sign_option', 'is_correct', 'order']

    def get_translations(self, obj):
        return self.get_translations_dict(
            obj,
            obj.translations.all(),
            fields=['text']
        )


class ExplanationSerializer(serializers.ModelSerializer, AllTranslationsMixin):
    translations = serializers.SerializerMethodField()

    class Meta:
        model = Explanation
        fields = ['translations', 'media_url', 'media_type']

    def get_translations(self, obj):
        return self.get_translations_dict(
            obj,
            obj.translations.all(),
            fields=['detail']
        )


class QuestionSerializer(serializers.ModelSerializer, AllTranslationsMixin):
    translations = serializers.SerializerMethodField()
    # choices = AnswerChoiceSerializer(many=True, read_only=True)
    choices = serializers.SerializerMethodField()
    explanation = ExplanationSerializer(read_only=True)
    associated_road_sign = RoadSignSerializer(read_only=True)
    effective_image_url = serializers.SerializerMethodField()
    category = QuestionCategorySerializer(read_only=True)

    class Meta:
        model = Question
        fields = [
            'id', 'question_type', 'translations', 'choices',
            'explanation', 'associated_road_sign', 'effective_image_url',
            'difficulty', 'category'
        ]

    def get_translations(self, obj):
        return self.get_translations_dict(
            obj,
            obj.translations.all(),
            fields=['content']
        )
    
    def get_effective_image_url(self, obj):
        if obj.associated_road_sign and obj.associated_road_sign.image:
            url = obj.associated_road_sign.image.url
        elif obj.media_image:
            url = obj.media_image.url
        else:
            return None

        # Same Cloudinary optimization
        return url.replace(
            '/upload/',
            '/upload/w_400,h_400,c_limit,q_auto,f_auto/'
        )
    
    def get_choices(self, obj):
        request = self.context.get("request")
        user = getattr(request, "user", None)

        choices = list(obj.choices.all())
        
        total = len(choices)
        if total <= 2:
            # Too few choices to shuffle
            return AnswerChoiceSerializer(choices, many=True, context=self.context).data

        # Split last choice
        normal_choices = choices[:-1]   # shuffle these
        last_choice = choices[-1:]      # keep last as is

        # Create deterministic seed includes date for daily shuffling
        today_str = date.today().isoformat()
        seed = f"{user.id if user.id else 'anon'}-{obj.id}-{today_str}"

        rng = random.Random(seed)
        rng.shuffle(normal_choices)
        
        # Combine shuffled + last choice
        final_choices = normal_choices + last_choice

        return AnswerChoiceSerializer(
            final_choices,
            many=True,
            context=self.context
        ).data
    