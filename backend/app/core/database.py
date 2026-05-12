import os
import logging
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

class SupabaseManager:
    def __init__(self):
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
        if not url or not key:
            logging.warning("SUPABASE_URL or SUPABASE_KEY is missing. Database functionality is disabled.")
            self.client: Client | None = None
        else:
            self.client: Client = create_client(url, key)
            
    def save_predictions(self, predictions_data: list):
        if not self.client:
            logging.error("Supabase client is not initialized.")
            return None
            
        try:
            # Insert a new record containing the JSON payload of all daily predictions
            data, count = self.client.table("mlb_predictions").insert({"data": predictions_data}).execute()
            return data
        except Exception as e:
            logging.error(f"Failed to save predictions to Supabase: {e}")
            return None

    def get_latest_predictions(self):
        if not self.client:
            return {"error": "Supabase client not initialized"}
        
        try:
            # Query the most recent prediction payload
            response = self.client.table("mlb_predictions").select("*").order("updated_at", desc=True).limit(1).execute()
            # If the schema uses created_at instead of updated_at, we might need to adjust. Assuming updated_at as requested.
            if response.data:
                return response.data[0].get("data", [])
            return []
        except Exception as e:
            logging.error(f"Failed to fetch predictions from Supabase: {e}")
            return {"error": str(e)}
