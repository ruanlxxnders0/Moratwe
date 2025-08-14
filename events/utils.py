"""
Utility functions for the events app.
"""
from urllib.parse import urlencode
from django.utils.html import format_html
from django.utils.safestring import mark_safe
import datetime


def generate_calendar_links(event, site_url=None):
    """
    Generate calendar links for Google Calendar, Outlook, and ICS download.
    
    Args:
        event: Event instance
        site_url: Base site URL for absolute links
    
    Returns:
        Dictionary containing calendar links and HTML
    """
    if not event.date:
        return {}
    
    # Convert to appropriate timezone-aware datetime
    start_time = event.date
    # Default 2-hour duration
    end_time = start_time + datetime.timedelta(hours=2)
    
    # Format dates for different calendar systems
    google_date_format = lambda dt: dt.strftime('%Y%m%dT%H%M%S')
    outlook_date_format = lambda dt: dt.strftime('%Y-%m-%dT%H:%M:%S')
    ics_date_format = lambda dt: dt.strftime('%Y%m%dT%H%M%SZ')
    
    # Event details
    title = event.title
    description = f"{event.description}\n\nOrganized by: {event.organizer.get_full_name()}" if event.description else f"Organized by: {event.organizer.get_full_name()}"
    location = event.location
    
    # Event URL
    event_url = ""
    if site_url:
        event_url = f"{site_url}/events/{event.id}/"
        description += f"\n\nEvent Details: {event_url}"
    
    # Google Calendar
    google_params = {
        'action': 'TEMPLATE',
        'text': title,
        'dates': f"{google_date_format(start_time)}/{google_date_format(end_time)}",
        'details': description,
        'location': location,
    }
    google_url = f"https://calendar.google.com/calendar/render?{urlencode(google_params)}"
    
    # Outlook/Office 365
    outlook_params = {
        'subject': title,
        'startdt': outlook_date_format(start_time),
        'enddt': outlook_date_format(end_time),
        'body': description,
        'location': location,
    }
    outlook_url = f"https://outlook.live.com/calendar/0/deeplink/compose?{urlencode(outlook_params)}"
    
    # Yahoo Calendar
    yahoo_params = {
        'v': '60',
        'title': title,
        'st': google_date_format(start_time),
        'et': google_date_format(end_time),
        'desc': description,
        'in_loc': location,
    }
    yahoo_url = f"https://calendar.yahoo.com/?{urlencode(yahoo_params)}"
    
    # iOS Calendar - create a download URL for ICS file
    # This will work better in email clients for iOS devices
    if site_url:
        # Create a URL that will serve the ICS file for download
        ios_url = f"{site_url}/events/{event.id}/calendar.ics"
    else:
        # Fallback to Google Calendar for iOS if no site URL
        ios_url = google_url
    
    # ICS file content - escape newlines for ICS format
    ics_description = description.replace('\n', '\\n')
    organizer_name = event.organizer.get_full_name()
    organizer_email = event.organizer.email
    
    ics_content = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Moratwe//Event Calendar//EN
BEGIN:VEVENT
UID:{event.id}@moratwe.com
DTSTART:{ics_date_format(start_time)}
DTEND:{ics_date_format(end_time)}
SUMMARY:{title}
DESCRIPTION:{ics_description}
LOCATION:{location}
ORGANIZER:CN={organizer_name}:MAILTO:{organizer_email}
BEGIN:VALARM
TRIGGER:-PT15M
ACTION:DISPLAY
DESCRIPTION:Event reminder
END:VALARM
END:VEVENT
END:VCALENDAR"""
    
    return {
        'google_url': google_url,
        'outlook_url': outlook_url,
        'yahoo_url': yahoo_url,
        'ios_url': ios_url,
        'ics_content': ics_content,
        'ics_filename': f"{title.replace(' ', '_')}.ics"
    }


def get_calendar_buttons_html(event, site_url=None):
    """
    Generate HTML for individual calendar buttons.
    
    Args:
        event: Event instance
        site_url: Base site URL for absolute links
    
    Returns:
        Safe HTML string for individual calendar buttons
    """
    calendar_links = generate_calendar_links(event, site_url)
    
    if not calendar_links:
        return ""
    
    html = f"""
    <div class="calendar-buttons w-full">
        <h3 class="text-lg font-semibold mb-3 text-gray-700">📅 Add to Calendar</h3>
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            <a href="{calendar_links['google_url']}" target="_blank" class="inline-flex items-center justify-center px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white text-sm font-medium rounded-lg transition duration-200 shadow-sm">
                <svg class="w-4 h-4 mr-2" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                    <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                    <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                    <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                </svg>
                Google
            </a>
            
            <a href="{calendar_links['outlook_url']}" target="_blank" class="inline-flex items-center justify-center px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg transition duration-200 shadow-sm">
                <svg class="w-4 h-4 mr-2" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M7.88 12.04q0 .45-.11.87-.1.41-.33.74-.22.33-.58.52-.37.2-.87.2t-.85-.2q-.35-.21-.57-.55-.22-.33-.33-.75-.1-.42-.1-.83 0-.43.1-.85.1-.42.33-.75.22-.34.57-.55.35-.2.85-.2t.87.2q.36.19.58.52.22.33.33.74.11.42.11.87zm-3.02 0q0 .66.25 1.09.26.44.68.44.43 0 .68-.44.26-.43.26-1.09 0-.65-.26-1.09-.25-.44-.68-.44-.42 0-.68.44-.25.44-.25 1.09zM24 12.5V7.04l-5.5 1.47v8.98L24 16.02v-3.52zM13.5 8.51v7.98L7 17.98V6.02l6.5 2.49z"/>
                </svg>
                Outlook
            </a>
            
            <a href="{calendar_links['yahoo_url']}" target="_blank" class="inline-flex items-center justify-center px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white text-sm font-medium rounded-lg transition duration-200 shadow-sm">
                <svg class="w-4 h-4 mr-2" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M11.5 9.5L7 5l6.5 2.49V7.5l.5.5v1.5zM12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2z"/>
                </svg>
                Yahoo
            </a>
            
            <a href="{calendar_links['ios_url']}" target="_blank" class="inline-flex items-center justify-center px-4 py-2 bg-gray-800 hover:bg-gray-900 text-white text-sm font-medium rounded-lg transition duration-200 shadow-sm">
                <svg class="w-4 h-4 mr-2" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M18.71 19.5c-.83 1.24-1.71 2.45-3.05 2.47-1.34.03-1.77-.79-3.29-.79-1.53 0-2 .77-3.27.82-1.31.05-2.3-1.32-3.14-2.53C4.25 17 2.94 12.45 4.7 9.39c.87-1.52 2.43-2.48 4.12-2.51 1.28-.02 2.5.87 3.29.87.78 0 2.26-1.07 3.81-.91.65.03 2.47.26 3.64 1.98-.09.06-2.17 1.28-2.15 3.81.03 3.02 2.65 4.03 2.68 4.04-.03.07-.42 1.44-1.38 2.83M13 3.5c.73-.83 1.94-1.46 2.94-1.5.13 1.17-.34 2.35-1.04 3.19-.69.85-1.83 1.51-2.95 1.42-.15-1.15.41-2.35 1.05-3.11z"/>
                </svg>
                iOS
            </a>
        </div>
        
        <div class="mt-3">
            <button onclick="downloadICSFile_{event.id}()" class="inline-flex items-center justify-center px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 text-sm font-medium rounded-lg transition duration-200 shadow-sm border border-gray-300">
                <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                </svg>
                Download ICS File
            </button>
        </div>
    </div>
    
    <script>
        function downloadICSFile_{event.id}() {{
            const icsContent = `{calendar_links['ics_content']}`;
            const blob = new Blob([icsContent], {{ type: 'text/calendar;charset=utf-8' }});
            const link = document.createElement('a');
            link.href = window.URL.createObjectURL(blob);
            link.download = '{calendar_links['ics_filename']}';
            link.click();
        }}
    </script>
    """
    
    return mark_safe(html)


def get_calendar_email_html(event, site_url=None):
    """
    Generate simple HTML calendar links for email templates.
    
    Args:
        event: Event instance
        site_url: Base site URL for absolute links
    
    Returns:
        Safe HTML string for email calendar links
    """
    calendar_links = generate_calendar_links(event, site_url)
    
    if not calendar_links:
        return ""
    
    html = f"""
    <div style="text-align: center; margin: 20px 0; padding: 20px; background-color: #f8f9fa; border-radius: 8px;">
        <h3 style="color: #333; margin-bottom: 15px;">📅 Add to Your Calendar</h3>
        <div style="margin-bottom: 10px;">
            <a href="{calendar_links['google_url']}" target="_blank" style="display: inline-block; margin: 5px; padding: 10px 20px; background-color: #4285f4; color: white; text-decoration: none; border-radius: 5px; font-weight: bold;">
                Google Calendar
            </a>
            <a href="{calendar_links['outlook_url']}" target="_blank" style="display: inline-block; margin: 5px; padding: 10px 20px; background-color: #0072c6; color: white; text-decoration: none; border-radius: 5px; font-weight: bold;">
                Outlook
            </a>
        </div>
        <div style="margin-bottom: 10px;">
            <a href="{calendar_links['yahoo_url']}" target="_blank" style="display: inline-block; margin: 5px; padding: 10px 20px; background-color: #5f01d1; color: white; text-decoration: none; border-radius: 5px; font-weight: bold;">
                Yahoo Calendar
            </a>
            <a href="{calendar_links['ios_url']}" target="_blank" style="display: inline-block; margin: 5px; padding: 10px 20px; background-color: #333333; color: white; text-decoration: none; border-radius: 5px; font-weight: bold;">
                iOS Calendar
            </a>
        </div>
        <p style="color: #666; font-size: 0.9em; margin-top: 10px;">
            Click any button above to add this event to your calendar
        </p>
    </div>
    """
    
    return mark_safe(html)
