"use client";

import type { BoundingBox } from "@/lib/types";
import styles from "./ImpurityInspector.module.css";

interface Props {
  src: string;
  alt: string;
  naturalWidth: number;
  naturalHeight: number;
  boxes: BoundingBox[];
  visible: boolean;
  highlighted: number | null;
  onHover: (index: number | null) => void;
}

/**
 * Renderiza a imagem com as bounding boxes sobrepostas.
 *
 * As coordenadas vêm em pixels da imagem ORIGINAL; convertê-las em
 * porcentagem torna o overlay responsivo a qualquer tamanho de tela,
 * sem precisar medir o elemento <img> com JavaScript.
 */
export function BoundingBoxOverlay({
  src, alt, naturalWidth, naturalHeight, boxes, visible, highlighted, onHover,
}: Props) {
  return (
    <div className={styles.stage}>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={src} alt={alt} className={styles.stageImage} />
      {visible &&
        boxes.map((b, i) => (
          <div
            key={i}
            className={`${styles.box} ${highlighted === i ? styles.boxActive : ""}`}
            style={{
              left: `${(b.x / naturalWidth) * 100}%`,
              top: `${(b.y / naturalHeight) * 100}%`,
              width: `${(b.width / naturalWidth) * 100}%`,
              height: `${(b.height / naturalHeight) * 100}%`,
            }}
            onMouseEnter={() => onHover(i)}
            onMouseLeave={() => onHover(null)}
            title={`Impureza #${i + 1} — ${b.width}×${b.height}px`}
          >
            <span className={styles.boxLabel}>#{i + 1}</span>
          </div>
        ))}
    </div>
  );
}
