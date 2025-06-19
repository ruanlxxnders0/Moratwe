from django.shortcuts import render, get_object_or_404
from rest_framework import generics, permissions, status, views, parsers
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from users.serializers import UserCreateSerializer, CustomUserSerializer
from users.models import CustomUser
from events.models import Event, RSVP, BreakawaySession
from events.serializers import EventSerializer, BreakawaySessionSerializer
import logging
from django.utils import timezone
from django.contrib.auth import authenticate
from django.core.mail import send_mail
from django.conf import settings
import secrets
import string

logger = logging.getLogger(__name__)

# Simple in-memory storage for RSVPs and password reset tokens
EVENT_RSVPS = {}
PASSWORD_RESET_TOKENS = {}

def generate_reset_token():
    """Generate a secure random token for password reset."""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(64))

class RegisterView(views.APIView):
    """
    API view for registering a new user.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = UserCreateSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            user.is_active = True  # Ensure user is active
            user.save()
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': CustomUserSerializer(user).data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class TestAPIView(views.APIView):
    """
    Test API view to check if API is operational.
    """
    permission_classes = [permissions.AllowAny]
    
    def get(self, request):
        logger.info("TestAPIView accessed")
        return Response({
            'message': 'API is working!',
            'endpoints': [
                '/api/token/',
                '/api/token/refresh/',
                '/api/register/',
                '/api/users/me/',
                '/api/events/',
                '/api/events/<event_id>/',
                '/api/events/<event_id>/rsvp/',
                '/api/events/<event_id>/image/',
                '/api/events/<event_id>/breakaway-sessions/<session_id>/attend/',
                '/api/rsvps/'
            ]
        })

class AuthCheckView(views.APIView):
    """
    Simple view to check if authentication is working.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        return Response({
            'authenticated': True,
            'user_id': request.user.id,
            'username': request.user.username,
        })

class SimplifiedUserDetailsView(views.APIView):
    """
    Simplified user details view for debugging.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        logger.info(f"SimplifiedUserDetailsView.get called by user: {request.user}")
        logger.info(f"Request headers: {request.headers}")
        
        user = request.user
        return Response({
            'id': user.id,
            'email': user.email,
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'phone_number': user.phone_number,
            'date_joined': user.date_joined,
            'is_active': user.is_active,
            'is_organizer': user.is_organizer,
        })

class EventsListView(views.APIView):
    """
    List all events or create a new event.
    """
    permission_classes = [permissions.AllowAny]
    
    def get(self, request):
        # Create sample events if none exist
        if Event.objects.count() == 0:
            # Create or get the organizer
            organizer = CustomUser.objects.filter(is_organizer=True).first()
            if not organizer:
                organizer = CustomUser.objects.create_user(
                    email='organizer@example.com',
                    password='organizer123',
                    first_name='Event',
                    last_name='Organizer',
                    is_organizer=True
                )
            
            # Create sample events with all required fields
            Event.objects.create(
                title='Tech Conference 2024',
                description='Annual technology conference featuring the latest innovations',
                date=timezone.now() + timezone.timedelta(days=30),  # Set to future date
                location='Convention Center',
                organizer=organizer,
                is_active=True
            )
            
            Event.objects.create(
                title='Community Meetup',
                description='Monthly community gathering to discuss local initiatives',
                date=timezone.now() + timezone.timedelta(days=7),  # Set to near future
                location='Community Hall',
                organizer=organizer,
                is_active=True
            )
            
            Event.objects.create(
                title='Tech Workshop',
                description='Hands-on workshop on the latest technologies',
                date=timezone.now() + timezone.timedelta(days=14),  # Set to two weeks from now
                location='Innovation Hub',
                organizer=organizer,
                is_active=True
            )

        # Get all active events and serialize them
        events = Event.objects.filter(is_active=True).select_related('organizer')
        serializer = EventSerializer(events, many=True, context={'request': request})
        return Response(serializer.data)

class EventDetailView(views.APIView):
    """
    Retrieve a specific event.
    """
    permission_classes = [permissions.AllowAny]
    
    def get(self, request, event_id):
        event = get_object_or_404(Event.objects.select_related('organizer').prefetch_related('breakaways', 'breakaways__panelists'), id=event_id, is_active=True)
        serializer = EventSerializer(event, context={'request': request})
        return Response(serializer.data)

class EventRSVPView(views.APIView):
    """
    Handle event RSVPs.
    """
    permission_classes = [permissions.IsAuthenticated]  # Require authentication
    
    def post(self, request, event_id):
        try:
            event = get_object_or_404(Event, id=event_id, is_active=True)
            attending = request.data.get('attending', False)
            
            # Try to get existing RSVP
            rsvp = RSVP.objects.filter(event=event, user=request.user).first()
            
            if attending:
                if rsvp:
                    # User already RSVP'd
                    return Response({
                        'event_id': event_id,
                        'user_id': request.user.id,
                        'attending': True,
                        'status': 'already_confirmed',
                        'user_rsvpd': True
                    })
                else:
                    # Create new RSVP
                    rsvp = RSVP.objects.create(
                        event=event,
                        user=request.user,
                        checked_in=False
                    )
            else:
                # If not attending and RSVP exists, delete it
                if rsvp:
                    rsvp.delete()
                    rsvp = None
            
            return Response({
                'event_id': event_id,
                'user_id': request.user.id,
                'attending': bool(rsvp),
                'status': 'confirmed',
                'user_rsvpd': bool(rsvp)
            })
            
        except Exception as e:
            logger.error(f"Error in EventRSVPView: {str(e)}")
            return Response({
                'error': 'An error occurred while processing your RSVP',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class UserRSVPListView(views.APIView):
    """
    View to list all RSVPs for the authenticated user.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """
        Return a list of all RSVPs for the authenticated user.
        """
        rsvps = RSVP.objects.filter(user=request.user).select_related('event')
        data = []
        for rsvp in rsvps:
            event_data = {
                'id': rsvp.event.id,
                'title': rsvp.event.title,
                'description': rsvp.event.description,
                'date': rsvp.event.date,
                'location': rsvp.event.location,
                'is_active': rsvp.event.is_active,
                'is_past': rsvp.event.is_past,
                'created_at': rsvp.created_at,
                'checked_in': rsvp.checked_in,
            }
            data.append({
                'id': rsvp.id,
                'event': event_data,
                'created_at': rsvp.created_at,
                'checked_in': rsvp.checked_in,
            })
        return Response(data)

class CustomTokenObtainPairView(views.APIView):
    """
    Custom token view that uses email for authentication.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        email = request.data.get('email')
        password = request.data.get('password')

        if not email or not password:
            return Response(
                {'detail': 'Email and password are required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = CustomUser.objects.get(email=email)
            
            # Check if user is active
            if not user.is_active:
                return Response(
                    {'detail': 'User account is not active.'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            # Check password
            if not user.check_password(password):
                return Response(
                    {'detail': 'Invalid password.'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            # Generate tokens
            refresh = RefreshToken.for_user(user)
            
            # Return tokens and user data
            return Response({
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'is_active': user.is_active,
                    'is_organizer': user.is_organizer,
                }
            })
            
        except CustomUser.DoesNotExist:
            return Response(
                {'detail': 'No user found with this email address.'},
                status=status.HTTP_401_UNAUTHORIZED
            )

class PasswordResetRequestView(views.APIView):
    """
    View to handle password reset requests.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response(
                {'detail': 'Email is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = CustomUser.objects.get(email=email)
            
            # Generate and store reset token
            token = generate_reset_token()
            PASSWORD_RESET_TOKENS[token] = {
                'user_id': user.id,
                'timestamp': timezone.now()
            }

            # Send reset email
            reset_url = f"moratwe://reset-password?token={token}"
            email_body = f"""
            Hello {user.first_name or user.email},

            You have requested to reset your password. Please click the link below to reset your password:

            {reset_url}

            IMPORTANT: This link must be opened on a mobile device (iPhone or Android) where the Moratwe app is installed. The link will not work on desktop computers or devices without the app.

            If you don't have the Moratwe app installed, please download it from the App Store (iOS) or Google Play Store (Android) first, then click the reset link.

            If you did not request this password reset, please ignore this email.

            Best regards,
            Moratwe Team
            """

            send_mail(
                'Password Reset Request',
                email_body,
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )

            return Response({
                'detail': 'Password reset instructions have been sent to your email.'
            })

        except CustomUser.DoesNotExist:
            # For security reasons, we return the same message even if the user doesn't exist
            return Response({
                'detail': 'Password reset instructions have been sent to your email.'
            })

class PasswordResetConfirmView(views.APIView):
    """
    View to handle password reset confirmations.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        token = request.data.get('token')
        new_password = request.data.get('new_password')

        if not token or not new_password:
            return Response(
                {'detail': 'Token and new password are required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if token exists and is valid
        token_data = PASSWORD_RESET_TOKENS.get(token)
        if not token_data:
            return Response(
                {'detail': 'Invalid or expired token.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check token expiry (24 hours)
        token_age = timezone.now() - token_data['timestamp']
        if token_age.total_seconds() > 24 * 60 * 60:
            PASSWORD_RESET_TOKENS.pop(token, None)
            return Response(
                {'detail': 'Token has expired.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = CustomUser.objects.get(id=token_data['user_id'])
            user.set_password(new_password)
            user.save()

            # Remove used token
            PASSWORD_RESET_TOKENS.pop(token, None)

            return Response({
                'detail': 'Password has been reset successfully.'
            })

        except CustomUser.DoesNotExist:
            return Response(
                {'detail': 'User not found.'},
                status=status.HTTP_400_BAD_REQUEST
            )

class BreakawaySessionAttendanceView(views.APIView):
    """
    Toggle attendance for a breakaway session.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, event_id, session_id):
        # Get the event and session or return 404
        event = get_object_or_404(Event, id=event_id, is_active=True)
        session = get_object_or_404(BreakawaySession, id=session_id, event=event)
        
        # Check if the user has RSVP'd to the event
        try:
            rsvp = RSVP.objects.get(event=event, user=request.user)
        except RSVP.DoesNotExist:
            return Response(
                {'detail': 'You must RSVP to the event before selecting sessions.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        attending = request.data.get('attending', False)
        
        # Add or remove the session
        if attending:
            rsvp.selected_sessions.add(session)
        else:
            rsvp.selected_sessions.remove(session)
        
        # Get all selected sessions for the user
        selected_sessions = rsvp.selected_sessions.all()
        
        # Serialize the session data with context
        serializer = BreakawaySessionSerializer(session, context={'request': request})
        
        # Return updated session with attendance status
        return Response({
            'message': 'Attendance updated successfully',
            'session': serializer.data,
            'attending': attending,
            'selected_session_count': selected_sessions.count()
        })

class EventImageUploadView(views.APIView):
    """
    Upload an image for an event.
    """
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser]
    
    def post(self, request, event_id):
        event = get_object_or_404(Event, id=event_id)
        
        # Check if the user is the organizer of the event
        if event.organizer != request.user and not request.user.is_staff:
            return Response(
                {'detail': 'You must be the organizer or staff to upload an image.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get the image from the request
        image = request.data.get('image')
        if not image:
            return Response(
                {'detail': 'No image provided.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update the event with the new image
        event.image = image
        event.save()
        
        # Return the updated event data
        serializer = EventSerializer(event, context={'request': request})
        return Response(serializer.data)
