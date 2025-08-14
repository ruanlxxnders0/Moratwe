import logging
from django.core.management.base import BaseCommand
from events.models import RSVP

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Regenerate QR codes for all accepted RSVPs to use the new JSON format'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        # Get all accepted RSVPs
        accepted_rsvps = RSVP.objects.filter(status='accepted')
        
        self.stdout.write(f"Found {accepted_rsvps.count()} accepted RSVPs")
        
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN: No changes will be made"))
        
        updated_count = 0
        
        for rsvp in accepted_rsvps:
            try:
                if not dry_run:
                    # Delete existing QR code if it exists
                    if rsvp.qr_code:
                        rsvp.qr_code.delete(save=False)
                        rsvp.qr_code = None
                        rsvp.save()
                    
                    # Regenerate QR code with new format
                    rsvp.generate_qr_code()
                    
                updated_count += 1
                self.stdout.write(f"{'Would regenerate' if dry_run else 'Regenerated'} QR code for RSVP {rsvp.id} (Event: {rsvp.event.title}, User: {rsvp.user.email})")
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Error processing RSVP {rsvp.id}: {str(e)}")
                )
        
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(f"Would update {updated_count} QR codes")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"Successfully regenerated {updated_count} QR codes")
            )
