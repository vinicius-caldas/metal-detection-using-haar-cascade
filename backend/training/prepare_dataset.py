"""Prepara o dataset para o `opencv_traincascade` a partir de um CSV anotado.

Entrada:
    data/annotations.csv  -> colunas: filename,x,y,width,height  (1 linha por impureza)
    data/positives/       -> imagens com impurezas
    data/negatives/       -> imagens de metal limpo (sem impurezas)

Saída:
    data/positives.dat    -> formato "<caminho> <n> x y w h [x y w h ...]"
    data/bg.txt           -> lista de imagens negativas
    + relatório estatístico (Pandas) e sugestão de -w/-h para o treino.

Uso:
    python prepare_dataset.py --data-dir data
"""

from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np
import pandas as pd

IMG_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}


def load_annotations(csv_path: Path, positives_dir: Path, min_side: int) -> pd.DataFrame:
    df = pd.read_csv(csv_path, dtype={"filename": str})
    required = {"filename", "x", "y", "width", "height"}
    if missing := required - set(df.columns):
        raise SystemExit(f"CSV sem colunas obrigatórias: {missing}")

    # Dimensões reais de cada imagem (lidas uma vez por arquivo)
    sizes = {}
    for name in df["filename"].unique():
        img = cv2.imread(str(positives_dir / name), cv2.IMREAD_GRAYSCALE)
        sizes[name] = img.shape[::-1] if img is not None else (np.nan, np.nan)
    df["img_w"] = df["filename"].map(lambda n: sizes[n][0])
    df["img_h"] = df["filename"].map(lambda n: sizes[n][1])

    before = len(df)
    valid = (
        df["img_w"].notna()
        & (df["x"] >= 0) & (df["y"] >= 0)
        & (df["x"] + df["width"] <= df["img_w"])
        & (df["y"] + df["height"] <= df["img_h"])
        & (df[["width", "height"]].min(axis=1) >= min_side)
    )
    df = df[valid].copy()
    print(f"Anotações válidas: {len(df)}/{before} (descartadas {before - len(df)})")
    return df


def write_positives(df: pd.DataFrame, positives_dir: Path, out: Path) -> None:
    lines = []
    for name, group in df.groupby("filename"):
        coords = " ".join(
            f"{r.x} {r.y} {r.width} {r.height}" for r in group.itertuples(index=False)
        )
        rel = (positives_dir / name).relative_to(out.parent).as_posix()
        lines.append(f"{rel} {len(group)} {coords}")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{out.name}: {len(lines)} imagens / {len(df)} amostras positivas")


def write_negatives(negatives_dir: Path, out: Path) -> int:
    files = sorted(p for p in negatives_dir.rglob("*") if p.suffix.lower() in IMG_EXT)
    out.write_text(
        "\n".join(p.relative_to(out.parent).as_posix() for p in files) + "\n", encoding="utf-8"
    )
    print(f"{out.name}: {len(files)} imagens negativas")
    return len(files)


def report(df: pd.DataFrame, target_w: int) -> None:
    df = df.assign(aspect=df["width"] / df["height"], area=df["width"] * df["height"])
    print("\nEstatísticas das impurezas anotadas:")
    print(df[["width", "height", "aspect", "area"]].describe().round(2).to_string())
    aspect = float(df["aspect"].median())
    h = max(8, round(target_w / aspect))
    print(f"\nSugestão de janela de treino: -w {target_w} -h {h} (aspect mediano {aspect:.2f})")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", type=Path, default=Path(__file__).parent / "data")
    ap.add_argument("--min-side", type=int, default=6)
    ap.add_argument("--window", type=int, default=24, help="largura alvo da janela de treino")
    args = ap.parse_args()

    data = args.data_dir.resolve()
    df = load_annotations(data / "annotations.csv", data / "positives", args.min_side)
    if df.empty:
        raise SystemExit("Nenhuma anotação válida.")
    write_positives(df, data / "positives", data / "positives.dat")
    write_negatives(data / "negatives", data / "bg.txt")
    report(df, args.window)
    print(f"\nTotal de amostras para -numPos: use ~85% de {len(df)} = {int(len(df) * 0.85)}")


if __name__ == "__main__":
    main()
