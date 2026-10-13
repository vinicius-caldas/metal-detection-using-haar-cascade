import type { Health, Inspection, InspectionSummary } from "./types";

export const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

/** Converte caminho relativo (/media/...) em URL absoluta do backend. */
export const mediaUrl = (path: string) => `${API_URL}${path}`;

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}/api/v1${path}`, { cache: "no-store", ...init });
  } catch {
    throw new Error("Não foi possível conectar à API. O backend está em execução?");
  }
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    const detail = typeof body?.detail === "string" ? body.detail : `Erro HTTP ${res.status}`;
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => request<Health>("/health"),

  createInspection: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<Inspection>("/inspections", { method: "POST", body: form });
  },

  listInspections: (limit = 10) => request<InspectionSummary[]>(`/inspections?limit=${limit}`),

  getInspection: (id: string) => request<Inspection>(`/inspections/${id}`),
};
