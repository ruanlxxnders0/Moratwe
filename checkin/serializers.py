from django.utils import timezone
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
    Serializer for checking in by QR code. Accepts member RSVP codes and confirmed SMME codes.
    """
    qr_code_data = serializers.UUIDField(required=True)

    def validate_qr_code_data(self, value):
        from events.models import SMMERegistration
        rsvp = RSVP.objects.filter(qr_code_data=value).first()
        if rsvp:
            if rsvp.checked_in:
                raise serializers.ValidationError("This attendee has already been checked in.")
            self._rsvp = rsvp
            return value
        reg = SMMERegistration.objects.select_related('event').filter(
            rsvp_token=value, rsvp_status='confirmed').first()
        if reg is None:
            raise serializers.ValidationError("Invalid QR code.")
        if reg.attended_at:
            raise serializers.ValidationError("This attendee has already been checked in.")
        self._smme = reg
        return value

    def create(self, validated_data):
        user = self.context['request'].user
        reg = getattr(self, '_smme', None)
        if reg is not None:
            reg.attended_at = timezone.now()
            reg.attended_marked_by = user
            reg.save(update_fields=['attended_at', 'attended_marked_by', 'updated_at'])
            return {
                'type': 'smme',
                'name': f"{reg.name} {reg.surname}",
                'company': reg.company,
                'region': reg.get_region_display(),
                'event_title': reg.event.title,
                'checked_in_at': reg.attended_at,
            }
        checkin = CheckIn.objects.create(rsvp=self._rsvp, checked_in_by=user)
        return CheckInSerializer(checkin).data
