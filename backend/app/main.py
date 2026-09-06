from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api import zones, roads, emergency, weather, reports, alerts, auth, radar, chat, tts
from app.services.alert_service import alert_service

logger = logging.getLogger("ner_lews.main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI Lifespan Context Manager.
    Manages application startup and shutdown lifecycle hooks.
    """
    logger.info("Initializing NER-LEWS backend application (Environment: %s)...", settings.ENVIRONMENT)

    # 1. Startup: Start background monitoring worker if enabled
    if settings.ENABLE_BACKGROUND_WORKER:
        await alert_service.start_monitoring_worker(
            interval_seconds=settings.MONITORING_INTERVAL_SECONDS
        )
        logger.info(
            "Background alert monitoring worker started (interval=%.1fs).",
            settings.MONITORING_INTERVAL_SECONDS
        )
    else:
        logger.info("Background alert monitoring worker is disabled via configuration.")

    yield  # Application serves HTTP requests

    # 2. Shutdown: Gracefully stop background worker
    logger.info("Shutting down NER-LEWS backend application...")
    await alert_service.stop_monitoring_worker()
    logger.info("Background alert monitoring worker terminated cleanly.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    description="Monochrome Landslide Early Warning System REST API for North-East India (NER-LEWS)",
    lifespan=lifespan,
)

# Enable CORS for frontend clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API v1 Routes
app.include_router(zones.router, prefix=settings.API_V1_STR)
app.include_router(roads.router, prefix=settings.API_V1_STR)
app.include_router(emergency.router, prefix=settings.API_V1_STR)
app.include_router(weather.router, prefix=settings.API_V1_STR)
app.include_router(reports.router, prefix=settings.API_V1_STR)
app.include_router(alerts.router, prefix=settings.API_V1_STR)
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(radar.router, prefix=settings.API_V1_STR)
app.include_router(chat.router, prefix=settings.API_V1_STR)
app.include_router(tts.router, prefix=settings.API_V1_STR)

@app.get("/api/v1/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "NER-LEWS Backend API",
        "version": "1.0.0",
        "region": "North-East India (Meghalaya, Assam, Sikkim)",
        "worker": alert_service.get_worker_status()
    }

@app.get("/")
async def root():
    return {
        "message": "NER-LEWS API is active. Visit /api/v1/docs for interactive OpenAPI documentation.",
        "health": "/api/v1/health"
    }
