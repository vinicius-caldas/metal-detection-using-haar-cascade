"""Caso de uso: detectar impurezas em uma imagem de metal.

Orquestra as portas do domínio (detector, storage, repositório) sem conhecer
nenhuma tecnologia concreta. É código síncrono e CPU-bound por natureza; a
camada de entrega (FastAPI) é responsável por executá-lo fora do event loop.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import PurePath
from typing import Callable

from app.domain.entities import Inspection
from app.domain.exceptions import InvalidImageError
from app.domain.ports import ImageStorage, ImpurityDetector, InspectionRepository
from app.domain.services import QualityPolicy

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"})


@dataclass(frozen=True, slots=True)
class DetectImpuritiesCommand:
    """DTO de entrada do caso de uso."""

    filename: str
    image_bytes: bytes


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return uuid.uuid4().hex


class DetectImpuritiesUseCase:
    def __init__(
        self,
        detector: ImpurityDetector,
        repository: InspectionRepository,
        storage: ImageStorage,
        policy: QualityPolicy | None = None,
        clock: Callable[[], datetime] = _utcnow,
        id_factory: Callable[[], str] = _new_id,
    ) -> None:
        self._detector = detector
        self._repository = repository
        self._storage = storage
        self._policy = policy or QualityPolicy()
        self._clock = clock
        self._id_factory = id_factory

    def execute(self, command: DetectImpuritiesCommand) -> Inspection:
        if not command.image_bytes:
            raise InvalidImageError("Arquivo vazio.")

        extension = PurePath(command.filename).suffix.lower()
        if extension not in ALLOWED_EXTENSIONS:
            raise InvalidImageError(
                f"Extensão '{extension or '?'}' não suportada. "
                f"Use: {', '.join(sorted(ALLOWED_EXTENSIONS))}."
            )

        started = time.perf_counter()

        # 1. Visão computacional (Haar Cascade) — porta ImpurityDetector
        output = self._detector.detect(command.image_bytes)

        # 2. Regra de negócio pura — classificação de qualidade
        ratio, quality = self._policy.evaluate(output.boxes, output.image_size)

        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)

        # 3. Persistência dos binários no filesystem
        inspection_id = self._id_factory()
        original_key = self._storage.save(
            f"{inspection_id}/original{extension}", command.image_bytes
        )
        annotated_key = self._storage.save(
            f"{inspection_id}/annotated{output.annotated_extension}",
            output.annotated_image,
        )

        inspection = Inspection(
            id=inspection_id,
            original_filename=PurePath(command.filename).name,
            image_size=output.image_size,
            impurity_area_ratio=ratio,
            quality=quality,
            processing_time_ms=elapsed_ms,
            original_image_key=original_key,
            annotated_image_key=annotated_key,
            created_at=self._clock(),
            impurities=list(output.boxes),
        )

        # 4. Persistência dos metadados — com compensação em caso de falha
        try:
            self._repository.add(inspection)
        except Exception:
            logger.exception("Falha ao persistir inspeção %s; revertendo arquivos.", inspection_id)
            self._storage.delete(original_key)
            self._storage.delete(annotated_key)
            raise

        logger.info(
            "Inspeção %s: %d impurezas, %.4f%% da área, qualidade=%s (%.1f ms)",
            inspection_id,
            inspection.impurity_count,
            ratio * 100,
            quality.value,
            elapsed_ms,
        )
        return inspection
