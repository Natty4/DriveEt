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
        if not obj.image:
            return None

        # Cloudinary auto-optimized URL (w=400, quality auto, best format)
        url = obj.image.url

        # Resize to 400px width, auto quality/format, fill crop
        optimized_url = url.replace(
            '/upload/',
            '/upload/w_400,h_400,c_fill,q_auto,f_auto/'
        )

        return optimized_url


    
    
    