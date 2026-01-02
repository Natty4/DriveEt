# core/serializers/roadsign.py
from rest_framework import serializers
from core.models import RoadSign, RoadSignTranslation
from .base import AllTranslationsMixin

class RoadSignSerializer(serializers.ModelSerializer, AllTranslationsMixin):
    translations = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = RoadSign
        fields = ['id', 'code', 'translations', 'image_url', 'category']

    def get_translations(self, obj):
        return self.get_translations_dict(
            obj,
            obj.translations.all(),
            fields=['name', 'meaning', 'detailed_explanation']
        )

    def get_image_url(self, obj):
        request = self.context.get('request')
        return request.build_absolute_uri(obj.image.url) if obj.image and request else None