"""Entidades de domínio.

Esta camada é Python puro: não conhece OpenCV, FastAPI, SQLAlchemy nem NumPy.
É o "coração" da aplicação e pode ser testada sem nenhuma dependência externa.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class MetalQuality(str, Enum):
    """Classificação final de qualidade da amostra de metal."""

    PREMIUM = "PREMIUM"
    STANDARD = "STANDARD"
    LOW = "LOW"
    REJECTED = "REJECTED"


@dataclass(frozen=True, slots=True)
class ImageSize:
    width: int
    height: int

    @property
    def area(self) -> int:
        return self.width * self.height


@dataclass(frozen=True, slots=True)
class BoundingBox:
    """Região retangular (em pixels da imagem original) onde há uma impureza."""

    x: int
    y: int
    width: int
    height: int
    # Peso do último estágio do cascade (levelWeights). NÃO é uma probabilidade,
    # mas é útil para ordenar/filtrar detecções.
    score: float | None = None

    @property
    def area(self) -> int:
        return self.width * self.height


@dataclass(frozen=True, slots=True)
class DetectionOutput:
    """Resultado bruto do motor de visão (porta ImpurityDetector)."""

    image_size: ImageSize
    boxes: list[BoundingBox]
    annotated_image: bytes
    annotated_extension: str = ".jpg"


@dataclass(slots=True)
class Inspection:
    """Agregado principal: uma inspeção de uma amostra de metal."""

    id: str
    original_filename: str
    image_size: ImageSize
    impurity_area_ratio: float
    quality: MetalQuality
    processing_time_ms: float
    original_image_key: str
    annotated_image_key: str
    created_at: datetime
    impurities: list[BoundingBox] = field(default_factory=list)

    @property
    def impurity_count(self) -> int:
        return len(self.impurities)
