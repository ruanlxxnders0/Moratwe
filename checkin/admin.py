from django.contrib import admin
from .models import CheckIn


@admin.register(CheckIn)
class CheckInAdmin(admin.ModelAdmin):
    list_display = ('rsvp', 'checked_in_at', 'checked_in_by')
    list_filter = ('checked_in_at',)
    search_fields = ('rsvp__user__email', 'rsvp__event__title')
    date_hierarchy = 'checked_in_at'
    readonly_fields = ('rsvp', 'checked_in_at', 'checked_in_by')
