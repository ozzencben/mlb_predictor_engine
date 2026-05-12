from httpx import AsyncClient, Limits, Timeout
from typing import Optional

class AsyncClientManager:
    client: Optional[AsyncClient] = None

    @classmethod
    async def setup(cls) -> None:
        """AsyncClient instance'ını konfigüre eder ve başlatır."""
        cls.client = AsyncClient(
            limits=Limits(max_keepalive_connections=5, max_connections=20),
            timeout=Timeout(10.0, read=15.0),
            headers={"User-Agent": "MLB-Predictor-Engine/2.0"}
        )

    @classmethod
    async def teardown(cls) -> None:
        """Connection pool'u güvenli şekilde kapatır."""
        if cls.client:
            await cls.client.aclose()
            cls.client = None

    @classmethod
    def get_client(cls) -> AsyncClient:
        if cls.client is None:
            raise RuntimeError("HTTPX Client başlatılmadı.")
        return cls.client