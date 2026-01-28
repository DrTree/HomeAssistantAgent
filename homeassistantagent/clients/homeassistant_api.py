import base64
import json
import logging
import os
from dataclasses import dataclass
from typing import Any
from urllib import parse, request
from urllib.error import HTTPError, URLError

DEFAULT_BASE_URL = os.environ.get("HOME_ASSISTANT_URL", "http://supervisor/core")
DEFAULT_TOKEN = os.environ.get("SUPERVISOR_TOKEN") or os.environ.get("HOME_ASSISTANT_TOKEN")
logger = logging.getLogger(__name__)


@dataclass
class HomeAssistantApiClient:
    base_url: str = DEFAULT_BASE_URL
    token: str | None = DEFAULT_TOKEN
    timeout: float = 10.0

    def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        query: dict[str, Any] | None = None,
    ) -> Any:
        if not self.token:
            raise RuntimeError("Home Assistant API token is not configured.")

        url = f"{self.base_url.rstrip('/')}{path}"
        if query:
            url = f"{url}?{parse.urlencode(query, doseq=True)}"
        token_prefix = self.token[:4]
        logger.info(
            "Home Assistant API request url=%s token_prefix=%s",
            url,
            token_prefix,
        )
        data = None
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
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

    def _request_binary(
        self,
        method: str,
        path: str,
        query: dict[str, Any] | None = None,
    ) -> dict[str, str]:
        if not self.token:
            raise RuntimeError("Home Assistant API token is not configured.")

        url = f"{self.base_url.rstrip('/')}{path}"
        if query:
            url = f"{url}?{parse.urlencode(query, doseq=True)}"
        headers = {
            "Authorization": f"Bearer {self.token}",
        }
        req = request.Request(url, headers=headers, method=method)
        try:
            with request.urlopen(req, timeout=self.timeout) as response:
                content_type = response.headers.get("Content-Type", "application/octet-stream")
                data = response.read()
                return {
                    "content_type": content_type,
                    "base64": base64.b64encode(data).decode("utf-8"),
                }
        except HTTPError as exc:
            detail = exc.read().decode("utf-8") if exc.fp else str(exc)
            raise RuntimeError(f"Home Assistant API error {exc.code}: {detail}") from exc
        except URLError as exc:
            raise RuntimeError(f"Home Assistant API connection error: {exc.reason}") from exc

    def render_template(
        self, template: str, variables: dict[str, Any] | None = None
    ) -> str | dict[str, Any] | None:
        payload: dict[str, Any] = {"template": template}
        if variables:
            payload["variables"] = variables
        response = self._request("POST", "/api/template", payload=payload)
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
        return self._request("POST", path, payload=payload)

    def get_config(self) -> Any:
        return self._request("GET", "/api/config")

    def list_components(self) -> Any:
        return self._request("GET", "/api/components")

    def list_states(self) -> Any:
        return self._request("GET", "/api/states")

    def get_state(self, entity_id: str) -> Any:
        return self._request("GET", f"/api/states/{entity_id}")

    def list_services(self) -> Any:
        return self._request("GET", "/api/services")

    def list_events(self) -> Any:
        return self._request("GET", "/api/events")

    def history_period(
        self,
        start_time: str,
        entity_ids: list[str],
        end_time: str | None = None,
        minimal_response: bool = True,
        no_attributes: bool = True,
        significant_changes_only: bool = True,
    ) -> Any:
        query: dict[str, Any] = {
            "filter_entity_id": entity_ids,
            "minimal_response": str(minimal_response).lower(),
            "no_attributes": str(no_attributes).lower(),
            "significant_changes_only": str(significant_changes_only).lower(),
        }
        if end_time:
            query["end_time"] = end_time
        return self._request("GET", f"/api/history/period/{start_time}", query=query)

    def logbook(
        self,
        start_time: str,
        end_time: str | None = None,
        entity_ids: list[str] | None = None,
    ) -> Any:
        query: dict[str, Any] = {}
        if end_time:
            query["end_time"] = end_time
        if entity_ids:
            query["entity"] = entity_ids
        return self._request("GET", f"/api/logbook/{start_time}", query=query)

    def error_log(self) -> Any:
        return self._request("GET", "/api/error_log")

    def check_config(self) -> Any:
        return self._request("POST", "/api/config/core/check_config")

    def list_calendars(self) -> Any:
        return self._request("GET", "/api/calendars")

    def get_calendar_events(self, calendar_entity_id: str, start: str, end: str) -> Any:
        return self._request(
            "GET",
            f"/api/calendars/{calendar_entity_id}",
            query={"start": start, "end": end},
        )

    def camera_proxy(self, camera_entity_id: str) -> dict[str, str]:
        return self._request_binary("GET", f"/api/camera_proxy/{camera_entity_id}")

    def fire_event(self, event_type: str, event_data: dict[str, Any] | None = None) -> Any:
        return self._request("POST", f"/api/events/{event_type}", payload=event_data or {})

    def set_state(self, entity_id: str, state: str, attributes: dict[str, Any] | None = None) -> Any:
        payload: dict[str, Any] = {"state": state}
        if attributes is not None:
            payload["attributes"] = attributes
        return self._request("POST", f"/api/states/{entity_id}", payload=payload)

    def delete_state(self, entity_id: str) -> Any:
        return self._request("DELETE", f"/api/states/{entity_id}")

    def handle_intent(self, intent: str, slots: dict[str, Any] | None = None) -> Any:
        payload: dict[str, Any] = {"name": intent}
        if slots:
            payload["slots"] = slots
        return self._request("POST", "/api/intent/handle", payload=payload)
