from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import (
    RoadSign, RoadSignTranslation, 
    Question, QuestionTranslation,
    AnswerChoice, AnswerChoiceTranslation,
    Explanation, ExplanationTranslation,
    PaymentMethod, PaymentMethodTranslation,
    UserProfile
)
from django.utils import timezone


class Command(BaseCommand):
    help = 'Seed minimal test data with translations for development'
    
    def handle(self, *args, **options):
        self.stdout.write('Seeding minimal test data...')
        
        # Create one road sign with full translations
        road_sign = RoadSign.objects.create(code='STOP01')
        
        RoadSignTranslation.objects.bulk_create([
            RoadSignTranslation(
                road_sign=road_sign,
                language='en',
                name='Stop Sign',
                description='Complete stop required'
            ),
            RoadSignTranslation(
                road_sign=road_sign,
                language='am',
                name='መቆም ምልክት',
                description='ሙሉ በሙሉ መቆም ያስፈልጋል'
            ),
        ])
        
        # Create one free question
        free_question = Question.objects.create(
            road_sign=road_sign,
            is_premium=False,
            difficulty=1
        )
        
        QuestionTranslation.objects.bulk_create([
            QuestionTranslation(
                question=free_question,
                language='en',
                content='What does a stop sign require you to do?'
            ),
            QuestionTranslation(
                question=free_question,
                language='am',
                content='መቆም ምልክት ምን ማድረግ እንዳለብዎት ይጠይቃል?'
            ),
        ])
        
        # Create answer choices
        correct_answer = AnswerChoice.objects.create(
            question=free_question,
            is_correct=True,
            order=1
        )
        
        AnswerChoiceTranslation.objects.bulk_create([
            AnswerChoiceTranslation(
                answer_choice=correct_answer,
                language='en',
                text='Come to a complete stop'
            ),
            AnswerChoiceTranslation(
                answer_choice=correct_answer,
                language='am',
                text='ሙሉ በሙሉ ቁም'
            ),
        ])
        
        wrong_answer = AnswerChoice.objects.create(
            question=free_question,
            is_correct=False,
            order=2
        )
        
        AnswerChoiceTranslation.objects.bulk_create([
            AnswerChoiceTranslation(
                answer_choice=wrong_answer,
                language='en',
                text='Slow down'
            ),
            AnswerChoiceTranslation(
                answer_choice=wrong_answer,
                language='am',
                text='ያምር'
            ),
        ])
        
        # Create explanation
        explanation = Explanation.objects.create(
            question=free_question
        )
        
        ExplanationTranslation.objects.bulk_create([
            ExplanationTranslation(
                explanation=explanation,
                language='en',
                detail='Stop signs require a complete stop before proceeding.'
            ),
            ExplanationTranslation(
                explanation=explanation,
                language='am',
                detail='መቆም ምልክቶች ከመቀጠልዎ በፊት ሙሉ በሙሉ መቆም ይጠይቃሉ።'
            ),
        ])
        
        # Create one payment method
        payment_method = PaymentMethod.objects.create(
            name='Telebirr',
            code='TELEBIRR',
            is_active=True,
            order=1
        )
        
        PaymentMethodTranslation.objects.bulk_create([
            PaymentMethodTranslation(
                payment_method=payment_method,
                language='en',
                account_details='Account: 251912345678',
                instruction='Send 150 ETB to this account'
            ),
            PaymentMethodTranslation(
                payment_method=payment_method,
                language='am',
                account_details='አካውንት: 251912345678',
                instruction='150 ብር ወደዚህ አካውንት ይላኩ'
            ),
        ])
        
        # Create admin user if not exists
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser(
                username='admin',
                email='admin@example.com',
                password='admin123'
            )
            self.stdout.write('Created admin user (admin/admin123)')
        
        self.stdout.write(self.style.SUCCESS('Minimal test data seeded successfully!'))