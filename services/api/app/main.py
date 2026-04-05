from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.errors import AppError, logger as app_logger
from app.migrations import prepare_database
from app.routes.explanations import router as explanations_router
from app.routes.health import router as health_router
from app.routes.market import router as market_router
from app.routes.opportunities import router as opportunities_router
from app.routes.paper_trading import router as paper_trading_router
from app.routes.risk import router as risk_router
from app.routes.session import router as session_router
from app.routes.signals import router as signals_router
from app.routes.watchlist import router as watchlist_router


logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(_: FastAPI):
    prepare_database()
    yield

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Core inference and orchestration API for the Unveni options assistant.",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["*"]
)


def build_error_payload(code: str, message: str) -> dict[str, object]:
    return {
        "error": {
            "code": code,
            "message": message
        }
    }


@app.exception_handler(AppError)
async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
    app_logger.log(exc.log_level, "%s", exc)
    return JSONResponse(
        status_code=exc.status_code,
        content=build_error_payload(exc.code, exc.message)
    )


@app.exception_handler(HTTPException)
async def handle_http_error(_: Request, exc: HTTPException) -> JSONResponse:
    code = exc.detail if isinstance(exc.detail, str) else "http_error"
    message = exc.detail if isinstance(exc.detail, str) else "Request failed."
    return JSONResponse(
        status_code=exc.status_code,
        content=build_error_payload(code, message)
    )


@app.exception_handler(RequestValidationError)
async def handle_validation_error(
    _: Request,
    exc: RequestValidationError
) -> JSONResponse:
    field_errors = []
    for error in exc.errors():
        location = ".".join(str(part) for part in error.get("loc", ()))
        field_errors.append(
            {
                "field": location,
                "message": error.get("msg", "Invalid value.")
            }
        )
    return JSONResponse(
        status_code=422,
        content={
            **build_error_payload("validation_error", "Request validation failed."),
            "fields": field_errors
        }
    )


@app.exception_handler(Exception)
async def handle_unexpected_error(_: Request, exc: Exception) -> JSONResponse:
    app_logger.exception("Unexpected API failure", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content=build_error_payload(
            "internal_server_error",
            "The server could not complete the request."
        )
    )


app.include_router(health_router)
app.include_router(session_router)
app.include_router(market_router)
app.include_router(opportunities_router)
app.include_router(explanations_router)
app.include_router(risk_router)
app.include_router(signals_router)
app.include_router(watchlist_router)
app.include_router(paper_trading_router)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "service": settings.app_name,
        "docs": "/docs",
        "health": "/health"
    }
