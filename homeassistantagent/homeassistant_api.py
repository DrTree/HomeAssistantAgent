import json
import os
from dataclasses import dataclass
from typing import Any
from urllib import request
from urllib.error import HTTPError, URLError

DEFAULT_BASE_URL = os.environ.get("HOME_ASSISTANT_URL", "http://supervisor/core")
DEFAULT_TOKEN = os.environ.get("SUPERVISOR_TOKEN") or os.environ.get("HOME_ASSISTANT_TOKEN")


@dataclass
class HomeAssistantApiClient:
    base_url: str = DEFAULT_BASE_URL
    token: str | None = DEFAULT_TOKEN
    timeout: float = 10.0

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
        if not self.token:
            raise RuntimeError("Home Assistant API token is not configured.")

        url = f"{self.base_url.rstrip('/')}{path}"
        data = json.dumps(payload or {}).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        req = request.Request(url, data=data, headers=headers, method=method)
        try:
            with request.urlopen(req, timeout=self.timeout) as response:
                body = response.read().decode("utf-8")
                if body:
                    return json.loads(body)
                return None
        except HTTPError as exc:
            detail = exc.read().decode("utf-8") if exc.fp else str(exc)
            raise RuntimeError(f"Home Assistant API error {exc.code}: {detail}") from exc
        except URLError as exc:
            raise RuntimeError(f"Home Assistant API connection error: {exc.reason}") from exc

    def render_template(self, template: str, variables: dict[str, Any] | None = None) -> str:
        payload = {"template": template}
        if variables:
            payload["variables"] = variables
        response = self._request("POST", "/api/template", payload)
        if isinstance(response, str):
            return response
        raise RuntimeError("Unexpected response from Home Assistant template API.")
