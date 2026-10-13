"""Portas (interfaces) do domínio — Dependency Inversion Principle.

Os casos de uso dependem destas abstrações; a camada de infraestrutura
fornece as implementações concretas (OpenCV, SQLite, sistema de arquivos).
"""

from __future__ import annotations

from typing import Protocol, Sequence

from app.domain.entities import DetectionOutput, Inspection


class ImpurityDetector(Protocol):
    """Motor de visão computacional."""

    def detect(self, image_bytes: bytes) -> DetectionOutput:
        """Decodifica a imagem, detecta impurezas e devolve a imagem anotada.

        Raises:
            InvalidImageError: se os bytes não formarem uma imagem válida.
        """
        ...


class InspectionRepository(Protocol):
    """Persistência dos metadados das inspeções."""

    def add(self, inspection: Inspection) -> None: ...

    def get(self, inspection_id: str) -> Inspection | None: ...

    def list(self, limit: int = 20, offset: int = 0) -> Sequence[Inspection]: ...


class ImageStorage(Protocol):
    """Armazenamento binário das imagens (original e anotada)."""

    def save(self, key: str, data: bytes) -> str:
        """Persiste `data` sob a chave relativa `key` e devolve a chave."""
        ...

    def delete(self, key: str) -> None: ...
