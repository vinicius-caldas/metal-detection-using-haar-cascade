"""Casos de uso de leitura (consulta de histórico)."""

from __future__ import annotations

from typing import Sequence

from app.domain.entities import Inspection
from app.domain.exceptions import InspectionNotFoundError
from app.domain.ports import InspectionRepository


class ListInspectionsUseCase:
    MAX_LIMIT = 100

    def __init__(self, repository: InspectionRepository) -> None:
        self._repository = repository

    def execute(self, limit: int = 20, offset: int = 0) -> Sequence[Inspection]:
        limit = max(1, min(limit, self.MAX_LIMIT))
        offset = max(0, offset)
        return self._repository.list(limit=limit, offset=offset)


class GetInspectionUseCase:
    def __init__(self, repository: InspectionRepository) -> None:
        self._repository = repository

    def execute(self, inspection_id: str) -> Inspection:
        inspection = self._repository.get(inspection_id)
        if inspection is None:
            raise InspectionNotFoundError(inspection_id)
        return inspection
