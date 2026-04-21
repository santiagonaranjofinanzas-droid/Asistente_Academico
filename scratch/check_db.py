import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv('local-workers/.env')

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not url or not key:
    print("Missing credentials")
    exit(1)

supabase = create_client(url, key)

try:
    # Try to list tables by querying a common one or just seeing if we can reach it
    res = supabase.table('tareas').select('id').limit(1).execute()
    print("Connection to 'tareas' successful")
    
    # Try to see if config table exists
    try:
        res = supabase.table('sistema_config').select('*').execute()
        print("Table 'sistema_config' exists")
        print(res.data)
    except:
        print("Table 'sistema_config' does NOT exist")
except Exception as e:
    print(f"Error: {e}")
