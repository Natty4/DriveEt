# core/serializers/base.py
from rest_framework import serializers

class AllTranslationsMixin:
    """Mixin to serialize all translations as a dict keyed by language code"""
    
    def get_translations_dict(self, obj, translation_qs, fields):
        """
        obj: parent object (e.g., Question, RoadSign)
        translation_qs: queryset of translations related to obj (e.g., obj.translations.all())
        fields: list of field names to include (e.g., ['content'], ['name', 'description'])
        """
        translations = {}
        for trans in translation_qs:
            lang = trans.language
            translations[lang] = {
                field: getattr(trans, field, "") for field in fields
            }
        # Ensure all supported languages are present with empty dicts if missing
        for lang in ['en', 'am', 'ti', 'or']:
            if lang not in translations:
                translations[lang] = {field: "" for field in fields}
        return translations
   