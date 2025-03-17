from rest_framework import serializers
from .models import Event, EventRSVP
from users.serializers import CustomUserSerializer

class EventSerializer(serializers.ModelSerializer):
    organizer = CustomUserSerializer(read_only=True)
    user_rsvpd = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = ['id', 'title', 'description', 'start_date', 'end_date', 'location', 
                 'image_url', 'is_public', 'organizer', 'user_rsvpd']

    def get_user_rsvpd(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            try:
                rsvp = EventRSVP.objects.get(event=obj, user=request.user)
                return rsvp.attending
            except EventRSVP.DoesNotExist:
                return False
        return False

class EventRSVPSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventRSVP
        fields = ['id', 'event', 'user', 'attending', 'created_at', 'updated_at']
        read_only_fields = ['user'] 