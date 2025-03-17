from rest_framework import serializers
from .models import CheckIn
from events.models import RSVP
from events.serializers import RSVPSerializer
from users.serializers import UserSerializer


class CheckInSerializer(serializers.ModelSerializer):
    """
    Serializer for the CheckIn model.
    """
    checked_in_by = UserSerializer(read_only=True)
    rsvp = RSVPSerializer(read_only=True)
    rsvp_id = serializers.PrimaryKeyRelatedField(
        queryset=RSVP.objects.filter(checked_in=False),
        write_only=True,
        source='rsvp'
    )
    event_title = serializers.CharField(source='rsvp.event.title', read_only=True)
    user_email = serializers.CharField(source='rsvp.user.email', read_only=True)
    user_full_name = serializers.CharField(source='rsvp.user.get_full_name', read_only=True)
    
    class Meta:
        model = CheckIn
        fields = (
            'id', 'rsvp', 'rsvp_id', 'checked_in_at', 'checked_in_by', 
            'event_title', 'user_email', 'user_full_name'
        )
        read_only_fields = (
            'id', 'checked_in_at', 'checked_in_by', 
            'event_title', 'user_email', 'user_full_name'
        )
    
    def create(self, validated_data):
        """
        Create and return a new check-in.
        """
        # Set the checked_in_by field to the current user
        validated_data['checked_in_by'] = self.context['request'].user
        return super().create(validated_data)
    
    def validate_rsvp_id(self, value):
        """
        Validate that the RSVP has not already been checked in.
        """
        if value.checked_in:
            raise serializers.ValidationError("This attendee has already checked in.")
        return value


class CheckInByQRCodeSerializer(serializers.Serializer):
    """
    Serializer for checking in by QR code.
    """
    qr_code_data = serializers.UUIDField(required=True)
    
    def validate_qr_code_data(self, value):
        """
        Validate that the QR code data is valid and has not been used for check-in.
        """
        try:
            # Find the RSVP by qr_code_data
            rsvp = RSVP.objects.get(qr_code_data=value)
        except RSVP.DoesNotExist:
            raise serializers.ValidationError("Invalid QR code.")
        
        # Check if the RSVP has already been checked in
        if rsvp.checked_in:
            raise serializers.ValidationError("This attendee has already checked in.")
        
        return value
    
    def create(self, validated_data):
        """
        Create a check-in using the provided QR code data.
        """
        qr_code_data = validated_data.get('qr_code_data')
        rsvp = RSVP.objects.get(qr_code_data=qr_code_data)
        
        # Create the check-in
        checkin = CheckIn.objects.create(
            rsvp=rsvp,
            checked_in_by=self.context['request'].user
        )
        
        return checkin 