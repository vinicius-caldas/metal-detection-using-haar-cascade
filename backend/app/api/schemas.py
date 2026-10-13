"""Contratos HTTP (Pydantic). Separados das entidades de domínio de propósito."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.domain.entities import Inspection, MetalQuality


class BoundingBoxOut(BaseModel):
    x: int
    y: int
    width: int
    height: int
    score: float | None = None


class ImageSizeOut(BaseModel):
    width: int
    height: int


class InspectionSummaryOut(BaseModel):
    id: str
    original_filename: str
    quality: MetalQuality
    impurity_count: int
    impurity_area_ratio: float = Field(description="Fração (0–1) da área contaminada")
    created_at: datetime
    annotated_image_url: str


class InspectionOut(InspectionSummaryOut):
    image: ImageSizeOut
    processing_time_ms: float
    original_image_url: str
    impurities: list[BoundingBoxOut]


class HealthOut(BaseModel):
    status: str
    detector_ready: bool
    detector_error: str | None = None


def _media_url(key: str) -> str:
    return f"/media/{key}"


def to_summary(e: Inspection) -> InspectionSummaryOut:
    return InspectionSummaryOut(
        id=e.id,
        original_filename=e.original_filename,
        quality=e.quality,
        impurity_count=e.impurity_count,
        impurity_area_ratio=e.impurity_area_ratio,
        created_at=e.created_at,
        annotated_image_url=_media_url(e.annotated_image_key),
    )


def to_detail(e: Inspection) -> InspectionOut:
    return InspectionOut(
        **to_summary(e).model_dump(),
        image=ImageSizeOut(width=e.image_size.width, height=e.image_size.height),
        processing_time_ms=e.processing_time_ms,
        original_image_url=_media_url(e.original_image_key),
        impurities=[
            BoundingBoxOut(x=b.x, y=b.y, width=b.width, height=b.height, score=b.score)
            for b in e.impurities
        ],
    )
