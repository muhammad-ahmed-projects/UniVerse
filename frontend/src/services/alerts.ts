import { apiClient } from "./api-client";

export interface Alert {
  id: number;
  camera_id: number;
  alert_type: string;
  priority: "low" | "medium" | "high";
  message: string;
  evidence_path: string | null;
  extra_data: Record<string, unknown> | null;
  incident_id: number | null;
  triggered_at: string;
}

export const alertsApi = {
  list: (params?: { camera_id?: number; unresolved_only?: boolean }) => {
    const qs = new URLSearchParams();
    if (params?.camera_id !== undefined) qs.set("camera_id", String(params.camera_id));
    if (params?.unresolved_only) qs.set("unresolved_only", "true");
    const suffix = qs.toString() ? `?${qs}` : "";
    return apiClient.get<Alert[]>(`/alerts${suffix}`);
  },
  get: (id: number) => apiClient.get<Alert>(`/alerts/${id}`),
};
