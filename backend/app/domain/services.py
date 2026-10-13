"""Regras de negócio puras: classificação da qualidade do metal."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from app.domain.entities import BoundingBox, ImageSize, MetalQuality


def union_area(boxes: Sequence[BoundingBox]) -> int:
    """Área da união dos retângulos (sem contar sobreposição duas vezes).

    Varredura por compressão de coordenadas no eixo X + merge de intervalos
    em Y. O(n² log n) — mais que suficiente para dezenas/centenas de caixas.
    """
    if not boxes:
        return 0

    xs = sorted({b.x for b in boxes} | {b.x + b.width for b in boxes})
    total = 0
    for x0, x1 in zip(xs, xs[1:]):
        intervals = sorted(
            (b.y, b.y + b.height) for b in boxes if b.x <= x0 and b.x + b.width >= x1
        )
        covered = 0
        cur_start: int | None = None
        cur_end = 0
        for start, end in intervals:
            if cur_start is None or start > cur_end:
                if cur_start is not None:
                    covered += cur_end - cur_start
                cur_start, cur_end = start, end
            else:
                cur_end = max(cur_end, end)
        if cur_start is not None:
            covered += cur_end - cur_start
        total += covered * (x1 - x0)
    return total


@dataclass(frozen=True, slots=True)
class QualityPolicy:
    """Política de grading baseada em fração de área contaminada e contagem.

    Os limiares são parametrizáveis para que possam ser calibrados com
    especialistas em metalurgia sem alterar o código.
    """

    premium_max_ratio: float = 0.005  # 0,5 % da área
    premium_max_count: int = 2
    standard_max_ratio: float = 0.02  # 2 %
    standard_max_count: int = 10
    low_max_ratio: float = 0.05  # 5 %

    def evaluate(
        self, boxes: Sequence[BoundingBox], image_size: ImageSize
    ) -> tuple[float, MetalQuality]:
        if image_size.area <= 0:
            raise ValueError("Imagem com área zero.")

        ratio = union_area(boxes) / image_size.area
        count = len(boxes)

        if ratio <= self.premium_max_ratio and count <= self.premium_max_count:
            quality = MetalQuality.PREMIUM
        elif ratio <= self.standard_max_ratio and count <= self.standard_max_count:
            quality = MetalQuality.STANDARD
        elif ratio <= self.low_max_ratio:
            quality = MetalQuality.LOW
        else:
            quality = MetalQuality.REJECTED

        return round(ratio, 6), quality
