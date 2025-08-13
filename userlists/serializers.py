from rest_framework import serializers
from .models import UserList, Invitee


class InviteeSerializer(serializers.ModelSerializer):
    """
    Serializer for the Invitee model.
    """
    guest_category_display = serializers.CharField(source='get_guest_category_display', read_only=True)
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    
    class Meta:
        model = Invitee
        fields = (
            'id', 'user_list', 'email', 'first_name', 'last_name', 'full_name',
            'mobile_number', 'guest_category', 'guest_category_display',
            'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'guest_category_display', 'full_name')


class UserListSerializer(serializers.ModelSerializer):
    """
    Serializer for the UserList model.
    """
    invitees = InviteeSerializer(many=True, read_only=True)
    invitee_count = serializers.SerializerMethodField()
    vip_count = serializers.SerializerMethodField()
    vvip_count = serializers.SerializerMethodField()
    regular_count = serializers.SerializerMethodField()
    
    class Meta:
        model = UserList
        fields = (
            'id', 'name', 'description', 'invitees', 'invitee_count',
            'vip_count', 'vvip_count', 'regular_count',
            'created_at', 'updated_at'
        )
        read_only_fields = (
            'id', 'created_at', 'updated_at', 'invitee_count',
            'vip_count', 'vvip_count', 'regular_count'
        )
    
    def get_invitee_count(self, obj):
        """Get total number of invitees in this list."""
        return obj.invitees.count()
    
    def get_vip_count(self, obj):
        """Get number of VIP invitees in this list."""
        return obj.invitees.filter(guest_category='vip').count()
    
    def get_vvip_count(self, obj):
        """Get number of VVIP invitees in this list."""
        return obj.invitees.filter(guest_category='vvip').count()
    
    def get_regular_count(self, obj):
        """Get number of Regular invitees in this list."""
        return obj.invitees.filter(guest_category='regular').count()
