import { API_BASE_URL, ApiError, apiClient, setToken } from "./api-client";

/** ai_service is the detection scripts' service account, not meant for dashboard use. */
export type UserRole = "admin" | "security_operator" | "ai_service";

export interface CurrentUser {
  id: number;
  username: string;
  email: string | null;
  role: UserRole;
  is_active: boolean;
  created_at: string;
}

export async function login(
  username: string,
  password: string,
): Promise<CurrentUser> {
  const res = await fetch(`${API_BASE_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({ username, password }),
  });

  if (!res.ok) {
    let detail = "Login failed";
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {
      // ignore
    }
    throw new ApiError(res.status, detail);
  }

  const { access_token } = await res.json();
  setToken(access_token);
  return apiClient.get<CurrentUser>("/auth/me");
}

export function logout(): void {
  setToken(null);
}

export function getCurrentUser(): Promise<CurrentUser> {
  return apiClient.get<CurrentUser>("/auth/me");
}
