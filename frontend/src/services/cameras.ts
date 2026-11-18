import { apiClient } from "./api-client";

export type CameraStatus = "online" | "offline" | "unknown";

export interface Camera {
  id: number;
  name: string;
  location: string | null;
  stream_source: string;
  status: CameraStatus;
  last_seen_at: string | null;
  created_at: string;
}

export interface CameraCreateInput {
  name: string;
  location?: string;
  stream_source: string;
}

export interface CameraUpdateInput {
  name?: string;
  location?: string | null;
  /** Omit to keep the saved source (responses show its password masked). */
  stream_source?: string;
}

export const camerasApi = {
  update: (id: number, input: CameraUpdateInput) =>
    apiClient.put<Camera>(`/cameras/${id}`, input),
  list: () => apiClient.get<Camera[]>("/cameras"),
  get: (id: number) => apiClient.get<Camera>(`/cameras/${id}`),
  create: (input: CameraCreateInput) =>
    apiClient.post<Camera>("/cameras", input),
  updateStatus: (id: number, status: CameraStatus) =>
    apiClient.put<Camera>(`/cameras/${id}`, { status }),
  remove: (id: number) => apiClient.delete<void>(`/cameras/${id}`),
};
