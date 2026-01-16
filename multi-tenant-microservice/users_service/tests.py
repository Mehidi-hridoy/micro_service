from django.test import TestCase

# Create your tests here.


"""



multi-tenant-microservice

python manage.py makemigrations 
python manage.py migrate
python manage.py runserver


git add .
git commit -m "Initial commit: multi-tenant microservice Django project"
git push -u origin main










# First, create migrations for each app
python manage.py makemigrations users_service
python manage.py makemigrations shipping_service

# Check the migrations were created
python manage.py showmigrations users_service
python manage.py showmigrations shipping_service


# For main database (users)
python manage.py migrate users_service --database=default

# For tenant databases
python manage.py migrate shipping_service --database=tenant_1
python manage.py migrate shipping_service --database=tenant_2


pip freeze > requirements.txt




"""