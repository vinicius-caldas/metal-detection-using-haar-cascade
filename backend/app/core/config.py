"""Configuração via variáveis de ambiente (12-factor, sem dependências extras)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]  # .../backend


def _env_float(name: str, default: float | None) -> float | None:
    raw = os.getenv(name)
    return float(raw) if raw not in (None, "") else default


@dataclass(frozen=True, slots=True)
class Settings:
    app_name: str = "Haar Impurity Inspector"
    api_prefix: str = "/api/v1"

    storage_dir: Path = field(
        default_factory=lambda: Path(os.getenv("STORAGE_DIR", BASE_DIR / "storage"))
    )
    cascade_path: Path = field(
        default_factory=lambda: Path(os.getenv("CASCADE_PATH", BASE_DIR / "models" / "cascade.xml"))
    )
    cors_origins: list[str] = field(
        default_factory=lambda: [
            o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",") if o.strip()
        ]
    )
    max_upload_mb: int = field(default_factory=lambda: int(os.getenv("MAX_UPLOAD_MB", "15")))
    inference_workers: int = field(
        default_factory=lambda: int(os.getenv("INFERENCE_WORKERS", str(min(4, os.cpu_count() or 1))))
    )

    # Hiperparâmetros do detectMultiScale
    haar_scale_factor: float = field(default_factory=lambda: float(os.getenv("HAAR_SCALE_FACTOR", "1.1")))
    haar_min_neighbors: int = field(default_factory=lambda: int(os.getenv("HAAR_MIN_NEIGHBORS", "5")))
    haar_min_size: int = field(default_factory=lambda: int(os.getenv("HAAR_MIN_SIZE", "12")))
    haar_max_side: int = field(default_factory=lambda: int(os.getenv("HAAR_MAX_SIDE", "1600")))
    haar_min_score: float | None = field(default_factory=lambda: _env_float("HAAR_MIN_SCORE", None))

    @property
    def db_path(self) -> Path:
        return self.storage_dir / "inspections.db"

    @property
    def images_dir(self) -> Path:
        return self.storage_dir / "images"

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


def get_settings() -> Settings:
    return Settings()
