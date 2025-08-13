from rest_framework import serializers
from .models import Event, BreakawaySession, RSVP, EmailTemplate
from users.serializers import CustomUserSerializer
from django.contrib.auth import get_user_model
from django.utils import timezone
import qrcode
from io import BytesIO
from django.core.files.base import ContentFile
import uuid

User = get_user_model()


class EmailTemplateSerializer(serializers.ModelSerializer):
    """
    Serializer for the EmailTemplate model.
    """
    guest_category_display = serializers.CharField(source='get_guest_category_display', read_only=True)
    
    class Meta:
        model = EmailTemplate
        fields = (
            'id', 'name', 'subject', 'content', 'guest_category', 'guest_category_display',
            'is_default', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'guest_category_display')


class BreakawaySessionSerializer(serializers.ModelSerializer):
    """
    Serializer for the BreakawaySession model.
    """
    panelists = CustomUserSerializer(many=True, read_only=True)
    panelist_ids = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(is_organizer=True),
        write_only=True,
        many=True,
        required=False,
        source='panelists'
    )
    user_attending = serializers.SerializerMethodField()
    
    class Meta:
        model = BreakawaySession
        fields = (
            'id', 'event', 'title', 'description', 'start_time', 'end_time',
            'max_attendees', 'panelists', 'panelist_ids', 'user_attending'
        )
        read_only_fields = ('id',)
    
    def get_user_attending(self, obj):
        """
        Check if the current user is attending this session.
        """
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            # Get the user's RSVP for the event
            rsvp = RSVP.objects.filter(event=obj.event, user=request.user).first()
            if rsvp:
                # Check if this session is in the user's selected sessions
                return rsvp.selected_sessions.filter(id=obj.id).exists()
        return False


class EventSerializer(serializers.ModelSerializer):
    """
    Serializer for the Event model.
    """
    organizer = CustomUserSerializer(read_only=True)
    organizer_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(is_organizer=True),
        write_only=True,
        required=False,
        source='organizer'
    )
    breakaways = BreakawaySessionSerializer(many=True, read_only=True)
    is_past = serializers.BooleanField(read_only=True)
    date = serializers.DateTimeField(required=True)
    location = serializers.CharField(required=True)
    title = serializers.CharField(required=True)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    organizer_name = serializers.SerializerMethodField()
    user_rsvpd = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()
    qr_code_data = serializers.SerializerMethodField()
    
    class Meta:
        model = Event
        fields = (
            'id', 'title', 'description', 'location', 'date',
            'organizer', 'organizer_id', 'created_at', 'updated_at', 
            'is_active', 'is_past', 'breakaways', 'organizer_name',
            'user_rsvpd', 'image', 'image_url', 'qr_code_data'
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'is_past', 'image_url')
    
    def get_organizer_name(self, obj):
        """
        Get a display name for the organizer.
        """
        if obj.organizer:
            if obj.organizer.first_name and obj.organizer.last_name:
                return f"{obj.organizer.first_name} {obj.organizer.last_name}"
            return obj.organizer.email.split('@')[0]
        return "Unknown Organizer"
    
    def get_user_rsvpd(self, obj):
        """
        Check if the current user has RSVP'd for this event.
        """
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return RSVP.objects.filter(event=obj, user=request.user).exists()
        return False
    
    def get_image_url(self, obj):
        """
        Get the absolute URL of the event image.
        """
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
        return None
    
    def get_qr_code_data(self, obj):
        """
        Get the QR code data for the current user's RSVP.
        """
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            rsvp = RSVP.objects.filter(event=obj, user=request.user).first()
            if rsvp:
                return rsvp.qr_code_data
        return None
    
    def validate(self, data):
        """
        Validate that all required fields are present and non-null.
        """
        if not data.get('title'):
            raise serializers.ValidationError("Title is required")
        if not data.get('date'):
            raise serializers.ValidationError("Date is required")
        if not data.get('location'):
            raise serializers.ValidationError("Location is required")
        return data
    
    def create(self, validated_data):
        """
        Create and return a new event.
        """
        # If organizer is not provided, set it to the current user
        if 'organizer' not in validated_data and self.context.get('request'):
            user = self.context['request'].user
            if user.is_organizer:
                validated_data['organizer'] = user
            else:
                raise serializers.ValidationError("Only organizers can create events.")
        
        return super().create(validated_data)


class RSVPSerializer(serializers.ModelSerializer):
    """
    Serializer for the RSVP model.
    """
    user = CustomUserSerializer(read_only=True)
    event = EventSerializer(read_only=True)
    event_id = serializers.PrimaryKeyRelatedField(
        queryset=Event.objects.filter(is_active=True),
        write_only=True,
        source='event'
    )
    selected_sessions = BreakawaySessionSerializer(many=True, read_only=True)
    session_ids = serializers.PrimaryKeyRelatedField(
        queryset=BreakawaySession.objects.all(),
        write_only=True,
        many=True,
        required=False,
        source='selected_sessions'
    )
    qr_code_url = serializers.SerializerMethodField()
    
    class Meta:
        model = RSVP
        fields = (
            'id', 'event', 'event_id', 'user', 'status', 'response_date', 'qr_code', 'qr_code_url', 'qr_code_data',
            'selected_sessions', 'session_ids', 'created_at', 'checked_in', 'number_of_guests', 'dietary_requirements'
        )
        read_only_fields = ('id', 'user', 'qr_code', 'qr_code_data', 'created_at', 'checked_in', 'response_date')
    
    def get_qr_code_url(self, obj):
        """
        Get the URL of the QR code.
        """
        if obj.qr_code:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.qr_code.url)
        return None
    
    def create(self, validated_data):
        """
        Create and return a new RSVP.
        """
        # Set the user field to the current user
        validated_data['user'] = self.context['request'].user
        
        # If no status is provided, default to 'accepted' for API-created RSVPs
        if 'status' not in validated_data:
            validated_data['status'] = 'accepted'
            validated_data['response_date'] = timezone.now()
            validated_data['is_registered_user'] = True
        
        # Create the RSVP
        rsvp = super().create(validated_data)
        
        # QR code is generated automatically in the model's save method
        
        return rsvp
    
    def validate_event_id(self, value):
        """
        Validate that the event is active and not in the past.
        """
        if not value.is_active:
            raise serializers.ValidationError("Cannot RSVP for an inactive event.")
        
        if value.is_past:
            raise serializers.ValidationError("Cannot RSVP for a past event.")
        
        # Check if the user is already registered for this event
        user = self.context['request'].user
        if RSVP.objects.filter(event=value, user=user).exists():
            raise serializers.ValidationError("You have already RSVP'd for this event.")
        
        return value
    
    def validate_session_ids(self, value):
        """
        Validate that the selected sessions belong to the event.
        """
        event_id = self.initial_data.get('event_id')
        if event_id and value:
            event = Event.objects.get(pk=event_id)
            for session in value:
                if session.event.id != event.id:
                    raise serializers.ValidationError(
                        f"Session '{session.title}' does not belong to the selected event."
                    )
        
        return value 