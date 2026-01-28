import logging
from typing import Any

from clients import HomeAssistantWebSocketClient
from clients.homeassistant_ws_client import HomeAssistantWsError

logger = logging.getLogger(__name__)
ws_client = HomeAssistantWebSocketClient()


def _as_str_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return [value for value in values if isinstance(value, str)]


async def ha_ws_area_registry_list(*, max_items: int = 500) -> dict[str, Any]:
    """List Home Assistant area registry entries via the WebSocket API."""
    max_items = max(0, int(max_items))
    try:
        response = await ws_client.send_command(
            "config/area_registry/list",
            {},
            is_write=False,
            timeout_s=10,
        )
    except HomeAssistantWsError as exc:
        if exc.code == "HA_ERROR":
            error_payload = exc.details if isinstance(exc.details, dict) else {}
            return {
                "ok": False,
                "error": {
                    "code": "HA_WS_ERROR",
                    "message": error_payload.get("message", "Home Assistant error."),
                    "details": error_payload.get("code"),
                },
            }
        return {
            "ok": False,
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            },
        }
    except Exception as exc:
        logger.exception("WS area registry list failed.")
        return {
            "ok": False,
            "error": {
                "code": "UNKNOWN",
                "message": str(exc),
                "details": None,
            },
        }

    if not response.get("success", True):
        error_payload = response.get("error", {})
        return {
            "ok": False,
            "error": {
                "code": "HA_WS_ERROR",
                "message": error_payload.get("message", "HA Error (no details provided)."),
                "details": error_payload.get("code"),
            },
        }

    result = response.get("result")
    areas_source = result if isinstance(result, list) else []
    truncated = len(areas_source) > max_items
    if truncated:
        areas_source = areas_source[:max_items]

    areas = [
        {
            "area_id": area.get("area_id"),
            "name": area.get("name"),
            "picture": area.get("picture"),
        }
        for area in areas_source
        if isinstance(area, dict)
    ]
    return {
        "ok": True,
        "areas": areas,
        "count": len(areas),
        "truncated": truncated,
    }


async def ha_ws_resolve_from_area(
    *,
    area_id: str | None = None,
    area_name: str | None = None,
    include_entities: bool = True,
    include_devices: bool = True,
    expand_group: bool = True,
    entity_domain_filter: list[str] | None = None,
    max_entities: int = 200,
    max_devices: int = 200,
) -> dict[str, Any]:
    """Resolve entity/device ids targeted by a Home Assistant area."""
    if bool(area_id) == bool(area_name):
        return {
            "ok": False,
            "error": {
                "code": "INVALID_INPUT",
                "message": "Provide exactly one of area_id or area_name.",
                "details": None,
            },
        }

    resolved_area_id = area_id
    area_summary = {"area_id": area_id, "name": None}
    if area_name:
        area_name_clean = area_name.strip()
        if not area_name_clean:
            return {
                "ok": False,
                "error": {
                    "code": "INVALID_INPUT",
                    "message": "area_name must be non-empty.",
                    "details": None,
                },
            }
        registry_response = await ha_ws_area_registry_list()
        if not registry_response.get("ok", False):
            return {"ok": False, "error": registry_response.get("error")}

        areas = registry_response.get("areas", [])
        exact_matches = [
            area
            for area in areas
            if isinstance(area, dict)
            and isinstance(area.get("name"), str)
            and area.get("name").lower() == area_name_clean.lower()
        ]
        matches = exact_matches
        if not matches:
            matches = [
                area
                for area in areas
                if isinstance(area, dict)
                and isinstance(area.get("name"), str)
                and area_name_clean.lower() in area.get("name").lower()
            ]

        if not matches:
            return {
                "ok": False,
                "error": {
                    "code": "AREA_NOT_FOUND",
                    "message": f'No area matches "{area_name_clean}".',
                    "details": None,
                },
            }

        if len(matches) > 1:
            candidates = [
                {"area_id": area.get("area_id"), "name": area.get("name")}
                for area in matches
            ]
            return {
                "ok": False,
                "candidates": candidates,
                "error": {
                    "code": "AMBIGUOUS_AREA",
                    "message": f'Multiple areas match "{area_name_clean}".',
                    "details": {"candidates": candidates},
                },
            }

        match = matches[0]
        resolved_area_id = match.get("area_id")
        area_summary = {"area_id": resolved_area_id, "name": match.get("name")}

    if not resolved_area_id:
        return {
            "ok": False,
            "error": {
                "code": "AREA_NOT_FOUND",
                "message": "area_id could not be resolved.",
                "details": None,
            },
        }

    max_entities = max(0, int(max_entities))
    max_devices = max(0, int(max_devices))
    try:
        response = await ws_client.send_command(
            "extract_from_target",
            {
                "target": {"area_id": [resolved_area_id]},
                "expand_group": expand_group,
            },
            is_write=False,
            timeout_s=10,
        )
    except HomeAssistantWsError as exc:
        if exc.code == "HA_ERROR":
            error_payload = exc.details if isinstance(exc.details, dict) else {}
            return {
                "ok": False,
                "error": {
                    "code": "HA_WS_ERROR",
                    "message": error_payload.get("message", "Home Assistant error."),
                    "details": error_payload.get("code"),
                },
            }
        return {
            "ok": False,
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            },
        }
    except Exception as exc:
        logger.exception("WS extract_from_target failed.")
        return {
            "ok": False,
            "error": {
                "code": "UNKNOWN",
                "message": str(exc),
                "details": None,
            },
        }

    if not response.get("success", True):
        error_payload = response.get("error", {})
        return {
            "ok": False,
            "error": {
                "code": "HA_WS_ERROR",
                "message": error_payload.get("message", "HA Error (no details provided)."),
                "details": error_payload.get("code"),
            },
        }

    result = response.get("result") if isinstance(response.get("result"), dict) else {}
    entities = _as_str_list(result.get("referenced_entities"))
    devices = _as_str_list(result.get("referenced_devices"))

    if not include_entities:
        entities = []
    elif entity_domain_filter is not None:
        allowed = {
            domain.strip().lower()
            for domain in entity_domain_filter
            if isinstance(domain, str) and domain.strip()
        }
        entities = [
            entity_id
            for entity_id in entities
            if entity_id.split(".", 1)[0].lower() in allowed
        ]

    if not include_devices:
        devices = []

    truncated_entities = len(entities) > max_entities
    truncated_devices = len(devices) > max_devices
    if truncated_entities:
        entities = entities[:max_entities]
    if truncated_devices:
        devices = devices[:max_devices]

    missing = {
        "areas": _as_str_list(result.get("missing_areas")),
        "devices": _as_str_list(result.get("missing_devices")),
        "floors": _as_str_list(result.get("missing_floors")),
        "labels": _as_str_list(result.get("missing_labels")),
    }

    return {
        "ok": True,
        "area": area_summary,
        "entity_ids": entities,
        "device_ids": devices,
        "counts": {"entities": len(entities), "devices": len(devices)},
        "truncated_entities": truncated_entities,
        "truncated_devices": truncated_devices,
        "missing": missing,
    }
