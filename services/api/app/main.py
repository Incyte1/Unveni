from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routes.health import router as health_router
from app.routes.opportunities import router as opportunities_router
from app.routes.risk import router as risk_router

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Core inference and orchestration API for the Unveni options assistant."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"]
)

app.include_router(health_router)
app.include_router(opportunities_router)
app.include_router(risk_router)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "service": settings.app_name,
        "docs": "/docs",
        "health": "/health"
    }

