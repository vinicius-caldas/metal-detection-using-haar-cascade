"""Implementação SQLite da porta `InspectionRepository`."""

from __future__ import annotations

from datetime import timezone
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.domain.entities import BoundingBox, ImageSize, Inspection, MetalQuality
from app.infrastructure.persistence.models import ImpurityModel, InspectionModel


class SqliteInspectionRepository:
    def __init__(self, session_factory: sessionmaker) -> None:
        self._session_factory = session_factory

    def add(self, inspection: Inspection) -> None:
        with self._session_factory.begin() as session:
            session.add(self._to_model(inspection))

    def get(self, inspection_id: str) -> Inspection | None:
        with self._session_factory() as session:
            model = session.get(InspectionModel, inspection_id)
            return self._to_entity(model) if model else None

    def list(self, limit: int = 20, offset: int = 0) -> Sequence[Inspection]:
        stmt = (
            select(InspectionModel)
            .order_by(InspectionModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        with self._session_factory() as session:
            return [self._to_entity(m) for m in session.scalars(stmt).all()]

    # -------------------------------------------------------------- mappers
    @staticmethod
    def _to_model(e: Inspection) -> InspectionModel:
        return InspectionModel(
            id=e.id,
            original_filename=e.original_filename,
            image_width=e.image_size.width,
            image_height=e.image_size.height,
            impurity_count=e.impurity_count,
            impurity_area_ratio=e.impurity_area_ratio,
            quality=e.quality.value,
            processing_time_ms=e.processing_time_ms,
            original_image_key=e.original_image_key,
            annotated_image_key=e.annotated_image_key,
            created_at=e.created_at,
            impurities=[
                ImpurityModel(x=b.x, y=b.y, width=b.width, height=b.height, score=b.score)
                for b in e.impurities
            ],
        )

    @staticmethod
    def _to_entity(m: InspectionModel) -> Inspection:
        created_at = m.created_at
        if created_at.tzinfo is None:  # SQLite não guarda timezone
            created_at = created_at.replace(tzinfo=timezone.utc)
        return Inspection(
            id=m.id,
            original_filename=m.original_filename,
            image_size=ImageSize(width=m.image_width, height=m.image_height),
            impurity_area_ratio=m.impurity_area_ratio,
            quality=MetalQuality(m.quality),
            processing_time_ms=m.processing_time_ms,
            original_image_key=m.original_image_key,
            annotated_image_key=m.annotated_image_key,
            created_at=created_at,
            impurities=[
                BoundingBox(x=i.x, y=i.y, width=i.width, height=i.height, score=i.score)
                for i in m.impurities
            ],
        )
