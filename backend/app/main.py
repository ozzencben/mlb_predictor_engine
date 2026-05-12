from fastapi import FastAPI, Header, HTTPException, Depends
from typing import Optional
import os
import json
import logging
from pathlib import Path
from app.services.prediction_service import PredictionService
from app.core.database import SupabaseManager
from fastapi.middleware.cors import CORSMiddleware

BASE_DIR = Path(__file__).resolve().parent.parent

app = FastAPI(title="MLB Predictor API", version="1.0.0")
db = SupabaseManager()

origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://mlb-predictor-app.vercel.app",
    "https://mlb-predictor-engine-an47qzgkl-ozzencs-projects.vercel.app"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"], 
)

def verify_cron_secret(cron_secret: Optional[str] = Header(None)):
    expected_secret = os.environ.get("CRON_SECRET", "your_super_secret_cron_token_here")
    if cron_secret != expected_secret:
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid CRON_SECRET")

@app.get("/api/v1/predictions/latest")
async def get_latest_predictions():
    """
    Fetches the most recent JSON predictions payload. 
    Falls back to local file if DB is unavailable or mocked.
    """
    data_path = BASE_DIR / "data" / "daily_matchups.json"
    
    # Check if Supabase URL is missing, mocked, or invalid
    supabase_url = os.environ.get("SUPABASE_URL", "")
    is_mock = not supabase_url or "your-project-id" in supabase_url or "mock.supabase.url" in supabase_url
    
    if not is_mock:
        data = db.get_latest_predictions()
        if isinstance(data, dict) and "error" in data:
            logging.warning(f"DB Fetch failed: {data['error']}. Falling back to local data.")
        elif data:
            return {"status": "success", "data": data}
            
    # Local Fallback Logic
    if data_path.exists():
        try:
            with open(data_path, "r", encoding="utf-8") as f:
                local_data = json.load(f)
            return {"status": "success (local fallback)", "data": local_data}
        except Exception as e:
            logging.error(f"Failed to read local fallback file: {e}")
            raise HTTPException(status_code=500, detail="Failed to load predictions from DB and local file.")
            
    raise HTTPException(status_code=404, detail="No predictions found in DB or local fallback.")

@app.post("/api/v1/cron/update", dependencies=[Depends(verify_cron_secret)])
async def update_predictions():
    """
    The Worker endpoint. Scrapes data, runs engine, saves locally, and persists to DB.
    Protected by CRON_SECRET.
    """
    service = PredictionService()
    results = service.run_daily_pipeline()
    
    if results:
        # 1. Save Locally
        data_path = BASE_DIR / "data" / "daily_matchups.json"
        data_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(data_path, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logging.error(f"Failed to save results locally: {e}")
            
        # 2. Save to DB
        db_res = db.save_predictions(results)
        if not db_res:
            logging.warning("Failed to save to Supabase. Results saved locally only.")
            return {"status": "success (local only)", "message": f"Successfully processed and saved {len(results)} matches locally."}
        
        return {"status": "success", "message": f"Successfully processed and saved {len(results)} matches to DB and Local."}
    
    return {"status": "warning", "message": "No matches processed."}