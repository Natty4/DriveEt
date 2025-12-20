# api/views/ai_chat.py
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
import google.generativeai as genai
from django.conf import settings
import logging

from core.models import AIChatHistory, ResourceTransaction
from core.authentication import TelegramAuthenticationBackend
from core.services import BundleService

logger = logging.getLogger(__name__)


class AIChatView(APIView):
    """
    AI Chat with bundle consumption
    """
    authentication_classes = [TelegramAuthenticationBackend]
    permission_classes = [IsAuthenticated]
    
    def __init__(self):
        super().__init__()
        try:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.model = genai.GenerativeModel('gemini-pro')
        except Exception as e:
            logger.error(f"Failed to initialize Gemini AI: {str(e)}")
            self.model = None
    
    def post(self, request):
        """
        POST /api/v1/ai/chat/
        Ask AI a question - consumes 1 chat message
        """
        if not self.model:
            return Response({
                'error': 'AI service is currently unavailable'
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
        question = request.data.get('question', '').strip()
        session_id = request.data.get('session_id', 'default')
        
        if not question:
            return Response({
                'error': 'Question is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Consume chat resource
        success, bundle, error = BundleService.consume_resource(
            user=request.user,
            resource_type=ResourceTransaction.ResourceType.CHAT,
            quantity=1,
            description=f"AI Chat: {question[:50]}..."
        )
        
        if not success:
            return Response({
                'error': 'Cannot use AI chat',
                'detail': error,
                'remaining_resources': bundle.get_remaining_resources() if bundle else None
            }, status=status.HTTP_402_PAYMENT_REQUIRED)
        
        try:
            # Create system prompt
            system_prompt = """
            You are an expert on Ethiopian driving laws, traffic rules, road signs, and vehicle regulations.
            Provide accurate, concise, and helpful information specific to Ethiopia.
            
            Guidelines:
            1. Only answer questions related to driving in Ethiopia
            2. Cite specific Ethiopian laws and regulations when possible
            3. Mention relevant road signs and their meanings
            4. Provide practical advice for Ethiopian driving conditions
            5. If you don't know something, say so
            6. Keep answers clear and straightforward
            7. Use Ethiopian context (cities like Addis Ababa, Bahir Dar, etc.)
            
            Question: {question}
            """
            
            # Generate response
            response = self.model.generate_content(
                system_prompt.format(question=question),
                generation_config={
                    'temperature': 0.7,
                    'top_p': 0.8,
                    'top_k': 40,
                    'max_output_tokens': 500,
                }
            )
            
            # Save chat history
            chat_history = AIChatHistory.objects.create(
                user=request.user,
                session_id=session_id,
                question=question,
                answer=response.text,
                tokens_used=len(response.text.split())
            )
            
            return Response({
                'success': True,
                'answer': response.text,
                'chat_id': str(chat_history.id),
                'session_id': session_id,
                'created_at': chat_history.created_at.isoformat(),
                'remaining_chats': bundle.chats_remaining if bundle else 0,
                'daily_chats_remaining': max(0, bundle.bundle_definition.daily_chat_limit - bundle.daily_chats_used) if bundle else 0
            })
            
        except Exception as e:
            logger.error(f"AI chat error: {str(e)}")
            return Response({
                'error': 'Failed to get AI response',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

























































































# from rest_framework import status
# from rest_framework.response import Response
# from rest_framework.views import APIView
# from rest_framework.permissions import IsAuthenticated
# import google.generativeai as genai
# from django.conf import settings
# import logging

# from core.models import AIChatHistory
# from core.authentication import TelegramAuthenticationBackend
# from core.permissions import IsProUser

# logger = logging.getLogger(__name__)


# class AIChatView(APIView):
#     """
#     AI Chat for Pro users to ask questions about driving rules
#     """
#     authentication_classes = [TelegramAuthenticationBackend]
#     permission_classes = [IsAuthenticated, IsProUser]
    
#     def __init__(self):
#         super().__init__()
#         # Initialize Gemini AI
#         try:
#             genai.configure(api_key=settings.GEMINI_API_KEY)
#             self.model = genai.GenerativeModel('gemini-pro')
#         except Exception as e:
#             logger.error(f"Failed to initialize Gemini AI: {str(e)}")
#             self.model = None
    
#     def post(self, request):
#         """
#         POST /api/v1/ai/chat/
#         Ask AI a question about Ethiopian driving rules
#         """
#         if not self.model:
#             return Response({
#                 'error': 'AI service is currently unavailable'
#             }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
#         question = request.data.get('question', '').strip()
#         session_id = request.data.get('session_id', 'default')
        
#         if not question:
#             return Response({
#                 'error': 'Question is required'
#             }, status=status.HTTP_400_BAD_REQUEST)
        
#         try:
#             # Create system prompt for Ethiopian driving context
#             system_prompt = """
#             You are an expert on Ethiopian driving laws, traffic rules, road signs, and vehicle regulations.
#             Provide accurate, concise, and helpful information specific to Ethiopia.
            
#             Guidelines:
#             1. Only answer questions related to driving in Ethiopia
#             2. Cite specific Ethiopian laws and regulations when possible
#             3. Mention relevant road signs and their meanings
#             4. Provide practical advice for Ethiopian driving conditions
#             5. If you don't know something, say so
#             6. Keep answers clear and straightforward
#             7. Use Ethiopian context (cities like Addis Ababa, Bahir Dar, etc.)
            
#             Question: {question}
#             """
            
#             # Generate response
#             response = self.model.generate_content(
#                 system_prompt.format(question=question),
#                 generation_config={
#                     'temperature': 0.7,
#                     'top_p': 0.8,
#                     'top_k': 40,
#                     'max_output_tokens': 500,
#                 }
#             )
            
#             # Save chat history
#             chat_history = AIChatHistory.objects.create(
#                 user=request.user,
#                 session_id=session_id,
#                 question=question,
#                 answer=response.text,
#                 tokens_used=len(response.text.split())  # Approximate token count
#             )
            
#             return Response({
#                 'success': True,
#                 'answer': response.text,
#                 'chat_id': str(chat_history.id),
#                 'session_id': session_id,
#                 'created_at': chat_history.created_at.isoformat()
#             })
            
#         except Exception as e:
#             logger.error(f"AI chat error: {str(e)}")
#             return Response({
#                 'error': 'Failed to get AI response',
#                 'detail': str(e)
#             }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
#     def get(self, request):
#         """
#         GET /api/v1/ai/chat/
#         Get chat history for a session
#         """
#         session_id = request.query_params.get('session_id', 'default')
        
#         chats = AIChatHistory.objects.filter(
#             user=request.user,
#             session_id=session_id
#         ).order_by('created_at')[:50]  # Limit to last 50 messages
        
#         chat_data = []
#         for chat in chats:
#             chat_data.append({
#                 'id': str(chat.id),
#                 'question': chat.question,
#                 'answer': chat.answer,
#                 'created_at': chat.created_at.isoformat()
#             })
        
#         return Response({
#             'session_id': session_id,
#             'chats': chat_data,
#             'total_messages': len(chat_data)
#         })