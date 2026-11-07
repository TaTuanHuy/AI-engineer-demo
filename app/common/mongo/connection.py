from beanie import Document, init_beanie
from pymongo import AsyncMongoClient

from app.config import settings


mongo_client: AsyncMongoClient | None = None


async def init_mongo(document_models: list[type[Document]] | None = None) -> None:
    global mongo_client
    mongo_client = AsyncMongoClient(settings.mongo_uri)
    await mongo_client.admin.command("ping")
    await init_beanie(
        database=mongo_client[settings.mongo_database],
        document_models=document_models or [],
    )


async def close_mongo() -> None:
    global mongo_client
    if mongo_client is not None:
        await mongo_client.close()
        mongo_client = None

