import os
from dotenv import load_dotenv
from supabase import create_client, Client

# load environment variables from .env file
load_dotenv()


def get_db_connection() -> Client:
    """
    Initializes and returns a Supabase client using the modern SDK.
    Note: For backend data ingestion, you MUST use the 'service_role' key
    to bypass Row Level Security (RLS).
    """
    url: str = os.environ.get("SUPABASE_URL")

    key: str = os.environ.get("SUPABASE_KEY")

    if not url or not key:
        raise ValueError("SUPABASE_URL or SUPABASE_KEY is missing from .env file!")

    return create_client(url, key)


def test_connection():
    """
    Tests the Supabase SDK connection and reports the current row count.
    """
    try:
        supabase = get_db_connection()
        # perform a simple count query to verify the key has access
        response = (
            supabase.table("dramas").select("*", count="exact").limit(1).execute()
        )

        print("Supabase SDK Connection Successful!")
        print(f"Current rows in 'dramas' table: {response.count}")

    except Exception as e:
        print(f"Connection failed: {e}")
        print("\nTroubleshooting Tips:")
        print("1. Ensure SUPABASE_URL is 'https://xxx.supabase.co'")
        print(
            "2. Ensure SUPABASE_KEY is the 'service_role' key (not the anon key) to bypass RLS."
        )


if __name__ == "__main__":
    test_connection()
