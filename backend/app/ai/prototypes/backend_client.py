"""Phase 3 step 3: shared HTTP client so Phase 1 AI scripts can read
camera_settings and write real alerts through the running FastAPI backend,
instead of only CLI flags and console prints.

Goes through the real REST API (not a direct DB connection) so camera_id
validation, priority validation, and the WebSocket broadcast on new alerts
all happen exactly as they do for any other API client.

Credentials: pass --api-username/--api-password, or set the
UNIVERSE_API_USERNAME / UNIVERSE_API_PASSWORD env vars. No default
credentials are hardcoded here.
"""
import os

import requests


class BackendClient:
    def __init__(self, base_url: str, username: str, password: str, timeout: float = 5.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._token = self._login(username, password)

    def _login(self, username: str, password: str) -> str:
        resp = requests.post(
            f"{self.base_url}/auth/login",
            data={"username": username, "password": password},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()["access_token"]

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._token}"}

    def get_camera_settings(self, camera_id: int) -> dict:
        resp = requests.get(
            f"{self.base_url}/cameras/{camera_id}/settings",
            headers=self._headers(), timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()

    def post_alert(
        self, camera_id: int, alert_type: str, priority: str, message: str,
        extra_data: dict | None = None,
    ) -> dict:
        resp = requests.post(
            f"{self.base_url}/alerts",
            headers=self._headers(),
            json={
                "camera_id": camera_id,
                "alert_type": alert_type,
                "priority": priority,
                "message": message,
                "extra_data": extra_data,
            },
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()


def add_backend_args(parser) -> None:
    parser.add_argument("--camera-id", type=int, default=None,
                         help="If set, read thresholds from camera_settings and write real alerts to the backend")
    parser.add_argument("--api-base", default="http://localhost:8000", help="Backend base URL")
    parser.add_argument("--api-username", default=os.getenv("UNIVERSE_API_USERNAME"))
    parser.add_argument("--api-password", default=os.getenv("UNIVERSE_API_PASSWORD"))


def build_client(args) -> "BackendClient | None":
    if args.camera_id is None:
        return None
    if not args.api_username or not args.api_password:
        raise SystemExit(
            "--camera-id given but no credentials: pass --api-username/--api-password "
            "or set UNIVERSE_API_USERNAME / UNIVERSE_API_PASSWORD"
        )
    return BackendClient(args.api_base, args.api_username, args.api_password)
