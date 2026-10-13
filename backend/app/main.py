"""Ponto de entrada da aplicação FastAPI (camada de entrega)."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.core.config import get_settings
from app.core.container import build_container
from app.domain.exceptions import (
    DetectorUnavailableError,
    DomainError,
    InspectionNotFoundError,
    InvalidImageError,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")

settings = get_settings()
settings.images_dir.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    container = build_container(settings)
    app.state.container = container
    try:
        yield
    finally:
        container.shutdown()


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Detecção de impurezas em metais raros com classificadores Haar Cascade.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(router, prefix=settings.api_prefix)

# Imagens originais e anotadas servidas diretamente do filesystem
app.mount("/media", StaticFiles(directory=settings.images_dir), name="media")


# ---------------------------------------------- tradução de erros de domínio
_ERROR_STATUS: dict[type[DomainError], int] = {
    InvalidImageError: status.HTTP_422_UNPROCESSABLE_ENTITY,
    InspectionNotFoundError: status.HTTP_404_NOT_FOUND,
    DetectorUnavailableError: status.HTTP_503_SERVICE_UNAVAILABLE,
}


@app.exception_handler(DomainError)
async def domain_error_handler(_: Request, exc: DomainError) -> JSONResponse:
    code = _ERROR_STATUS.get(type(exc), status.HTTP_400_BAD_REQUEST)
    detail = str(exc) or exc.__class__.__name__
    if isinstance(exc, InspectionNotFoundError):
        detail = f"Inspeção '{exc}' não encontrada."
    return JSONResponse(status_code=code, content={"detail": detail})
