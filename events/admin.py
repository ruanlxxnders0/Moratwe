from django.contrib import admin
from .models import Event, BreakawaySession, RSVP
from django.utils.safestring import mark_safe


class BreakawaySessionInline(admin.TabularInline):
    model = BreakawaySession
    extra = 1
    filter_horizontal = ('panelists',)


class RSVPInline(admin.TabularInline):
    model = RSVP
    extra = 1
    readonly_fields = ('qr_code',)
    filter_horizontal = ('selected_sessions',)


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'location', 'date', 'organizer', 'is_active', 'has_image')
    list_filter = ('is_active', 'date')
    search_fields = ('title', 'description', 'location')
    date_hierarchy = 'date'
    inlines = [BreakawaySessionInline, RSVPInline]
    readonly_fields = ('display_image',)
    fields = ('title', 'description', 'date', 'location', 'organizer', 'is_active', 'image', 'display_image')
    
    def has_image(self, obj):
        return bool(obj.image)
    has_image.boolean = True
    has_image.short_description = 'Has Image'
    
    def display_image(self, obj):
        if obj.image:
            return mark_safe(f'<img src="{obj.image.url}" width="300" />')
        return "No Image"
    display_image.short_description = 'Image Preview'


@admin.register(BreakawaySession)
class BreakawaySessionAdmin(admin.ModelAdmin):
    list_display = ('title', 'event', 'start_time', 'end_time')
    list_filter = ('event',)
    search_fields = ('title', 'description', 'event__title')
    filter_horizontal = ('panelists',)


@admin.register(RSVP)
class RSVPAdmin(admin.ModelAdmin):
    list_display = ('user', 'event', 'created_at', 'checked_in')
    list_filter = ('event', 'checked_in')
    search_fields = ('user__email', 'event__title')
    date_hierarchy = 'created_at'
    filter_horizontal = ('selected_sessions',)
    readonly_fields = ('qr_code',)
