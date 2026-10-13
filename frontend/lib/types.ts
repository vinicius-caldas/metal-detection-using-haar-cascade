export type MetalQuality = "PREMIUM" | "STANDARD" | "LOW" | "REJECTED";

export interface BoundingBox {
  x: number;
  y: number;
  width: number;
  height: number;
  score: number | null;
}

export interface InspectionSummary {
  id: string;
  original_filename: string;
  quality: MetalQuality;
  impurity_count: number;
  impurity_area_ratio: number;
  created_at: string;
  annotated_image_url: string;
}

export interface Inspection extends InspectionSummary {
  image: { width: number; height: number };
  processing_time_ms: number;
  original_image_url: string;
  impurities: BoundingBox[];
}

export interface Health {
  status: string;
  detector_ready: boolean;
  detector_error: string | null;
}
