# Moratwe Django Project

This is a Django project for Moratwe.

## Setup

1. Clone the repository:
   ```
   git clone <repository-url>
   cd moratwe
   ```

2. Create a virtual environment and activate it:
   ```
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   - Copy the example environment file:
     ```
     cp .env.example .env
     ```
   - Edit the `.env` file with your specific configuration if needed

5. Set up PostgreSQL:
   - Install PostgreSQL if you haven't already
   - Create a database named 'moratwe' (or the name specified in your .env file):
     ```
     createdb moratwe
     ```
   - Or using psql:
     ```
     psql -U postgres
     CREATE DATABASE moratwe;
     \q
     ```
   - Update the database settings in `moratwe/settings.py` if needed (username, password, etc.)

6. Run migrations:
   ```
   python manage.py migrate
   ```

7. Start the development server:
   ```
   python manage.py runserver
   ```

8. Open your browser and navigate to http://127.0.0.1:8000/

## Project Structure

- `moratwe/` - Main project settings
- `core/` - Core application with main functionality

## Creating a Superuser

To access the admin interface, create a superuser:
```
python manage.py createsuperuser
```

Then visit http://127.0.0.1:8000/admin/ and log in with your credentials. 