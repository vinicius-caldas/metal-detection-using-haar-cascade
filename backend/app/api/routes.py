"""Rotas REST de inspeção.

Concorrência: os handlers são `async`. O I/O de rede (upload) é aguardado no
event loop; o trabalho CPU-bound (decodificar matriz, Haar Cascade, gravar
arquivos/SQLite) é despachado para um ThreadPoolExecutor dedicado via
`loop.run_in_executor`. Assim o servidor continua respondendo a outras
requisições enquanto imagens são processadas.
"""

from __future__ import annotations

import asyncio
from functools import partial

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status

from app.api.schemas import HealthOut, InspectionOut, InspectionSummaryOut, to_detail, to_summary
from app.application.use_cases.detect_impurities import DetectImpuritiesCommand
from app.core.container import Container

router = APIRouter()

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/bmp", "image/tiff"}
_CHUNK = 1024 * 1024


def get_container(request: Request) -> Container:
    return request.app.state.container


async def _run_blocking(container: Container, fn, *args, **kwargs):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(container.executor, partial(fn, *args, **kwargs))


async def _read_limited(file: UploadFile, max_bytes: int) -> bytes:
    """Lê o upload em chunks, abortando cedo se ultrapassar o limite."""
    buffer = bytearray()
    while chunk := await file.read(_CHUNK):
        buffer.extend(chunk)
        if len(buffer) > max_bytes:
            raise HTTPException(
                status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                f"Arquivo excede {max_bytes // (1024 * 1024)} MB.",
            )
    return bytes(buffer)


@router.get("/health", response_model=HealthOut, tags=["infra"])
async def health(container: Container = Depends(get_container)) -> HealthOut:
    return HealthOut(
        status="ok",
        detector_ready=container.detect_impurities is not None,
        detector_error=container.detector_error,
    )


@router.post(
    "/inspections",
    response_model=InspectionOut,
    status_code=status.HTTP_201_CREATED,
    tags=["inspections"],
    summary="Envia imagem de metal e detecta impurezas via Haar Cascade",
)
async def create_inspection(
    file: UploadFile = File(..., description="Imagem (JPEG/PNG/BMP/TIFF) da amostra"),
    container: Container = Depends(get_container),
) -> InspectionOut:
    use_case = container.detect_impurities
    if use_case is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, container.detector_error)

    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            f"Tipo '{file.content_type}' não suportado.",
        )

    data = await _read_limited(file, container.settings.max_upload_bytes)
    command = DetectImpuritiesCommand(filename=file.filename or "upload.jpg", image_bytes=data)

    inspection = await _run_blocking(container, use_case.execute, command)
    return to_detail(inspection)


@router.get("/inspections", response_model=list[InspectionSummaryOut], tags=["inspections"])
async def list_inspections(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    container: Container = Depends(get_container),
) -> list[InspectionSummaryOut]:
    items = await _run_blocking(container, container.list_inspections.execute, limit, offset)
    return [to_summary(i) for i in items]


@router.get("/inspections/{inspection_id}", response_model=InspectionOut, tags=["inspections"])
async def get_inspection(
    inspection_id: str, container: Container = Depends(get_container)
) -> InspectionOut:
    inspection = await _run_blocking(container, container.get_inspection.execute, inspection_id)
    return to_detail(inspection)
