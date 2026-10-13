"""Testes unitários do caso de uso — usando fakes no lugar das portas.

Demonstra o benefício da Clean Architecture: a lógica de negócio é testada
sem OpenCV, sem banco e sem HTTP.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.application.use_cases.detect_impurities import (
    DetectImpuritiesCommand,
    DetectImpuritiesUseCase,
)
from app.domain.entities import BoundingBox, DetectionOutput, ImageSize, Inspection, MetalQuality
from app.domain.exceptions import InvalidImageError
from app.domain.services import QualityPolicy, union_area


class FakeDetector:
    def __init__(self, boxes: list[BoundingBox], size=ImageSize(1000, 1000)) -> None:
        self.boxes, self.size = boxes, size

    def detect(self, image_bytes: bytes) -> DetectionOutput:
        return DetectionOutput(self.size, self.boxes, b"annotated")


class FakeStorage:
    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}

    def save(self, key: str, data: bytes) -> str:
        self.files[key] = data
        return key

    def delete(self, key: str) -> None:
        self.files.pop(key, None)


class FakeRepo:
    def __init__(self, fail: bool = False) -> None:
        self.items: dict[str, Inspection] = {}
        self.fail = fail

    def add(self, inspection: Inspection) -> None:
        if self.fail:
            raise RuntimeError("db down")
        self.items[inspection.id] = inspection

    def get(self, inspection_id):  # pragma: no cover
        return self.items.get(inspection_id)

    def list(self, limit=20, offset=0):  # pragma: no cover
        return list(self.items.values())


def make_uc(boxes, repo=None, storage=None):
    return DetectImpuritiesUseCase(
        FakeDetector(boxes),
        repo or FakeRepo(),
        storage or FakeStorage(),
        QualityPolicy(),
        clock=lambda: datetime(2026, 1, 1, tzinfo=timezone.utc),
        id_factory=lambda: "abc123",
    )


def test_clean_sample_is_premium():
    result = make_uc([]).execute(DetectImpuritiesCommand("amostra.png", b"img"))
    assert result.quality is MetalQuality.PREMIUM
    assert result.impurity_count == 0
    assert result.original_image_key == "abc123/original.png"


def test_heavily_contaminated_sample_is_rejected():
    boxes = [BoundingBox(0, 0, 300, 300)]  # 9 % da área
    result = make_uc(boxes).execute(DetectImpuritiesCommand("a.jpg", b"img"))
    assert result.quality is MetalQuality.REJECTED
    assert result.impurity_area_ratio == pytest.approx(0.09)


def test_rejects_unsupported_extension():
    with pytest.raises(InvalidImageError):
        make_uc([]).execute(DetectImpuritiesCommand("a.gif", b"img"))


def test_rejects_empty_file():
    with pytest.raises(InvalidImageError):
        make_uc([]).execute(DetectImpuritiesCommand("a.jpg", b""))


def test_files_are_rolled_back_when_repository_fails():
    storage = FakeStorage()
    with pytest.raises(RuntimeError):
        make_uc([], repo=FakeRepo(fail=True), storage=storage).execute(
            DetectImpuritiesCommand("a.jpg", b"img")
        )
    assert storage.files == {}


def test_union_area_does_not_double_count_overlap():
    a = BoundingBox(0, 0, 10, 10)
    b = BoundingBox(5, 5, 10, 10)
    assert union_area([a, b]) == 100 + 100 - 25
    assert union_area([a, a]) == 100
