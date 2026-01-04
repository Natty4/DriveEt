# core/serializers/category.py

from rest_framework import serializers
from core.models import (
    QuestionCategory, 
    QuestionCategoryTranslation, 
    RoadSignCategory, 
    RoadSignCategoryTranslation
)
from .base import AllTranslationsMixin

class QuestionCategorySerializer(serializers.ModelSerializer, AllTranslationsMixin):
    translations = serializers.SerializerMethodField()

    class Meta:
        model = QuestionCategory
        fields = ['id', 'code', 'order', 'translations']

    def get_translations(self, obj):
        return self.get_translations_dict(
            obj,
            obj.translations.all(),
            fields=['name', 'description']
        )


class RoadSignCategorySerializer(serializers.ModelSerializer, AllTranslationsMixin):
    translations = serializers.SerializerMethodField()

    class Meta:
        model = RoadSignCategory
        fields = ['id', 'code', 'order', 'translations']

    def get_translations(self, obj):
        return self.get_translations_dict(
            obj,
            obj.translations.all(),
            fields=['name', 'description']
        )
        
        