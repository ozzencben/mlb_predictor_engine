from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.core.http_client import AsyncClientManager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Veri akışı için HTTPX Client'ı ayağa kaldır
    await AsyncClientManager.setup()
    yield
    # Shutdown: Kaynak sızıntısını önlemek için kapat
    await AsyncClientManager.teardown()

