# api/views/chat.py
import google.generativeai as genai
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.core.cache import cache
from django.conf import settings

from core.models import User


class ChatAssistantView(APIView):
    """AI Chat Assistant using Google Gemini"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        message = request.data.get('message')
        context = request.data.get('context', '')  # Optional: question context
        
        if not message:
            return Response(
                {'error': 'Message is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user = request.user
        
        # Check if user is premium
        is_premium = user.is_premium()
        
        # Check rate limits
        if not self.check_rate_limit(user, is_premium):
            if is_premium:
                return Response(
                    {'error': 'Daily limit reached. Try again tomorrow.'},
                    status=status.HTTP_429_TOO_MANY_REQUESTS
                )
            else:
                return Response(
                    {'error': 'Free tier limit reached. Upgrade to premium for unlimited access.'},
                    status=status.HTTP_402_PAYMENT_REQUIRED
                )
        
        try:
            # Configure Gemini
            genai.configure(api_key=settings.GEMINI_API_KEY)
            
            # Create model
            model = genai.GenerativeModel('gemini-pro')
            
            # Create prompt with context
            prompt = self.create_prompt(message, context, user.preferred_language)
            
            # Generate response
            response = model.generate_content(prompt)
            
            # Extract response text
            response_text = response.text
            
            # Update user's query count
            user.reset_chat_queries()
            user.ai_chat_queries_today += 1
            user.save(update_fields=['ai_chat_queries_today'])
            
            return Response({
                'response': response_text,
                'queries_used_today': user.ai_chat_queries_today,
                'queries_limit': self.get_query_limit(is_premium),
                'is_premium': is_premium
            })
            
        except Exception as e:
            return Response(
                {'error': f'Chat error: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def check_rate_limit(self, user, is_premium):
        """Check if user has exceeded rate limits"""
        user.reset_chat_queries()
        
        if is_premium:
            # Premium users: 100 queries per day
            return user.ai_chat_queries_today < 100
        else:
            # Free users: 5 queries per day
            return user.ai_chat_queries_today < 5
    
    def get_query_limit(self, is_premium):
        return 100 if is_premium else 5
    
    def create_prompt(self, message, context, language):
        """Create prompt for the AI"""
        base_prompt = """
        You are a helpful driving exam assistant for Ethiopian driving tests.
        Your role is to explain driving rules, road signs, and answer questions about driving in Ethiopia.
        
        Important guidelines:
        1. Always provide accurate information based on Ethiopian traffic laws
        2. If you're not sure about something, say so
        3. Keep explanations clear and concise
        4. Focus on practical driving advice
        
        User's question: {message}
        """.format(message=message)
        
        if context:
            base_prompt += f"\nContext: {context}\n"
        
        # Add language preference
        language_names = {
            'en': 'English',
            'am': 'Amharic',
            'om': 'Oromo',
            'ti': 'Tigrigna'
        }
        
        if language in language_names:
            base_prompt += f"\nPlease respond in {language_names[language]} if possible."
        
        return base_prompt


class ChatUsageView(APIView):
    """Get chat usage statistics"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        user.reset_chat_queries()
        
        is_premium = user.is_premium()
        limit = 100 if is_premium else 5
        
        return Response({
            'queries_used_today': user.ai_chat_queries_today,
            'queries_limit': limit,
            'queries_remaining': limit - user.ai_chat_queries_today,
            'is_premium': is_premium,
            'last_query_date': user.last_chat_query_date
        })

