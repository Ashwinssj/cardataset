import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import subprocess
import os
import sys
from dotenv import load_dotenv

def setup_database():
    print("=== OBD PostgreSQL Database Setup ===")
    
    # Load .env variables
    load_dotenv()
    
    user = os.environ.get('DB_USER', 'postgres')
    password = os.environ.get('DB_PASSWORD', 'your_password_here')
    host = os.environ.get('DB_HOST', 'localhost')
    port = os.environ.get('DB_PORT', '5432')
    db_name = os.environ.get('DB_NAME', 'obd_db')

    if password == 'your_password_here':
        print("❌ Error: Please open backend/.env and update your DB_PASSWORD before running this script.")
        return

    try:
        # Connect to the default 'postgres' database to create the new one
        conn = psycopg2.connect(
            dbname='postgres',
            user=user,
            password=password,
            host=host,
            port=port
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        # Check if database exists
        cursor.execute("SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s", (db_name,))
        exists = cursor.fetchone()

        if not exists:
            print(f"\nCreating database '{db_name}'...")
            cursor.execute(f"CREATE DATABASE {db_name};")
            print("Database created successfully!")
        else:
            print(f"\nDatabase '{db_name}' already exists.")

        cursor.close()
        conn.close()

        print("\n--- Running Django Migrations ---")
        # Run makemigrations
        subprocess.run([sys.executable, "manage.py", "makemigrations", "api"], check=True)
        # Run migrate
        subprocess.run([sys.executable, "manage.py", "migrate"], check=True)
        
        print("\n✅ Database and migrations are fully set up!")
        print(f"\nYou can now start your Django server!")
        
    except psycopg2.OperationalError as e:
        print(f"\n❌ Connection Failed: Could not connect to PostgreSQL.")
        print(f"Details: {e}")
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")

if __name__ == "__main__":
    setup_database()
