from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenRefreshView,
    TokenVerifyView,
)
from .views import (
    RegisterView, 
    TestAPIView, 
    AuthCheckView,
    EventsListView, 
    EventDetailView,
    EventRSVPView,
    UserRSVPListView,
    CustomTokenObtainPairView,
    SimplifiedUserDetailsView,
    PasswordResetRequestView,
    PasswordResetConfirmView,
    BreakawaySessionAttendanceView,
    EventImageUploadView
)
from users.views import UserViewSet

# Create a router and register our viewsets with it
router = DefaultRouter()
router.register(r'users', UserViewSet)

urlpatterns = [
    # Test endpoints
    path('test/', TestAPIView.as_view(), name='test-api'),
    path('auth-check/', AuthCheckView.as_view(), name='auth-check'),
    
    # Authentication endpoints
    path('auth/', include('rest_framework.urls', namespace='rest_framework')),
    path('token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('register/', RegisterView.as_view(), name='register'),
    
    # Events endpoints
    path('events/', EventsListView.as_view(), name='events-list'),
    path('events/<int:event_id>/', EventDetailView.as_view(), name='event-detail'),
    path('events/<int:event_id>/rsvp/', EventRSVPView.as_view(), name='event-rsvp'),
    path('events/<int:event_id>/image/', EventImageUploadView.as_view(), name='event-image-upload'),
    path('events/<int:event_id>/breakaway-sessions/<int:session_id>/attend/', 
         BreakawaySessionAttendanceView.as_view(), name='breakaway-session-attendance'),
    
    # RSVPs endpoint
    path('rsvps/', UserRSVPListView.as_view(), name='user-rsvps'),
    
    # Include router URLs last to avoid conflicts
    path('', include(router.urls)),
    
    # Password reset endpoints
    path('password-reset/', PasswordResetRequestView.as_view(), name='password-reset-request'),
    path('password-reset/confirm/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
] 