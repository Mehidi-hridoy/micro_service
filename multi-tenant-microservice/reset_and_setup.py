import os
import sys
import subprocess
import psycopg2
from psycopg2 import sql

def run_command(command):
    print(f"Running: {command}")
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.stdout:
        print(f"Output: {result.stdout}")
    if result.stderr and "already exists" not in result.stderr:
        print(f"Error: {result.stderr}")
    return result.returncode

def reset_databases():
    """Drop and recreate all databases"""
    print("Resetting databases...")
    
    databases = ['main_db', 'tenant_1_db', 'tenant_2_db']
    
    try:
        # Connect to PostgreSQL
        conn = psycopg2.connect(
            host='localhost',
            port=5432,
            user='postgres',
            password='password'
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Drop existing databases
        for db_name in databases:
            try:
                # Terminate connections first
                cursor.execute("""
                    SELECT pg_terminate_backend(pg_stat_activity.pid)
                    FROM pg_stat_activity
                    WHERE pg_stat_activity.datname = %s
                    AND pid <> pg_backend_pid();
                """, (db_name,))
                
                cursor.execute(sql.SQL("DROP DATABASE IF EXISTS {}").format(
                    sql.Identifier(db_name)
                ))
                print(f"Dropped database: {db_name}")
            except Exception as e:
                print(f"Error dropping {db_name}: {e}")
        
        # Create fresh databases
        for db_name in databases:
            try:
                cursor.execute(sql.SQL("CREATE DATABASE {}").format(
                    sql.Identifier(db_name)
                ))
                print(f"Created database: {db_name}")
            except Exception as e:
                print(f"Error creating {db_name}: {e}")
        
        cursor.close()
        conn.close()
        print("✅ Databases reset successfully")
        
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        sys.exit(1)

def main():
    print("=" * 60)
    print("COMPLETE MICROSERVICE SETUP")
    print("=" * 60)
    
    # Step 1: Reset databases
    reset_databases()
    
    # Step 2: Delete migration files
    print("\nCleaning up migration files...")
    migration_dirs = [
        'users_service/migrations',
        'shipping_service/migrations'
    ]
    
    for dir_path in migration_dirs:
        if os.path.exists(dir_path):
            for file in os.listdir(dir_path):
                if file.endswith('.py') and file != '__init__.py':
                    os.remove(os.path.join(dir_path, file))
            print(f"Cleaned {dir_path}")
    
    # Ensure __init__.py files exist
    open('users_service/migrations/__init__.py', 'a').close()
    open('shipping_service/migrations/__init__.py', 'a').close()
    
    # Step 3: Create migrations
    print("\nCreating migrations...")
    run_command("python manage.py makemigrations users_service")
    run_command("python manage.py makemigrations shipping_service")
    
    # Step 4: Apply migrations to ALL databases
    print("\nApplying migrations...")
    
    databases = ['default', 'tenant_1', 'tenant_2']
    
    for db in databases:
        print(f"\nApplying to {db} database:")
        
        # Apply all Django built-in migrations first
        run_command(f"python manage.py migrate auth --database={db}")
        run_command(f"python manage.py migrate contenttypes --database={db}")
        run_command(f"python manage.py migrate sessions --database={db}")
        run_command(f"python manage.py migrate admin --database={db}")
        run_command(f"python manage.py migrate authtoken --database={db}")
        
        # Apply custom app migrations
        if db == 'default':
            run_command(f"python manage.py migrate users_service --database={db}")
        
        run_command(f"python manage.py migrate shipping_service --database={db}")
        
        # Run any remaining migrations
        run_command(f"python manage.py migrate --database={db}")
    
    # Step 5: Create superuser
    print("\nCreating superuser...")
    run_command("python manage.py createsuperuser --database=default")
    
    print("\n" + "=" * 60)
    print("✅ SETUP COMPLETE!")
    print("=" * 60)
    print("\nRun server: python manage.py runserver")
    print("\nTest endpoints:")
    print("1. Health check: http://localhost:8000/api/health")
    print("2. Get token: POST http://localhost:8000/api/token/")
    print("3. Admin: http://localhost:8000/admin")
    print("=" * 60)

if __name__ == "__main__":
    main()