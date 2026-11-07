from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import BaseModel

from app.config import settings
from app.common.mongo import close_mongo, init_mongo
from app.common.qdrant import close_qdrant, get_qdrant_client
from app.module.prompt_evaluation.router import router as prompt_evaluation_router
from app.module.multi_model_smart.router import router as multi_model_smart_router
from app.module.multi_model_smart.lifecycle import seed_datasets


class MessageResponse(BaseModel):
    message: str
    docs_url: str


class HealthResponse(BaseModel):
    status: str


class ConfigStatusResponse(BaseModel):
    app_name: str
    environment: str
    reload_enabled: bool
    gemini_configured: bool


class DemoRequest(BaseModel):
    name: str = "Developer"


class DemoResponse(BaseModel):
    message: str
    received_name: str
    service: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.mongo_enabled:
        await init_mongo()
        await seed_datasets()
    if settings.qdrant_enabled:
        get_qdrant_client().get_collections()
    yield
    if settings.mongo_enabled:
        await close_mongo()
    if settings.qdrant_enabled:
        close_qdrant()


app = FastAPI(
    title=settings.app_name,
    description="FastAPI demo project managed by uv and runnable with Docker.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)
app.include_router(prompt_evaluation_router)
app.include_router(multi_model_smart_router)


@app.get(
    "/",
    response_model=MessageResponse,
    summary="Welcome endpoint",
    tags=["General"],
)
async def read_root() -> MessageResponse:
    return MessageResponse(
        message="Welcome to Demo AI API",
        docs_url="/docs",
    )


@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Check application health",
    tags=["Monitoring"],
)
async def health_check() -> HealthResponse:
    return HealthResponse(status="healthy")

async def call_demo_service(payload: DemoRequest) -> DemoResponse:
    name = payload.name.strip() or "Developer"
    return DemoResponse(
        message=f"Hello, {name}! The demo service is working.",
        received_name=name,
        service="local-demo-service",
    )

