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
  /** Operator verdict; null = not reviewed yet. */
  review_status: ReviewStatus | null;
  reviewed_by: number | null;
  reviewed_at: string | null;
}

export type ReviewStatus = "confirmed" | "false_alarm";

export interface ReviewCounts {
  total: number;
  confirmed: number;
  false_alarm: number;
  unreviewed: number;
  /** confirmed / reviewed; null until something is reviewed. */
  precision: number | null;
  false_alarm_rate: number | null;
}

export interface ReviewStats {
  overall: ReviewCounts;
  by_type: (ReviewCounts & { alert_type: string })[];
}

/** Readable names for alert types (the API sends the codes). */
export const ALERT_TYPE_LABELS: Record<string, string> = {
  ROI_ENTRY: "Restricted area entry",
  LOITERING: "Loitering",
  CROWD: "Crowd",
  RUNNING: "Running",
  FALL_DETECTED: "Possible fall",
  ABANDONED_OBJECT: "Unattended object",
  UNKNOWN_FACE: "Unknown face",
  TAMPER_COVERED: "Camera covered",
  TAMPER_MOVED: "Camera moved",
  TAMPER_DEFOCUSED: "Camera out of focus",
  CAMERA_OFFLINE: "Camera offline",
  CAMERA_ONLINE: "Camera back online",
};

export const alertTypeLabel = (type: string) => ALERT_TYPE_LABELS[type] ?? type;

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
  review: (id: number, reviewStatus: ReviewStatus | null) =>
    apiClient.patch<Alert>(`/alerts/${id}/review`, {
      review_status: reviewStatus,
    }),
  reviewStats: () => apiClient.get<ReviewStats>("/alerts/review-stats"),
};
