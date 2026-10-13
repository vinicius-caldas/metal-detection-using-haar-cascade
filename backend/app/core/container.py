"""Composition Root: o ÚNICO lugar que conhece todas as implementações concretas.

Monta o grafo de dependências (adapters -> use cases) uma vez no startup.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from sqlalchemy import Engine

from app.application.use_cases.detect_impurities import DetectImpuritiesUseCase
from app.application.use_cases.query_inspections import (
    GetInspectionUseCase,
    ListInspectionsUseCase,
)
from app.core.config import Settings
from app.domain.exceptions import DetectorUnavailableError
from app.domain.services import QualityPolicy
from app.infrastructure.persistence.database import (
    create_session_factory,
    create_sqlite_engine,
    init_db,
)
from app.infrastructure.persistence.sqlite_repository import SqliteInspectionRepository
from app.infrastructure.storage.local_image_storage import LocalImageStorage
from app.infrastructure.vision.haar_detector import HaarCascadeDetector, HaarParams

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class Container:
    settings: Settings
    engine: Engine
    executor: ThreadPoolExecutor
    storage: LocalImageStorage
    detect_impurities: DetectImpuritiesUseCase | None
    list_inspections: ListInspectionsUseCase
    get_inspection: GetInspectionUseCase
    detector_error: str | None = None

    def shutdown(self) -> None:
        self.executor.shutdown(wait=True, cancel_futures=True)
        self.engine.dispose()


def build_container(settings: Settings) -> Container:
    engine = create_sqlite_engine(settings.db_path)
    init_db(engine)
    session_factory = create_session_factory(engine)

    repository = SqliteInspectionRepository(session_factory)
    storage = LocalImageStorage(settings.images_dir)

    # Pool DEDICADO e limitado para inferência: tarefas CPU-bound não competem
    # com o threadpool padrão do Starlette e há backpressure natural.
    executor = ThreadPoolExecutor(
        max_workers=settings.inference_workers, thread_name_prefix="haar-worker"
    )

    detect_uc: DetectImpuritiesUseCase | None = None
    detector_error: str | None = None
    try:
        detector = HaarCascadeDetector(
            settings.cascade_path,
            HaarParams(
                scale_factor=settings.haar_scale_factor,
                min_neighbors=settings.haar_min_neighbors,
                min_size=settings.haar_min_size,
                max_detection_side=settings.haar_max_side,
                min_score=settings.haar_min_score,
            ),
        )
        detect_uc = DetectImpuritiesUseCase(detector, repository, storage, QualityPolicy())
        logger.info("Haar Cascade carregado de %s", settings.cascade_path)
    except DetectorUnavailableError as exc:
        # A API sobe mesmo sem modelo (histórico continua acessível);
        # o endpoint de detecção responde 503 com mensagem clara.
        detector_error = str(exc)
        logger.warning(detector_error)

    return Container(
        settings=settings,
        engine=engine,
        executor=executor,
        storage=storage,
        detect_impurities=detect_uc,
        list_inspections=ListInspectionsUseCase(repository),
        get_inspection=GetInspectionUseCase(repository),
        detector_error=detector_error,
    )
