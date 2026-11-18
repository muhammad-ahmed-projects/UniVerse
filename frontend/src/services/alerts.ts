import { apiClient } from "./api-client";

/** Evidence snapshot metadata; the JPEG itself is at alertImagePath(image). */
export interface AlertImage {
  id: number;
  alert_id: number;
  captured_at: string;
}

export interface Alert {
  id: number;
  camera_id: number;
  alert_type: string;
  priority: "low" | "medium" | "high";
  message: string;
  extra_data: Record<string, unknown> | null;
  incident_id: number | null;
  triggered_at: string;
  images: AlertImage[];
}

export const alertImagePath = (image: AlertImage) =>
  `/alerts/${image.alert_id}/images/${image.id}`;

export const alertsApi = {
  list: (params?: {
    camera_id?: number;
    unresolved_only?: boolean;
    limit?: number;
  }) => {
    const qs = new URLSearchParams();
    if (params?.camera_id !== undefined)
      qs.set("camera_id", String(params.camera_id));
    if (params?.unresolved_only) qs.set("unresolved_only", "true");
    if (params?.limit !== undefined) qs.set("limit", String(params.limit));
    const suffix = qs.toString() ? `?${qs}` : "";
    return apiClient.get<Alert[]>(`/alerts${suffix}`);
  },
  get: (id: number) => apiClient.get<Alert>(`/alerts/${id}`),
};
