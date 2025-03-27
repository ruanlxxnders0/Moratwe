from django.urls import path
from . import views

app_name = 'events'

urlpatterns = [
    path('', views.home, name='home'),
    path('rsvp/accept/', views.rsvp_accept, name='rsvp_accept'),
    path('rsvp/decline/', views.rsvp_decline, name='rsvp_decline'),
    path('rsvp/register/', views.register_from_invitation, name='register_from_invitation'),
    path('<int:event_id>/', views.event_detail, name='event_detail'),
    path('<int:event_id>/update-rsvp/', views.update_rsvp, name='update_rsvp'),
] 