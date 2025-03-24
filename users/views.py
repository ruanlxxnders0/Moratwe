from django.shortcuts import render
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import action
from .models import CustomUser
from .serializers import CustomUserSerializer
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
    
    @action(detail=False, methods=['get', 'put'])
    def me(self, request):
        """
        Return or update the authenticated user's details.
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
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

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
