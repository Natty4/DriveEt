# core/responses.py

from rest_framework.response import Response
from rest_framework import status

class APIResponse:
    @staticmethod
    def success(data=None, message="Success", status_code=status.HTTP_200_OK):
        payload = {
            "success": True,
            "message": message,
            "data": data or {}
        }
        return Response(payload, status=status_code)

    @staticmethod
    def created(data=None, message="Resource created successfully"):
        return APIResponse.success(data, message, status_code=status.HTTP_201_CREATED)

    @staticmethod
    def error(message="An error occurred", errors=None, status_code=status.HTTP_400_BAD_REQUEST):
        payload = {
            "success": False,
            "message": message,
            "errors": errors or {}
        }
        return Response(payload, status=status_code)

    @staticmethod
    def not_found(message="Resource not found"):
        return APIResponse.error(message, status_code=status.HTTP_404_NOT_FOUND)

    @staticmethod
    def forbidden(message="You do not have permission to perform this action"):
        return APIResponse.error(message, status_code=status.HTTP_403_FORBIDDEN)

    @staticmethod
    def unauthorized(message="Authentication required"):
        return APIResponse.error(message, status_code=status.HTTP_401_UNAUTHORIZED)
    
    