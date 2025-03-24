import os
import django
import random
import datetime
import requests
from io import BytesIO
from django.core.files.base import ContentFile

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'moratwe.settings')
django.setup()

from events.models import Event, BreakawaySession, RSVP
from users.models import CustomUser

# Event theme categories
event_themes = [
    "Tech Conference", 
    "Community Meetup", 
    "Workshop", 
    "Networking Event", 
    "Hackathon",
    "Panel Discussion",
    "Product Launch",
    "Career Fair",
    "Developer Summit",
    "Leadership Symposium"
]

# Event locations
locations = [
    "Cape Town Innovation Hub",
    "Johannesburg Tech Center",
    "Pretoria Business Center",
    "Durban Beachfront Convention",
    "Stellenbosch University Hall",
    "Port Elizabeth Civic Center",
    "Bloemfontein Conference Center",
    "Sandton Convention Center",
    "V&A Waterfront Pavilion",
    "Kirstenbosch Botanical Gardens",
    "Virtual (Zoom)"
]

# Breakaway session titles
session_titles = [
    "Getting Started with AI",
    "Python for Data Science",
    "Flutter Mobile Development",
    "Django Web Development",
    "Building with React Native",
    "Cloud Infrastructure Basics",
    "Startup Funding Strategies",
    "User Experience Design",
    "Agile Project Management",
    "Blockchain Applications",
    "Cybersecurity Best Practices",
    "IoT Solutions",
    "DevOps Workshop",
    "Leadership in Tech",
    "Women in Tech Panel"
]

# Session descriptions
session_descriptions = [
    "Join us for an interactive session where experts share their insights.",
    "Learn practical skills that you can apply immediately in your work.",
    "This hands-on workshop will guide you through building a real-world application.",
    "Network with industry leaders and learn about emerging trends.",
    "Expand your knowledge and get inspired by leading practitioners.",
    "A beginner-friendly introduction to key concepts and tools.",
    "Advanced techniques for experienced professionals.",
    "Collaborative problem-solving session to tackle industry challenges.",
    "Case studies and success stories from top companies.",
    "Future trends and how to prepare for upcoming industry shifts."
]

# Event descriptions
event_descriptions = [
    "Join us for this exciting event bringing together tech professionals from across South Africa. We'll explore cutting-edge technologies and their applications in our local context.",
    "A community-focused gathering where developers can network, share ideas, and collaborate on innovative projects. All skill levels welcome!",
    "This professional development event features expert speakers and hands-on workshops designed to enhance your technical skills and career prospects.",
    "An immersive experience focused on building real-world solutions to local challenges. Bring your laptop and your creativity!",
    "Connect with industry leaders and potential employers in this networking-focused event. Great opportunity for students and early career professionals.",
    "A platform for innovation where startups and established companies showcase their latest products and services to the tech community.",
    "Celebrating diversity in tech with a special focus on underrepresented groups. Come share your experiences and learn from others.",
    "A deep dive into specific technologies that are shaping the future of our industry. Expert-led sessions with Q&A opportunities.",
    "Bringing together business and technology perspectives to address challenges facing South African companies in the digital age.",
    "A collaborative event focused on developing technological solutions for sustainability and social impact in our communities."
]

# Unsplash collections for tech events
unsplash_collections = [
    "conference",
    "technology",
    "coding",
    "workshop",
    "business meeting",
    "presentation",
    "tech event",
    "networking",
    "hackathon",
    "tech community"
]

def download_image_from_unsplash(search_term):
    """Download a random image from Unsplash based on search term"""
    url = f"https://source.unsplash.com/random/1200x800/?{search_term}"
    response = requests.get(url)
    if response.status_code == 200:
        return ContentFile(response.content)
    return None

def generate_random_date(start_date, end_date):
    """Generate a random date between start_date and end_date"""
    time_between_dates = end_date - start_date
    days_between_dates = time_between_dates.days
    random_number_of_days = random.randrange(days_between_dates)
    random_date = start_date + datetime.timedelta(days=random_number_of_days)
    
    # Add random time
    hour = random.randint(8, 18)  # Between 8 AM and 6 PM
    minute = random.choice([0, 15, 30, 45])
    random_date = random_date.replace(hour=hour, minute=minute)
    
    return random_date

def create_sample_events(num_events=10):
    """Create sample events with images and breakaway sessions"""
    # Get a random organizer
    organizers = list(CustomUser.objects.all())
    if not organizers:
        print("No users found. Please create users first.")
        return
    
    # Get all users for panelists and attendees
    all_users = list(CustomUser.objects.all())
    if len(all_users) < 5:
        print("Not enough users for meaningful data. Please create at least 5 users.")
        return
    
    # Start date ranges for events (past, present, future)
    start_past = datetime.datetime.now() - datetime.timedelta(days=90)
    end_past = datetime.datetime.now() - datetime.timedelta(days=1)
    start_future = datetime.datetime.now() + datetime.timedelta(days=1)
    end_future = datetime.datetime.now() + datetime.timedelta(days=180)
    
    # Create events
    for i in range(num_events):
        # Decide if event is past or future
        is_past = random.choice([True, False])
        
        if is_past:
            event_date = generate_random_date(start_past, end_past)
        else:
            event_date = generate_random_date(start_future, end_future)
        
        title = f"{random.choice(event_themes)} {random.randint(2023, 2025)}"
        description = random.choice(event_descriptions)
        location = random.choice(locations)
        organizer = random.choice(organizers)
        
        # Create event
        event = Event(
            title=title,
            description=description,
            date=event_date,
            location=location,
            organizer=organizer,
            is_active=True
        )
        
        # Download and save image
        search_term = random.choice(unsplash_collections)
        image_content = download_image_from_unsplash(search_term)
        if image_content:
            event.image.save(f"event_{i+1}.jpg", image_content, save=False)
        
        event.save()
        print(f"Created event: {title}")
        
        # Create 3-5 breakaway sessions for each event
        num_sessions = random.randint(3, 5)
        for j in range(num_sessions):
            session_title = random.choice(session_titles)
            session_description = random.choice(session_descriptions)
            
            # Generate start and end times
            base_hour = 9 + j*2  # Spread throughout the day
            start_hour = min(base_hour, 16)  # No later than 4 PM
            end_hour = min(start_hour + 1, 17)  # Sessions last 1 hour, no later than 5 PM
            
            session = BreakawaySession(
                event=event,
                title=session_title,
                description=session_description,
                start_time=datetime.time(start_hour, 0),
                end_time=datetime.time(end_hour, 0),
                max_attendees=random.choice([20, 30, 50, 100, None])
            )
            session.save()
            
            # Add 3-6 random users as panelists
            num_panelists = random.randint(3, 6)
            panelists = random.sample(all_users, min(num_panelists, len(all_users)))
            session.panelists.add(*panelists)
            
            print(f"  - Added session: {session_title}")
        
        # Create RSVPs for the event (10-30 users)
        num_rsvps = random.randint(10, min(30, len(all_users)))
        attendees = random.sample(all_users, num_rsvps)
        
        for attendee in attendees:
            # Check if already RSVP'd
            if not RSVP.objects.filter(event=event, user=attendee).exists():
                rsvp = RSVP(
                    event=event,
                    user=attendee,
                    checked_in=is_past and random.random() > 0.3  # 70% chance of check-in for past events
                )
                rsvp.save()
                
                # Add user to 1-3 random sessions
                if event.breakaways.count() > 0:
                    num_selected = min(random.randint(1, 3), event.breakaways.count())
                    selected_sessions = random.sample(list(event.breakaways.all()), num_selected)
                    rsvp.selected_sessions.add(*selected_sessions)
                
                print(f"  - Added RSVP for: {attendee.email}")

if __name__ == "__main__":
    print("Generating sample events...")
    create_sample_events(15)  # Create 15 events
    print("Done!") 