import os
import django
import random
from django.contrib.auth.hashers import make_password

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'moratwe.settings')
django.setup()

from users.models import CustomUser

# Sample first names
first_names = [
    "Thabo", "Sipho", "Lerato", "Naledi", "Mandla", "Thandi", "Kagiso", 
    "Zanele", "Themba", "Nandi", "Tumelo", "Nomsa", "Sibusiso", "Precious",
    "Siyabonga", "Nthabiseng", "Kgomotso", "Thandeka", "Mpho", "Dikeledi",
    "Lindiwe", "Bongani", "Nosipho", "Nkosinathi", "Palesa", "Blessing",
    "Ayanda", "Tebogo", "Mduduzi", "Noluthando"
]

# Sample last names
last_names = [
    "Nkosi", "Dlamini", "Mkhize", "Ndlovu", "Khumalo", "Zuma", "Sithole",
    "Mokoena", "Molefe", "Tshabalala", "Mashaba", "Mahlangu", "Buthelezi",
    "Mabaso", "Mthembu", "Zwane", "Mbatha", "Phiri", "Maseko", "Motaung",
    "Naidoo", "Pillay", "Govender", "Singh", "Botha", "van der Merwe", 
    "Jacobs", "Hendricks", "Adams", "Abrahams"
]

def generate_phone_number():
    """Generate a random South African phone number"""
    prefixes = ["060", "061", "062", "063", "064", "065", "066", "067", "068", "071", "072", "073", "074", "076", "078", "079", "081", "082", "083", "084"]
    prefix = random.choice(prefixes)
    suffix = ''.join([str(random.randint(0, 9)) for _ in range(7)])
    return f"{prefix}{suffix}"

def create_sample_users(num_users=20):
    """Create sample users for testing"""
    created_count = 0
    admin_created = False
    
    print(f"Creating {num_users} sample users...")
    
    # First create an admin user
    if not CustomUser.objects.filter(email="admin@example.com").exists():
        admin_user = CustomUser.objects.create(
            email="admin@example.com",
            first_name="Admin",
            last_name="User",
            password=make_password("adminpass123"),
            is_active=True,
            is_staff=True,
            is_superuser=True,
            phone_number="0721234567",
            is_organizer=True
        )
        print(f"Created admin user: admin@example.com")
        admin_created = True
        created_count += 1
    
    # Create regular users
    for i in range(num_users - (1 if admin_created else 0)):
        first_name = random.choice(first_names)
        last_name = random.choice(last_names)
        email = f"{first_name.lower()}.{last_name.lower()}{random.randint(1, 999)}@example.com"
        
        # Generate unique phone number
        phone_number = generate_phone_number()
        while CustomUser.objects.filter(phone_number=phone_number).exists():
            phone_number = generate_phone_number()
        
        # Make some users organizers
        is_organizer = random.random() < 0.2  # 20% chance of being an organizer
        
        try:
            user = CustomUser.objects.create(
                email=email,
                first_name=first_name,
                last_name=last_name,
                password=make_password(f"password{i+1}"),
                is_active=True,
                phone_number=phone_number,
                is_organizer=is_organizer
            )
            
            print(f"Created user: {email} ({phone_number})")
            created_count += 1
        except Exception as e:
            print(f"Error creating user {email}: {str(e)}")
    
    print(f"Successfully created {created_count} users.")

if __name__ == "__main__":
    create_sample_users(25)  # Create 25 users 