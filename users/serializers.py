from rest_framework import serializers
from django.contrib.auth import get_user_model
import re

User = get_user_model()


class CustomUserSerializer(serializers.ModelSerializer):
    """
    Serializer for the custom user model.
    """
    username = serializers.SerializerMethodField()
    phone_number = serializers.CharField(max_length=30, required=False, allow_blank=True)
    
    class Meta:
        model = User
        fields = ('id', 'email', 'username', 'first_name', 'last_name', 'phone_number', 'date_joined', 'is_active', 'is_organizer')
        read_only_fields = ('id', 'date_joined', 'is_active')
        extra_kwargs = {
            'phone_number': {'validators': []},  # Remove default unique validator
        }
    
    def get_username(self, obj):
        """
        Get a username for the user (either their first name or email).
        """
        if obj.first_name:
            return obj.first_name
        return obj.email.split('@')[0]
    
    def validate_phone_number(self, value):
        """
        Clean and validate phone number format and uniqueness.
        """
        if value:
            # Remove any non-digit characters except for leading +
            if value.startswith('+'):
                # Keep the leading + sign
                cleaned_number = '+' + re.sub(r'\D', '', value[1:])
            else:
                cleaned_number = re.sub(r'\D', '', value)
            
            # Add + prefix for international format if it looks like an international number
            if not cleaned_number.startswith('+') and len(cleaned_number) > 10:
                cleaned_number = '+' + cleaned_number
                
            # Validate length
            if not cleaned_number.startswith('+') and len(cleaned_number) < 10:
                raise serializers.ValidationError("Phone number must be at least 10 digits.")
            
            # Check for duplicate phone number (exclude current user if updating)
            existing_user_query = User.objects.filter(phone_number=cleaned_number)
            if self.instance:
                # If updating an existing user, exclude the current user from the check
                existing_user_query = existing_user_query.exclude(pk=self.instance.pk)
            
            if existing_user_query.exists():
                raise serializers.ValidationError("This phone number is already registered. Please use a different phone number.")
            
            return cleaned_number
        return value


class UserCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a new user.
    """
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    password_confirm = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    phone_number = serializers.CharField(max_length=30, required=False, allow_blank=True)
    
    class Meta:
        model = User
        fields = ('id', 'email', 'first_name', 'last_name', 'phone_number', 'is_organizer', 'password', 'password_confirm')
        read_only_fields = ('id',)
        extra_kwargs = {
            'phone_number': {'validators': []},  # Remove default unique validator
        }
    
    def validate_phone_number(self, value):
        """
        Clean and validate phone number format and uniqueness.
        """
        if value:
            # Remove any non-digit characters except for leading +
            if value.startswith('+'):
                # Keep the leading + sign
                cleaned_number = '+' + re.sub(r'\D', '', value[1:])
            else:
                cleaned_number = re.sub(r'\D', '', value)
            
            # Add + prefix for international format if it looks like an international number
            if not cleaned_number.startswith('+') and len(cleaned_number) > 10:
                cleaned_number = '+' + cleaned_number
                
            # Validate length
            if not cleaned_number.startswith('+') and len(cleaned_number) < 10:
                raise serializers.ValidationError("Phone number must be at least 10 digits.")
            
            # Check for duplicate phone number (exclude current user if updating)
            existing_user_query = User.objects.filter(phone_number=cleaned_number)
            if self.instance:
                # If updating an existing user, exclude the current user from the check
                existing_user_query = existing_user_query.exclude(pk=self.instance.pk)
            
            if existing_user_query.exists():
                raise serializers.ValidationError("This phone number is already registered. Please use a different phone number.")
            
            return cleaned_number
        return value
    
    def validate(self, attrs):
        """
        Validate that the passwords match.
        """
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})
        return attrs
    
    def create(self, validated_data):
        """
        Create and return a new user.
        """
        # Remove password_confirm from the data
        validated_data.pop('password_confirm')
        
        # Create the user
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            phone_number=validated_data.get('phone_number', ''),
            is_organizer=validated_data.get('is_organizer', False)
        )
        
        return user 