# common/contents.py

import enum


class Language(enum.Enum):
    """Language enum for consistent usage across the application"""
    ENGLISH = 'en'
    AMHARIC = 'am'
    TIGRIGNA = 'ti'
    AFAN_OROMO = 'or'

    @classmethod
    def choices(cls):
        return [(member.value, member.name.replace('_', ' ').title()) for member in cls]

    @classmethod
    def values(cls):
        return [member.value for member in cls]

