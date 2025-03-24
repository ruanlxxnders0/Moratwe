import os
import django
import requests
import uuid
from django.core.files.base import ContentFile
from django.utils import timezone

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'moratwe.settings')
django.setup()

from events.models import Event

def download_random_image():
    """Download a random image from Unsplash."""
    try:
        # Use a more reliable Unsplash API endpoint
        response = requests.get(
            'https://api.unsplash.com/photos/random',
            params={
                'query': 'event,conference,meeting',
                'orientation': 'landscape'
            },
            headers={
                'Authorization': 'Client-ID DwZHO-VrMecuaoH5NyFtR0a9JmoT3kQPPZyvmM17d8I'
            },
            timeout=10
        )
        response.raise_for_status()
        
        # Get the image URL from the response
        image_url = response.json()['urls']['regular']
        
        # Download the actual image
        img_response = requests.get(image_url, timeout=10)
        img_response.raise_for_status()
        
        # Generate a unique filename
        filename = f"event_{uuid.uuid4().hex[:8]}.jpg"
        
        # Create a ContentFile from the image data with a name
        return ContentFile(img_response.content, name=filename), filename
    except requests.exceptions.RequestException as e:
        print(f"Error downloading image: {e}")
        return None, None

def attach_images_to_events():
    """Attach images to events that don't have images."""
    # Get all events without images
    events_without_images = Event.objects.filter(image='')
    
    count = events_without_images.count()
    if count == 0:
        print("No events found without images.")
        return
    
    print(f"Found {count} events without images.")
    confirmation = input("Do you want to attach images to these events? (yes/no): ")
    
    if confirmation.lower() != 'yes':
        print("Operation cancelled.")
        return
    
    success_count = 0
    error_count = 0
    
    for event in events_without_images:
        try:
            # Download a random image
            image_content, filename = download_random_image()
            
            if image_content is None:
                print(f"Failed to download image for event: {event.title}")
                error_count += 1
                continue
            
            # Attach the image to the event
            event.image = image_content
            event.save()
            
            success_count += 1
            print(f"Successfully attached image to event: {event.title}")
            
        except Exception as e:
            print(f"Error attaching image to event {event.title}: {e}")
            error_count += 1
    
    print(f"\nOperation completed:")
    print(f"- Successfully attached images to {success_count} events")
    print(f"- Failed to attach images to {error_count} events")

if __name__ == "__main__":
    attach_images_to_events() 