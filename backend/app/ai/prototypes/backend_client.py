"""Shared HTTP client so the AI scripts can read camera_settings, report
camera status, and write real alerts through the running FastAPI backend,
instead of only CLI flags and console prints.

Goes through the real REST API (not a direct DB connection) so camera_id
validation, priority validation, and the WebSocket broadcast on new alerts
all happen exactly as they do for any other API client.

Credentials: pass --api-username/--api-password, or set the
UNIVERSE_API_USERNAME / UNIVERSE_API_PASSWORD env vars. No default
credentials are hardcoded here.
"""

import argparse
import logging
import os
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("universe.backend_client")


class BackendClient:
    def __init__(self, base_url: str, username: str, password: str, timeout: float = 5.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._username = username
        self._password = password
        self._token = self._login()

    def _login(self) -> str:
        resp = requests.post(
            f"{self.base_url}/auth/login",
            data={"username": self._username, "password": self._password},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()["access_token"]

    def _request(self, method: str, path: str, **kwargs: Any) -> dict:
        """Authenticated request. JWTs expire (8h), and these scripts are meant
        to run unattended for longer than that, so a 401 triggers one re-login
        and retry instead of failing every call from then on.
        """
        url = f"{self.base_url}{path}"
        resp = requests.request(method, url, headers=self._headers(), timeout=self.timeout, **kwargs)
        if resp.status_code == 401:
            self._token = self._login()
            resp = requests.request(method, url, headers=self._headers(), timeout=self.timeout, **kwargs)
        resp.raise_for_status()
        return resp.json()

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._token}"}

    def get_camera_settings(self, camera_id: int) -> dict:
        # Called once at startup; let failures propagate so a misconfigured
        # camera_id or backend URL stops the script immediately.
        return self._request("GET", f"/cameras/{camera_id}/settings")

    def heartbeat(self, camera_id: int, status: str) -> dict | None:
        try:
            return self._request("POST", f"/cameras/{camera_id}/heartbeat", json={"status": status})
        except requests.RequestException as exc:
            logger.warning("heartbeat for camera %s failed: %s", camera_id, exc)
            return None

    def post_alert(
        self,
        camera_id: int,
        alert_type: str,
        priority: str,
        message: str,
        extra_data: dict | None = None,
    ) -> dict | None:
        # Mid-loop call: a backend restart or network blip must not kill the
        # detection loop, so log and carry on (the console print still records it).
        try:
            return self._request(
                "POST",
                "/alerts",
                json={
                    "camera_id": camera_id,
                    "alert_type": alert_type,
                    "priority": priority,
                    "message": message,
                    "extra_data": extra_data,
                },
            )
        except requests.RequestException as exc:
            logger.warning("posting %s alert for camera %s failed: %s", alert_type, camera_id, exc)
            return None


def add_backend_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--camera-id",
        type=int,
        default=None,
        help="If set, read thresholds from camera_settings and write real alerts to the backend",
    )
    # 127.0.0.1, not localhost: on this Windows setup "localhost" resolves to
    # ::1 first, which times out (~2s) before falling back to IPv4.
    parser.add_argument(
        "--api-base", default=os.getenv("UNIVERSE_API_BASE", "http://127.0.0.1:8000"), help="Backend base URL"
    )
    parser.add_argument("--api-username", default=os.getenv("UNIVERSE_API_USERNAME"))
    parser.add_argument("--api-password", default=os.getenv("UNIVERSE_API_PASSWORD"))


def build_client(args: argparse.Namespace) -> BackendClient | None:
    if args.camera_id is None:
        return None
    if not args.api_username or not args.api_password:
        raise SystemExit(
            "--camera-id given but no credentials: pass --api-username/--api-password "
            "or set UNIVERSE_API_USERNAME / UNIVERSE_API_PASSWORD"
        )
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    return BackendClient(args.api_base, args.api_username, args.api_password)
