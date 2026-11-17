import { apiClient } from "./api-client";

export interface Person {
  id: number;
  name: string;
  notes: string | null;
  is_active: boolean;
  created_at: string;
}

export interface PersonCreateInput {
  name: string;
  notes?: string;
}

export const peopleApi = {
  list: () => apiClient.get<Person[]>("/people"),
  create: (input: PersonCreateInput) => apiClient.post<Person>("/people", input),
  remove: (id: number) => apiClient.delete<void>(`/people/${id}`),
};
