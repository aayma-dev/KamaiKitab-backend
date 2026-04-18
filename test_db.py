import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("=" * 50)
print("DATABASE CONNECTION TEST")
print("=" * 50)

# Get database URL
db_url = os.getenv('DATABASE_URL')
print(f'\n1. DATABASE_URL: {db_url}')

if not db_url:
    print('❌ DATABASE_URL not found in .env file')
    sys.exit(1)

# Test connection
print('\n2. Testing connection...')
try:
    from app.database import check_db_connection, init_db
    
    if check_db_connection():
        print('✅ PostgreSQL connection successful with auth_user!')
        
        print('\n3. Creating tables...')
        init_db()
        print('✅ Database tables created successfully!')
        
        print('\n4. Verifying tables...')
        from sqlalchemy import inspect
        from app.database import engine
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f'✅ Tables created: {tables}')
        
        print('\n' + "=" * 50)
        print('✅ DATABASE IS READY!')
        print("=" * 50)
    else:
        print('❌ PostgreSQL connection failed!')
        print('\nTroubleshooting:')
        print('1. Make sure PostgreSQL is running: Get-Service postgresql-x64-18')
        print('2. Check password in .env file')
        print('3. Try connecting manually: psql -U auth_user -d auth_db -h localhost')
        
except Exception as e:
    print(f'❌ Error: {e}')
