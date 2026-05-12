# MLB Predictor Engine Backend

MLB Predictor Engine is a FastAPI-based backend that scrapes daily MLB game data, analyzes matchups using a mathematical model, and provides predictions.

## Features
- **Daily Scraper**: Fetches live bullpen data and Vegas odds from Covers.com.
- **Mathematical Engine**: Analyzes matchups based on wRC+, xERA, and other metrics.
- **FastAPI Interface**: Provides API endpoints for latest predictions and manual updates.
- **Supabase Integration**: Persists prediction data.
- **Dockerized**: Easy deployment using Docker and Docker Compose.

## Setup

1. Install `uv`:
   ```bash
   powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```

2. Sync dependencies:
   ```bash
   uv sync
   ```

3. Configure environment variables in `.env`:
   ```env
   SUPABASE_URL=your_supabase_url
   SUPABASE_KEY=your_supabase_key
   CRON_SECRET=your_secret_token
   ```

4. Run locally:
   ```bash
   uv run uvicorn app.main:app --reload
   ```
