from rest_framework import serializers
from .models import CheckIn
from events.models import RSVP
from events.serializers import RSVPSerializer
from users.serializers import CustomUserSerializer


class CheckInSerializer(serializers.ModelSerializer):
    """
    Serializer for the CheckIn model.
    """
    checked_in_by = CustomUserSerializer(read_only=True)
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
        validated_data['checked_in_by'] = self.context['request'].user
        return super().create(validated_data)
    
    def validate_rsvp_id(self, value):
        if value.checked_in:
            raise serializers.ValidationError("This attendee has already checked in.")
        return value


class CheckInByQRCodeSerializer(serializers.Serializer):
    """
    Serializer for checking in by QR code.
    """
    qr_code_data = serializers.UUIDField(required=True)
    
    def validate_qr_code_data(self, value):
        try:
            rsvp = RSVP.objects.get(qr_code_data=value)
        except RSVP.DoesNotExist:
            raise serializers.ValidationError("Invalid QR code.")
        
        if rsvp.checked_in:
            raise serializers.ValidationError("This attendee has already been checked in.")
        
        return value
    
    def create(self, validated_data):
        qr_code_data = validated_data.get('qr_code_data')
        rsvp = RSVP.objects.get(qr_code_data=qr_code_data)
        
        checkin = CheckIn.objects.create(
            rsvp=rsvp,
            checked_in_by=self.context['request'].user
        )
        
        return CheckInSerializer(checkin).data 