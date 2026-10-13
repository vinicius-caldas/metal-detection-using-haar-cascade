"""Avalia o cascade treinado num conjunto de teste anotado (Precision/Recall/F1).

Reutiliza o MESMO adaptador usado em produção (HaarCascadeDetector), garantindo
que as métricas reportadas na banca reflitam exatamente o pipeline da API.

Uso:
    python training/evaluate.py --csv data/test_annotations.csv --images data/test \
        --cascade models/cascade.xml --iou 0.5
(executar a partir da pasta backend/)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.infrastructure.vision.haar_detector import HaarCascadeDetector, HaarParams  # noqa: E402


def iou_matrix(gt: np.ndarray, pred: np.ndarray) -> np.ndarray:
    """IoU vetorizado entre caixas [x, y, w, h]. Retorna matriz (len(gt), len(pred))."""
    if len(gt) == 0 or len(pred) == 0:
        return np.zeros((len(gt), len(pred)))
    g = gt[:, None, :]
    p = pred[None, :, :]
    x1 = np.maximum(g[..., 0], p[..., 0])
    y1 = np.maximum(g[..., 1], p[..., 1])
    x2 = np.minimum(g[..., 0] + g[..., 2], p[..., 0] + p[..., 2])
    y2 = np.minimum(g[..., 1] + g[..., 3], p[..., 1] + p[..., 3])
    inter = np.clip(x2 - x1, 0, None) * np.clip(y2 - y1, 0, None)
    union = g[..., 2] * g[..., 3] + p[..., 2] * p[..., 3] - inter
    return inter / np.maximum(union, 1e-9)


def match(gt: np.ndarray, pred: np.ndarray, thr: float) -> tuple[int, int, int]:
    """Matching guloso por maior IoU. Retorna (TP, FP, FN)."""
    ious = iou_matrix(gt, pred)
    tp = 0
    used_g, used_p = set(), set()
    for gi, pi in zip(*np.unravel_index(np.argsort(-ious, axis=None), ious.shape)):
        if ious[gi, pi] < thr:
            break
        if gi in used_g or pi in used_p:
            continue
        used_g.add(gi); used_p.add(pi); tp += 1
    return tp, len(pred) - tp, len(gt) - tp


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", type=Path, required=True)
    ap.add_argument("--images", type=Path, required=True)
    ap.add_argument("--cascade", type=Path, default=Path("models/cascade.xml"))
    ap.add_argument("--iou", type=float, default=0.5)
    ap.add_argument("--min-neighbors", type=int, default=5)
    ap.add_argument("--scale-factor", type=float, default=1.1)
    args = ap.parse_args()

    detector = HaarCascadeDetector(
        args.cascade, HaarParams(scale_factor=args.scale_factor, min_neighbors=args.min_neighbors)
    )
    ann = pd.read_csv(args.csv)

    rows = []
    for img_path in sorted(p for p in args.images.iterdir() if p.is_file()):
        gt = ann.loc[ann["filename"] == img_path.name, ["x", "y", "width", "height"]].to_numpy(float)
        out = detector.detect(img_path.read_bytes())
        pred = np.array([[b.x, b.y, b.width, b.height] for b in out.boxes], dtype=float).reshape(-1, 4)
        tp, fp, fn = match(gt, pred, args.iou)
        rows.append({"image": img_path.name, "gt": len(gt), "pred": len(pred), "tp": tp, "fp": fp, "fn": fn})

    df = pd.DataFrame(rows)
    tp, fp, fn = df[["tp", "fp", "fn"]].sum()
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    f1 = 2 * precision * recall / max(precision + recall, 1e-9)

    print(df.to_string(index=False))
    print(f"\nIoU>={args.iou}  |  Precision={precision:.3f}  Recall={recall:.3f}  F1={f1:.3f}")
    df.to_csv("evaluation_report.csv", index=False)
    print("Relatório salvo em evaluation_report.csv")


if __name__ == "__main__":
    main()
