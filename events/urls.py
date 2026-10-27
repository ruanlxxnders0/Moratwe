from django.urls import path
from . import views

app_name = 'events'

urlpatterns = [
    path('', views.home, name='home'),
    path('rsvp/accept/', views.rsvp_accept, name='rsvp_accept'),
    path('rsvp/decline/', views.rsvp_decline, name='rsvp_decline'),
    path('rsvp/register/', views.register_from_invitation, name='register_from_invitation'),
    path('<int:event_id>/register/', views.smme_register, name='smme_register'),
    path('smme-rsvp/<uuid:token>/<str:action>/', views.smme_rsvp, name='smme_rsvp'),
    path('smme-rsvp/<uuid:token>/qr.png', views.smme_qr_image, name='smme_qr'),
    path('<int:event_id>/checkin/', views.smme_checkin, name='smme_checkin'),
    path('<int:event_id>/checkin/export/', views.smme_checkin_export, name='smme_checkin_export'),
    path('<int:event_id>/rsvp/', views.smme_rsvp_request, name='smme_rsvp_request'),
    path('<int:event_id>/register/success/', views.smme_register_success, name='smme_register_success'),
    path('<int:event_id>/', views.event_detail, name='event_detail'),
    path('<int:event_id>/update-rsvp/', views.update_rsvp, name='update_rsvp'),
    path('<int:event_id>/edit-rsvp/', views.edit_rsvp, name='edit_rsvp'),
    path('<int:event_id>/calendar.ics', views.event_calendar_ics, name='event_calendar_ics'),
] 