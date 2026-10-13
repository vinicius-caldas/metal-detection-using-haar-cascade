"""Adaptador OpenCV: implementação concreta da porta `ImpurityDetector`.

Detalhes de projeto relevantes para a banca:

* `cv2.CascadeClassifier` NÃO é thread-safe. Como a API executa inferências
  em um pool de threads, cada thread mantém sua própria instância
  (`threading.local`). O XML é validado uma única vez no construtor.
* As funções pesadas do OpenCV liberam o GIL, então threads paralelas
  aproveitam múltiplos núcleos de verdade.
* Imagens muito grandes são reduzidas antes da detecção (o custo do cascade
  cresce com a área) e as coordenadas são reescaladas para a imagem original.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from app.domain.entities import BoundingBox, DetectionOutput, ImageSize
from app.domain.exceptions import DetectorUnavailableError, InvalidImageError


@dataclass(frozen=True, slots=True)
class HaarParams:
    scale_factor: float = 1.1
    min_neighbors: int = 5
    min_size: int = 12  # px (no espaço da imagem possivelmente reduzida)
    max_detection_side: int = 1600  # px — lado máximo antes de reduzir
    min_score: float | None = None  # filtro opcional por levelWeights
    clahe_clip_limit: float = 2.0
    clahe_tile_grid: int = 8


_BOX_COLOR = (0, 0, 255)  # BGR — vermelho
_TEXT_COLOR = (255, 255, 255)


class HaarCascadeDetector:
    def __init__(self, cascade_path: Path, params: HaarParams | None = None) -> None:
        self._cascade_path = Path(cascade_path)
        self._params = params or HaarParams()

        if not self._cascade_path.is_file():
            raise DetectorUnavailableError(
                f"Modelo Haar Cascade não encontrado em '{self._cascade_path}'. "
                "Treine o modelo (backend/training) ou ajuste CASCADE_PATH."
            )
        if cv2.CascadeClassifier(str(self._cascade_path)).empty():
            raise DetectorUnavailableError(
                f"Arquivo '{self._cascade_path}' não é um cascade XML válido."
            )

        self._local = threading.local()

    # ------------------------------------------------------------------ API
    def detect(self, image_bytes: bytes) -> DetectionOutput:
        image = self._decode(image_bytes)
        height, width = image.shape[:2]

        gray, scale = self._preprocess(image)
        boxes = self._run_cascade(gray, scale, width, height)
        annotated = self._annotate(image, boxes)

        ok, encoded = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 90])
        if not ok:  # pragma: no cover — falha de encoder é improvável
            raise RuntimeError("Falha ao codificar a imagem anotada.")

        return DetectionOutput(
            image_size=ImageSize(width=width, height=height),
            boxes=boxes,
            annotated_image=encoded.tobytes(),
            annotated_extension=".jpg",
        )

    # ------------------------------------------------------------- internos
    def _thread_resources(self) -> tuple[cv2.CascadeClassifier, cv2.CLAHE]:
        res = getattr(self._local, "resources", None)
        if res is None:
            classifier = cv2.CascadeClassifier(str(self._cascade_path))
            clahe = cv2.createCLAHE(
                clipLimit=self._params.clahe_clip_limit,
                tileGridSize=(self._params.clahe_tile_grid,) * 2,
            )
            res = (classifier, clahe)
            self._local.resources = res
        return res

    @staticmethod
    def _decode(image_bytes: bytes) -> np.ndarray:
        buffer = np.frombuffer(image_bytes, dtype=np.uint8)
        image = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
        if image is None:
            raise InvalidImageError("Não foi possível decodificar a imagem enviada.")
        return image

    def _preprocess(self, image: np.ndarray) -> tuple[np.ndarray, float]:
        """Escala de cinza -> redução opcional -> CLAHE -> blur leve.

        CLAHE (equalização adaptativa) compensa a iluminação irregular típica
        de micrografias metalográficas, realçando inclusões escuras/claras.
        """
        _, clahe = self._thread_resources()
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        h, w = gray.shape
        longest = max(h, w)
        scale = 1.0
        if longest > self._params.max_detection_side:
            scale = self._params.max_detection_side / longest
            gray = cv2.resize(gray, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)

        gray = clahe.apply(gray)
        gray = cv2.GaussianBlur(gray, (3, 3), 0)
        return gray, scale

    def _run_cascade(
        self, gray: np.ndarray, scale: float, img_w: int, img_h: int
    ) -> list[BoundingBox]:
        classifier, _ = self._thread_resources()
        p = self._params

        rects, _levels, weights = classifier.detectMultiScale3(
            gray,
            scaleFactor=p.scale_factor,
            minNeighbors=p.min_neighbors,
            minSize=(p.min_size, p.min_size),
            outputRejectLevels=True,
        )
        if len(rects) == 0:
            return []

        scores = np.asarray(weights, dtype=float).reshape(-1)
        inv = 1.0 / scale
        boxes: list[BoundingBox] = []
        for (x, y, w, h), score in zip(rects, scores):
            if p.min_score is not None and score < p.min_score:
                continue
            # Reescala para a resolução original e garante limites válidos
            bx, by = int(round(x * inv)), int(round(y * inv))
            bw = min(int(round(w * inv)), img_w - bx)
            bh = min(int(round(h * inv)), img_h - by)
            boxes.append(BoundingBox(x=bx, y=by, width=bw, height=bh, score=round(float(score), 4)))

        boxes.sort(key=lambda b: b.score or 0.0, reverse=True)
        return boxes

    @staticmethod
    def _annotate(image: np.ndarray, boxes: list[BoundingBox]) -> np.ndarray:
        annotated = image.copy()
        thickness = max(1, round(max(image.shape[:2]) / 600))
        font_scale = 0.4 * thickness
        for idx, b in enumerate(boxes, start=1):
            cv2.rectangle(annotated, (b.x, b.y), (b.x + b.width, b.y + b.height), _BOX_COLOR, thickness)
            label = f"#{idx}"
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 1)
            ty = max(b.y, th + 4)
            cv2.rectangle(annotated, (b.x, ty - th - 4), (b.x + tw + 4, ty), _BOX_COLOR, -1)
            cv2.putText(
                annotated, label, (b.x + 2, ty - 2),
                cv2.FONT_HERSHEY_SIMPLEX, font_scale, _TEXT_COLOR, 1, cv2.LINE_AA,
            )
        return annotated
