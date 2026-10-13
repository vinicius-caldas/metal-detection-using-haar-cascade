"use client";

import { ChangeEvent, DragEvent, FormEvent, useCallback, useEffect, useState } from "react";

import { api, mediaUrl } from "@/lib/api";
import type { Health, Inspection, InspectionSummary, MetalQuality } from "@/lib/types";
import { BoundingBoxOverlay } from "./BoundingBoxOverlay";
import styles from "./ImpurityInspector.module.css";

const QUALITY_LABEL: Record<MetalQuality, string> = {
  PREMIUM: "Premium",
  STANDARD: "Padrão",
  LOW: "Baixa",
  REJECTED: "Rejeitado",
};

const ACCEPT = "image/jpeg,image/png,image/bmp,image/tiff";

function QualityBadge({ quality }: { quality: MetalQuality }) {
  return <span className={`${styles.badge} ${styles[`q${quality}`]}`}>{QUALITY_LABEL[quality]}</span>;
}

const pct = (ratio: number) => `${(ratio * 100).toFixed(3)}%`;
const fmtDate = (iso: string) => new Date(iso).toLocaleString("pt-BR");

export default function ImpurityInspector() {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [result, setResult] = useState<Inspection | null>(null);
  const [history, setHistory] = useState<InspectionSummary[]>([]);
  const [health, setHealth] = useState<Health | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showBoxes, setShowBoxes] = useState(true);
  const [highlighted, setHighlighted] = useState<number | null>(null);
  const [dragOver, setDragOver] = useState(false);

  const refreshHistory = useCallback(() => {
    api.listInspections(8).then(setHistory).catch(() => undefined);
  }, []);

  useEffect(() => {
    api.health().then(setHealth).catch((e: Error) => setError(e.message));
    refreshHistory();
  }, [refreshHistory]);

  // Libera a object URL do preview anterior (evita vazamento de memória)
  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview); }, [preview]);

  const selectFile = (f: File | undefined | null) => {
    if (!f) return;
    setFile(f);
    setPreview(URL.createObjectURL(f));
    setResult(null);
    setError(null);
  };

  const onInputChange = (e: ChangeEvent<HTMLInputElement>) => selectFile(e.target.files?.[0]);

  const onDrop = (e: DragEvent<HTMLLabelElement>) => {
    e.preventDefault();
    setDragOver(false);
    selectFile(e.dataTransfer.files?.[0]);
  };

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!file) return;
    setLoading(true);
    setError(null);
    try {
      const inspection = await api.createInspection(file);
      setResult(inspection);
      refreshHistory();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const openFromHistory = async (id: string) => {
    setError(null);
    try {
      const inspection = await api.getInspection(id);
      setResult(inspection);
      setFile(null);
      setPreview(null);
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const imageSrc = result ? mediaUrl(result.original_image_url) : preview;

  return (
    <div className={styles.layout}>
      {/* ------------------------------------------------ coluna principal */}
      <section className={styles.main}>
        {health && !health.detector_ready && (
          <div className={styles.warning}>
            <strong>Modelo indisponível:</strong> {health.detector_error}
          </div>
        )}

        <form onSubmit={onSubmit} className={styles.card}>
          <label
            className={`${styles.dropzone} ${dragOver ? styles.dropzoneActive : ""}`}
            onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
            onDragLeave={() => setDragOver(false)}
            onDrop={onDrop}
          >
            <input type="file" accept={ACCEPT} onChange={onInputChange} hidden />
            <span className={styles.dropzoneTitle}>
              {file ? file.name : "Arraste a imagem da amostra ou clique para selecionar"}
            </span>
            <span className={styles.muted}>JPEG, PNG, BMP ou TIFF</span>
          </label>

          <button type="submit" className={styles.button} disabled={!file || loading || health?.detector_ready === false}>
            {loading ? "Analisando…" : "Detectar impurezas"}
          </button>
        </form>

        {error && <div className={styles.error}>{error}</div>}

        {imageSrc && (
          <div className={styles.card}>
            <div className={styles.toolbar}>
              <h2 className={styles.h2}>{result ? result.original_filename : "Pré-visualização"}</h2>
              {result && (
                <label className={styles.toggle}>
                  <input type="checkbox" checked={showBoxes} onChange={(e) => setShowBoxes(e.target.checked)} />
                  Exibir bounding boxes
                </label>
              )}
            </div>

            {result ? (
              <BoundingBoxOverlay
                src={imageSrc}
                alt="Amostra analisada"
                naturalWidth={result.image.width}
                naturalHeight={result.image.height}
                boxes={result.impurities}
                visible={showBoxes}
                highlighted={highlighted}
                onHover={setHighlighted}
              />
            ) : (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={imageSrc} alt="Pré-visualização" className={styles.stageImage} />
            )}
          </div>
        )}
      </section>

      {/* ------------------------------------------------ coluna lateral */}
      <aside className={styles.side}>
        {result && (
          <div className={styles.card}>
            <h2 className={styles.h2}>Resultado</h2>
            <dl className={styles.metrics}>
              <dt>Qualidade</dt><dd><QualityBadge quality={result.quality} /></dd>
              <dt>Impurezas</dt><dd>{result.impurity_count}</dd>
              <dt>Área contaminada</dt><dd>{pct(result.impurity_area_ratio)}</dd>
              <dt>Resolução</dt><dd>{result.image.width}×{result.image.height}px</dd>
              <dt>Processamento</dt><dd>{result.processing_time_ms.toFixed(1)} ms</dd>
              <dt>Data</dt><dd>{fmtDate(result.created_at)}</dd>
            </dl>
            <a href={mediaUrl(result.annotated_image_url)} target="_blank" rel="noreferrer" className={styles.link}>
              Abrir imagem anotada (OpenCV) ↗
            </a>

            {result.impurities.length > 0 && (
              <table className={styles.table}>
                <thead>
                  <tr><th>#</th><th>x</th><th>y</th><th>L×A</th><th>score</th></tr>
                </thead>
                <tbody>
                  {result.impurities.map((b, i) => (
                    <tr
                      key={i}
                      className={highlighted === i ? styles.rowActive : ""}
                      onMouseEnter={() => setHighlighted(i)}
                      onMouseLeave={() => setHighlighted(null)}
                    >
                      <td>{i + 1}</td><td>{b.x}</td><td>{b.y}</td>
                      <td>{b.width}×{b.height}</td><td>{b.score?.toFixed(2) ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}

        <div className={styles.card}>
          <h2 className={styles.h2}>Histórico</h2>
          {history.length === 0 ? (
            <p className={styles.muted}>Nenhuma inspeção registrada.</p>
          ) : (
            <ul className={styles.history}>
              {history.map((h) => (
                <li key={h.id}>
                  <button type="button" onClick={() => openFromHistory(h.id)} className={styles.historyItem}>
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img src={mediaUrl(h.annotated_image_url)} alt="" className={styles.thumb} />
                    <span className={styles.historyText}>
                      <span className={styles.historyName}>{h.original_filename}</span>
                      <span className={styles.muted}>{h.impurity_count} impurezas · {fmtDate(h.created_at)}</span>
                    </span>
                    <QualityBadge quality={h.quality} />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </aside>
    </div>
  );
}
