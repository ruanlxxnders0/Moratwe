from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q

UserModel = get_user_model()

class EmailBackend(ModelBackend):
    """
    Custom authentication backend that allows login with email address
    and is case-insensitive.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        Authenticate a user based on email address as the user identifier.
        The username parameter is actually the email in this case.
        """
        try:
            # Case-insensitive match for email
            email = username.lower() if username else None
            user = UserModel.objects.filter(Q(email__iexact=email)).first()
            
            if user and user.check_password(password):
                return user
        except Exception as e:
            # Handle exceptions like type errors or validation errors
            return None
            
        return None 