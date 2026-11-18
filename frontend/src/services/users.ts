import { apiClient, setToken } from "./api-client";
import type { CurrentUser, UserRole } from "./auth";

export type User = CurrentUser;

/** Matches the API's rule (bcrypt uses at most 72 bytes). */
export const MIN_PASSWORD_LENGTH = 8;

/** Strong-password rules, the same as backend/app/schemas/auth.py. */
export const PASSWORD_RULES: {
  label: string;
  test: (pw: string) => boolean;
}[] = [
  {
    label: `At least ${MIN_PASSWORD_LENGTH} characters`,
    test: (pw) => pw.length >= MIN_PASSWORD_LENGTH,
  },
  { label: "An uppercase letter (A-Z)", test: (pw) => /[A-Z]/.test(pw) },
  { label: "A lowercase letter (a-z)", test: (pw) => /[a-z]/.test(pw) },
  { label: "A number (0-9)", test: (pw) => /[0-9]/.test(pw) },
  {
    label: "A special character (e.g. ! @ # $)",
    test: (pw) => /[^A-Za-z0-9]/.test(pw),
  },
];

export const isStrongPassword = (pw: string) =>
  PASSWORD_RULES.every((rule) => rule.test(pw));

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
  requests: () => apiClient.get<AccountRequestCounts>("/users/requests"),
  approve: (id: number, role: UserRole) =>
    apiClient.post<User>(`/users/${id}/approve`, { role }),
  dismissReset: (id: number) =>
    apiClient.post<User>(`/users/${id}/dismiss-reset`),
};

export interface AccountRequestCounts {
  signups: number;
  password_resets: number;
}

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
