import { apiClient, setToken } from "./api-client";
import type { CurrentUser, UserRole } from "./auth";

export type User = CurrentUser;

/** Matches the API's rule (bcrypt uses at most 72 bytes). */
export const MIN_PASSWORD_LENGTH = 8;

export interface UserCreateInput {
  username: string;
  email?: string;
  password: string;
  role: UserRole;
}

export interface UserUpdateInput {
  email?: string | null;
  role?: UserRole;
  is_active?: boolean;
}

export const ROLE_LABELS: Record<UserRole, string> = {
  admin: "Admin",
  security_operator: "Security operator",
  ai_service: "Detection service",
};

export const ROLE_DESCRIPTIONS: Record<UserRole, string> = {
  admin: "Full access: cameras, people, settings, users.",
  security_operator: "Watches cameras and reviews alerts and incidents.",
  ai_service:
    "Account for the detection scripts (UNIVERSE_API_USERNAME), not for people.",
};

/** Admin-only user management (the API returns 403 for anyone else). */
export const usersApi = {
  list: () => apiClient.get<User[]>("/users"),
  create: (input: UserCreateInput) => apiClient.post<User>("/users", input),
  update: (id: number, input: UserUpdateInput) =>
    apiClient.patch<User>(`/users/${id}`, input),
  resetPassword: (id: number, newPassword: string) =>
    apiClient.post<void>(`/users/${id}/password`, {
      new_password: newPassword,
    }),
  remove: (id: number) => apiClient.delete<void>(`/users/${id}`),
};

/** Change your own password. The API logs out the account's other sessions
 * and returns a fresh token so this tab stays signed in. */
export async function changeOwnPassword(
  currentPassword: string,
  newPassword: string,
): Promise<void> {
  const { access_token } = await apiClient.post<{ access_token: string }>(
    "/auth/change-password",
    { current_password: currentPassword, new_password: newPassword },
  );
  setToken(access_token);
}
