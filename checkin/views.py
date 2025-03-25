from django.shortcuts import render
from rest_framework import views, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .serializers import CheckInByQRCodeSerializer

class QRCodeCheckInView(views.APIView):
    """
    View for checking in attendees using QR codes.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CheckInByQRCodeSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            checkin_data = serializer.save()
            return Response(checkin_data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
