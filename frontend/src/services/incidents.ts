import type { AlertImage } from "./alerts";
import { apiClient } from "./api-client";

export type IncidentStatus = "open" | "acknowledged" | "resolved";

export interface Incident {
  id: number;
  camera_id: number;
  title: string;
  description: string | null;
  status: IncidentStatus;
  priority: "low" | "medium" | "high";
  acknowledged_by: number | null;
  acknowledged_at: string | null;
  resolved_by: number | null;
  resolved_at: string | null;
  created_at: string;
  updated_at: string;
  /** Evidence of the alert(s) this incident was promoted from. */
  images: AlertImage[];
}

export interface IncidentCreateInput {
  camera_id: number;
  title: string;
  description?: string;
  priority?: string;
  source_alert_id?: number;
}

export const incidentsApi = {
  list: (status?: IncidentStatus) =>
    apiClient.get<Incident[]>(`/incidents${status ? `?status=${status}` : ""}`),
  get: (id: number) => apiClient.get<Incident>(`/incidents/${id}`),
  create: (input: IncidentCreateInput) =>
    apiClient.post<Incident>("/incidents", input),
  acknowledge: (id: number) =>
    apiClient.patch<Incident>(`/incidents/${id}/acknowledge`),
  resolve: (id: number) =>
    apiClient.patch<Incident>(`/incidents/${id}/resolve`),
};
