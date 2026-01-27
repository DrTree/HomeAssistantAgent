import json
import logging
import os
from dataclasses import dataclass
from typing import Any
from urllib import request
from urllib.error import HTTPError, URLError

DEFAULT_BASE_URL = os.environ.get("HOME_ASSISTANT_URL", "http://supervisor/core")
DEFAULT_TOKEN = os.environ.get("SUPERVISOR_TOKEN") or os.environ.get("HOME_ASSISTANT_TOKEN")
logger = logging.getLogger(__name__)


@dataclass
class HomeAssistantApiClient:
    base_url: str = DEFAULT_BASE_URL
    token: str | None = DEFAULT_TOKEN
    timeout: float = 10.0

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
        if not self.token:
            raise RuntimeError("Home Assistant API token is not configured.")

        url = f"{self.base_url.rstrip('/')}{path}"
        token_prefix = self.token[:4]
        logger.info(
            "Home Assistant API request url=%s token_prefix=%s",
            url,
            token_prefix,
        )
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
                    content_type = response.headers.get_content_type()
                    if content_type == "application/json" or body.lstrip().startswith(("{", "[")):
                        try:
                            return json.loads(body)
                        except json.JSONDecodeError:
                            logger.warning("Failed to decode JSON response, returning raw body.")
                            return body
                    return body
                return None
        except HTTPError as exc:
            detail = exc.read().decode("utf-8") if exc.fp else str(exc)
            raise RuntimeError(f"Home Assistant API error {exc.code}: {detail}") from exc
        except URLError as exc:
            raise RuntimeError(f"Home Assistant API connection error: {exc.reason}") from exc

    def render_template(
        self, template: str, variables: dict[str, Any] | None = None
    ) -> str | dict[str, Any] | None:
        payload = {"template": template}
        if variables:
            payload["variables"] = variables
        response = self._request("POST", "/api/template", payload)
        return response

    def call_service(
        self,
        domain: str,
        service: str,
        service_data: dict[str, Any] | None = None,
        return_response: bool = False,
    ) -> Any:
        payload = service_data or {}
        query = "?return_response" if return_response else ""
        path = f"/api/services/{domain}/{service}{query}"
        return self._request("POST", path, payload)
