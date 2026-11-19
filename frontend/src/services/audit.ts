import { apiClient } from "./api-client";

export interface AuditEntry {
  id: number;
  created_at: string;
  actor_id: number | null;
  actor_username: string | null;
  action: string;
  target_type: string | null;
  target_id: number | null;
  details: Record<string, unknown> | null;
  ip_address: string | null;
}

export interface AuditPage {
  total: number;
  items: AuditEntry[];
}

export const AUDIT_CATEGORIES: { value: string; label: string }[] = [
  { value: "auth", label: "Sign-in & passwords" },
  { value: "user", label: "Users" },
  { value: "camera", label: "Cameras & settings" },
  { value: "monitoring", label: "Monitoring" },
  { value: "person", label: "Registered people" },
  { value: "face", label: "Face data" },
  { value: "incident", label: "Incidents" },
  { value: "alert", label: "Alert reviews" },
];

/** Readable sentence for an action code. */
export const AUDIT_ACTION_LABELS: Record<string, string> = {
  "auth.login": "Signed in",
  "auth.login_failed": "Failed sign-in",
  "auth.signup_request": "Requested an account",
  "auth.password_reset_request": "Asked for a password reset",
  "auth.password_change": "Changed own password",
  "user.create": "Added a user",
  "user.update": "Edited a user",
  "user.approve": "Approved an account request",
  "user.reset_request_dismiss": "Dismissed a reset request",
  "user.password_reset": "Reset a user's password",
  "user.delete": "Deleted a user",
  "camera.create": "Added a camera",
  "camera.update": "Edited a camera",
  "camera.delete": "Deleted a camera",
  "camera.settings_update": "Changed detection settings",
  "monitoring.start": "Started monitoring",
  "monitoring.stop": "Stopped monitoring",
  "person.create": "Registered a person",
  "person.delete": "Removed a person",
  "face.add": "Added a face photo",
  "face.view": "Viewed a face photo",
  "face.delete": "Deleted a face photo",
  "incident.create": "Created an incident",
  "incident.acknowledge": "Acknowledged an incident",
  "incident.resolve": "Resolved an incident",
  "alert.review": "Reviewed an alert",
};

/** Admin only (the API returns 403 for anyone else). */
export const auditApi = {
  list: (params: {
    category?: string;
    q?: string;
    limit: number;
    offset: number;
  }) => {
    const qs = new URLSearchParams({
      limit: String(params.limit),
      offset: String(params.offset),
    });
    if (params.category) qs.set("category", params.category);
    if (params.q) qs.set("q", params.q);
    return apiClient.get<AuditPage>(`/audit-logs?${qs}`);
  },
};
