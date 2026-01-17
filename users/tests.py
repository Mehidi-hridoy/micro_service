from django.test import TestCase

# Create your tests here.


"""


# Install dependencies
pip install django djangorestframework djangorestframework-simplejwt django-cors-headers drf-yasg django-filter

# Run migrations for each database
python manage.py makemigrations users
python manage.py makemigrations shifting
python manage.py makemigrations notifications
python manage.py makemigrations analytics
python manage.py makemigrations api_v1
python manage.py makemigrations api_v2

# Migrate to specific databases
python manage.py migrate --database=users_db
python manage.py migrate --database=shifting_db
python manage.py migrate --database=analytics_db
python manage.py migrate  # For default database

# Create superuser
python manage.py createsuperuser --database=users_db

# Run development server
python manage.py runserver

git add .
git commit -m "Microservices project setup"
git push -u origin main


"""