import { apiClient } from "./api-client";

export interface Person {
  id: number;
  name: string;
  notes: string | null;
  is_active: boolean;
  created_at: string;
  /** Registered face photos; 0 means the recognizer can't identify them yet. */
  face_count: number;
  /** Latest face-recognition match (reported by face_recognition.py). */
  last_seen_at: string | null;
  last_seen_camera_id: number | null;
}

export interface PersonCreateInput {
  name: string;
  notes?: string;
}

/** A registered face photo (admin only). The embedding never leaves the server. */
export interface FaceSample {
  id: number;
  person_id: number;
  created_at: string;
}

export const faceImagePath = (face: FaceSample) =>
  `/people/${face.person_id}/faces/${face.id}/image`;

export const peopleApi = {
  list: () => apiClient.get<Person[]>("/people"),
  get: (id: number) => apiClient.get<Person>(`/people/${id}`),
  create: (input: PersonCreateInput) =>
    apiClient.post<Person>("/people", input),
  remove: (id: number) => apiClient.delete<void>(`/people/${id}`),
  listFaces: (personId: number) =>
    apiClient.get<FaceSample[]>(`/people/${personId}/faces`),
  addFace: (personId: number, photo: Blob, fileName: string) => {
    const form = new FormData();
    form.append("file", photo, fileName);
    return apiClient.postForm<FaceSample>(`/people/${personId}/faces`, form);
  },
  removeFace: (face: FaceSample) =>
    apiClient.delete<void>(`/people/${face.person_id}/faces/${face.id}`),
};
