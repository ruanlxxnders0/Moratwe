from django.contrib import admin
from django.urls import path
from django.shortcuts import get_object_or_404, render
from django.http import JsonResponse
from django.utils.translation import gettext_lazy as _
from django.db.models import Count, Q
from django.utils import timezone
from datetime import datetime, timedelta
from .models import CheckIn
from events.models import Event, RSVP


@admin.register(CheckIn)
class CheckInAdmin(admin.ModelAdmin):
    list_display = ('rsvp', 'checked_in_at', 'checked_in_by', 'event_title', 'user_email')
    list_filter = ('checked_in_at', 'rsvp__event')
    search_fields = ('rsvp__user__email', 'rsvp__event__title', 'rsvp__user__first_name', 'rsvp__user__last_name')
    date_hierarchy = 'checked_in_at'
    readonly_fields = ('rsvp', 'checked_in_at', 'checked_in_by')
    change_list_template = 'admin/checkin/checkin_changelist.html'
    
    def changelist_view(self, request, extra_context=None):
        """Add events to the changelist context."""
        extra_context = extra_context or {}
        extra_context['all_events'] = Event.objects.filter(is_active=True).order_by('-date')
        return super().changelist_view(request, extra_context=extra_context)
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'checkin-dashboard/<int:event_id>/',
                self.admin_site.admin_view(self.checkin_dashboard),
                name='checkin-dashboard',
            ),
            path(
                'checkin-stats-api/<int:event_id>/',
                self.admin_site.admin_view(self.checkin_stats_api),
                name='checkin-stats-api',
            ),
        ]
        return custom_urls + urls
    
    def event_title(self, obj):
        return obj.rsvp.event.title if obj.rsvp else 'N/A'
    event_title.short_description = _('Event')
    event_title.admin_order_field = 'rsvp__event__title'
    
    def user_email(self, obj):
        return obj.rsvp.user.email if obj.rsvp else 'N/A'
    user_email.short_description = _('User Email')
    user_email.admin_order_field = 'rsvp__user__email'
    
    def checkin_dashboard(self, request, event_id):
        """Display check-in statistics and management dashboard for an event."""
        event = get_object_or_404(Event, id=event_id)
        
        # Get all RSVPs for this event
        all_rsvps = RSVP.objects.filter(event=event)
        accepted_rsvps = all_rsvps.filter(status='accepted')
        
        # Get check-in statistics
        checkins = CheckIn.objects.filter(rsvp__event=event)
        checked_in_count = all_rsvps.filter(checked_in=True).count()
        not_checked_in_count = accepted_rsvps.filter(checked_in=False).count()
        
        # Calculate rates
        total_accepted = accepted_rsvps.count()
        checkin_rate = (checked_in_count / total_accepted * 100) if total_accepted > 0 else 0
        
        # Get hourly check-in data for the last 24 hours
        now = timezone.now()
        twenty_four_hours_ago = now - timedelta(hours=24)
        
        hourly_checkins = []
        for i in range(24):
            hour_start = twenty_four_hours_ago + timedelta(hours=i)
            hour_end = hour_start + timedelta(hours=1)
            count = checkins.filter(
                checked_in_at__gte=hour_start,
                checked_in_at__lt=hour_end
            ).count()
            hourly_checkins.append({
                'hour': hour_start.strftime('%H:00'),
                'count': count
            })
        
        # Get recent check-ins
        recent_checkins = checkins.select_related(
            'rsvp__user', 'rsvp__event', 'checked_in_by'
        ).order_by('-checked_in_at')[:10]
        
        # Get attendees who haven't checked in yet
        not_checked_in = accepted_rsvps.filter(checked_in=False).select_related('user')[:10]
        
        # Get check-in staff statistics
        staff_stats = checkins.values('checked_in_by__email', 'checked_in_by__first_name', 'checked_in_by__last_name').annotate(
            checkin_count=Count('id')
        ).order_by('-checkin_count')[:5]
        
        # Calculate total attendees including guests
        total_guests = sum(rsvp.number_of_guests for rsvp in accepted_rsvps)
        total_expected_attendees = total_accepted + total_guests
        
        context = {
            'event': event,
            'checked_in_count': checked_in_count,
            'not_checked_in_count': not_checked_in_count,
            'total_accepted': total_accepted,
            'total_expected_attendees': total_expected_attendees,
            'checkin_rate': checkin_rate,
            'hourly_checkins': hourly_checkins,
            'recent_checkins': recent_checkins,
            'not_checked_in': not_checked_in,
            'staff_stats': staff_stats,
            'has_permission': True,
            'title': f'Check-in Dashboard - {event.title}',
            'opts': self.model._meta,
        }
        
        return render(request, 'admin/checkin/dashboard.html', context)
    
    def checkin_stats_api(self, request, event_id):
        """API endpoint for real-time check-in statistics."""
        event = get_object_or_404(Event, id=event_id)
        
        # Get current stats
        all_rsvps = RSVP.objects.filter(event=event)
        accepted_rsvps = all_rsvps.filter(status='accepted')
        checked_in_count = all_rsvps.filter(checked_in=True).count()
        total_accepted = accepted_rsvps.count()
        
        # Get latest check-ins (last 5 minutes)
        five_minutes_ago = timezone.now() - timedelta(minutes=5)
        recent_checkins = CheckIn.objects.filter(
            rsvp__event=event,
            checked_in_at__gte=five_minutes_ago
        ).count()
        
        return JsonResponse({
            'checked_in_count': checked_in_count,
            'total_accepted': total_accepted,
            'recent_checkins': recent_checkins,
            'checkin_rate': (checked_in_count / total_accepted * 100) if total_accepted > 0 else 0
        })
