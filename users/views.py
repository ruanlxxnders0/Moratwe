from django.shortcuts import render
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import action
from .models import CustomUser
from .serializers import CustomUserSerializer
from django.db import IntegrityError
import logging

logger = logging.getLogger(__name__)

# Create your views here.

class UserViewSet(viewsets.ModelViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer
    
    def get_permissions(self):
        """
        Override to set custom permissions based on the action.
        """
        if self.action == 'create':
            # Allow anyone to register
            permission_classes = [permissions.AllowAny]
        else:
            # Require authentication for other actions
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    def create(self, request, *args, **kwargs):
        """
        Override create to handle duplicate phone number errors gracefully.
        """
        try:
            return super().create(request, *args, **kwargs)
        except IntegrityError as e:
            # Handle database integrity errors (like duplicate phone numbers)
            if 'phone_number' in str(e).lower():
                return Response({
                    'phone_number': ['This phone number is already registered. Please use a different phone number.']
                }, status=status.HTTP_400_BAD_REQUEST)
            elif 'email' in str(e).lower():
                return Response({
                    'email': ['This email address is already registered. Please use a different email address.']
                }, status=status.HTTP_400_BAD_REQUEST)
            else:
                # Log the unexpected integrity error
                logger.error(f"Integrity error during user creation: {e}")
                return Response({
                    'error': ['A user with this information already exists. Please check your details.']
                }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            # Log any other unexpected errors
            logger.error(f"Unexpected error during user creation: {e}")
            return Response({
                'error': ['An unexpected error occurred during registration. Please try again.']
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get', 'put', 'delete'])
    def me(self, request):
        """
        Return, update, or delete the authenticated user's details.
        """
        if request.method == 'GET':
            logger.info(f"UserViewSet.me GET called by user: {request.user}")
            logger.info(f"Request headers: {request.headers}")
            serializer = self.get_serializer(request.user)
            return Response(serializer.data)
        elif request.method == 'PUT':
            logger.info(f"UserViewSet.me PUT called by user: {request.user}")
            logger.info(f"Request data: {request.data}")
            serializer = self.get_serializer(request.user, data=request.data, partial=True)
            if serializer.is_valid():
                try:
                    serializer.save()
                    return Response(serializer.data)
                except IntegrityError as e:
                    # Handle database integrity errors (like duplicate phone numbers)
                    if 'phone_number' in str(e).lower():
                        return Response({
                            'phone_number': ['This phone number is already registered. Please use a different phone number.']
                        }, status=status.HTTP_400_BAD_REQUEST)
                    elif 'email' in str(e).lower():
                        return Response({
                            'email': ['This email address is already registered. Please use a different email address.']
                        }, status=status.HTTP_400_BAD_REQUEST)
                    else:
                        # Log the unexpected integrity error
                        logger.error(f"Integrity error during user profile update: {e}")
                        return Response({
                            'error': ['A user with this information already exists. Please check your details.']
                        }, status=status.HTTP_400_BAD_REQUEST)
                except Exception as e:
                    # Log any other unexpected errors
                    logger.error(f"Unexpected error during user profile update: {e}")
                    return Response({
                        'error': ['An unexpected error occurred during profile update. Please try again.']
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        elif request.method == 'DELETE':
            logger.info(f"UserViewSet.me DELETE called by user: {request.user}")
            
            # Get user data for logging/deletion confirmation
            user_email = request.user.email
            
            # Delete the user account
            request.user.delete()
            
            logger.info(f"User account deleted: {user_email}")
            
            return Response(
                {"message": "Account successfully deleted"}, 
                status=status.HTTP_204_NO_CONTENT
            )

class CustomUserDetailsView(APIView):
    """
    View to retrieve and update the authenticated user's details.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """
        Return the authenticated user's details.
        """
        logger.info(f"CustomUserDetailsView.get called by user: {request.user}")
        logger.info(f"Request headers: {request.headers}")
        
        serializer = CustomUserSerializer(request.user)
        return Response(serializer.data)

    def put(self, request):
        """
        Update the authenticated user's details.
        """
        logger.info(f"CustomUserDetailsView.put called by user: {request.user}")
        logger.info(f"Request data: {request.data}")
        
        serializer = CustomUserSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

def privacy_policy(request):
    return render(request, 'privacy_policy.html')
