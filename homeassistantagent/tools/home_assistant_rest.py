import logging
from typing import Any, Iterable

from clients import HomeAssistantApiClient

logger = logging.getLogger(__name__)
home_assistant_client = HomeAssistantApiClient()


def _as_list(value: str | Iterable[str]) -> list[str]:
    if isinstance(value, str):
        return [value]
    return list(value)


def ha_rest_ping() -> dict[str, Any]:
    """Ping the Home Assistant REST API (/api/)."""
    try:
        response = home_assistant_client._request("GET", "/api/")
        return {"success": True, "result": response}
    except Exception as exc:
        logger.exception("REST ping failed.")
        return {"success": False, "error": str(exc)}


def ha_rest_get_config() -> dict[str, Any]:
    """Get the Home Assistant config summary."""
    try:
        return {"success": True, "result": home_assistant_client.get_config()}
    except Exception as exc:
        logger.exception("REST get_config failed.")
        return {"success": False, "error": str(exc)}


def ha_rest_list_components() -> dict[str, Any]:
    """List loaded Home Assistant components."""
    try:
        return {"success": True, "result": home_assistant_client.list_components()}
    except Exception as exc:
        logger.exception("REST list_components failed.")
        return {"success": False, "error": str(exc)}


def ha_rest_list_states() -> dict[str, Any]:
    """Get all current entity states."""
    try:
        return {"success": True, "result": home_assistant_client.list_states()}
    except Exception as exc:
        logger.exception("REST list_states failed.")
        return {"success": False, "error": str(exc)}


def ha_rest_get_state(entity_id: str) -> dict[str, Any]:
    """Get a single entity state."""
    try:
        return {"success": True, "result": home_assistant_client.get_state(entity_id)}
    except Exception as exc:
        logger.exception("REST get_state failed for entity_id=%s", entity_id)
        return {"success": False, "error": str(exc)}


def ha_rest_list_services() -> dict[str, Any]:
    """List available services."""
    try:
        return {"success": True, "result": home_assistant_client.list_services()}
    except Exception as exc:
        logger.exception("REST list_services failed.")
        return {"success": False, "error": str(exc)}


def ha_rest_list_events() -> dict[str, Any]:
    """List event types and listener counts."""
    try:
        return {"success": True, "result": home_assistant_client.list_events()}
    except Exception as exc:
        logger.exception("REST list_events failed.")
        return {"success": False, "error": str(exc)}


def ha_rest_history_period(
    start_time: str,
    entity_ids: str | list[str],
    end_time: str | None = None,
    minimal_response: bool = True,
    no_attributes: bool = True,
    significant_changes_only: bool = True,
) -> dict[str, Any]:
    """Fetch history for entities over a period."""
    try:
        entities = _as_list(entity_ids)
        if not entities:
            raise ValueError("entity_ids must include at least one entity id.")
        result = home_assistant_client.history_period(
            start_time=start_time,
            entity_ids=entities,
            end_time=end_time,
            minimal_response=minimal_response,
            no_attributes=no_attributes,
            significant_changes_only=significant_changes_only,
        )
        return {"success": True, "result": result}
    except Exception as exc:
        logger.exception("REST history_period failed.")
        return {"success": False, "error": str(exc)}


def ha_rest_logbook(
    start_time: str,
    end_time: str | None = None,
    entity_ids: str | list[str] | None = None,
) -> dict[str, Any]:
    """Fetch logbook entries."""
    try:
        entities = _as_list(entity_ids) if entity_ids is not None else None
        result = home_assistant_client.logbook(
            start_time=start_time,
            end_time=end_time,
            entity_ids=entities,
        )
        return {"success": True, "result": result}
    except Exception as exc:
        logger.exception("REST logbook failed.")
        return {"success": False, "error": str(exc)}


def ha_rest_error_log() -> dict[str, Any]:
    """Get the Home Assistant error log."""
    try:
        return {"success": True, "result": home_assistant_client.error_log()}
    except Exception as exc:
        logger.exception("REST error_log failed.")
        return {"success": False, "error": str(exc)}


def ha_rest_check_config() -> dict[str, Any]:
    """Run Home Assistant configuration check."""
    try:
        return {"success": True, "result": home_assistant_client.check_config()}
    except Exception as exc:
        logger.exception("REST check_config failed.")
        return {"success": False, "error": str(exc)}


def ha_rest_list_calendars() -> dict[str, Any]:
    """List calendar entities."""
    try:
        return {"success": True, "result": home_assistant_client.list_calendars()}
    except Exception as exc:
        logger.exception("REST list_calendars failed.")
        return {"success": False, "error": str(exc)}


def ha_rest_get_calendar_events(
    calendar_entity_id: str,
    start: str,
    end: str,
) -> dict[str, Any]:
    """Get events for a calendar entity in a time range."""
    try:
        result = home_assistant_client.get_calendar_events(
            calendar_entity_id=calendar_entity_id,
            start=start,
            end=end,
        )
        return {"success": True, "result": result}
    except Exception as exc:
        logger.exception("REST get_calendar_events failed.")
        return {"success": False, "error": str(exc)}


def ha_rest_camera_proxy(camera_entity_id: str) -> dict[str, Any]:
    """Fetch a camera image via the camera proxy API, returning base64 content."""
    try:
        return {"success": True, "result": home_assistant_client.camera_proxy(camera_entity_id)}
    except Exception as exc:
        logger.exception("REST camera_proxy failed.")
        return {"success": False, "error": str(exc)}


def ha_rest_fire_event(event_type: str, event_data: dict[str, Any] | None = None) -> dict[str, Any]:
    """Fire a Home Assistant event."""
    try:
        return {
            "success": True,
            "result": home_assistant_client.fire_event(event_type, event_data),
        }
    except Exception as exc:
        logger.exception("REST fire_event failed for event_type=%s", event_type)
        return {"success": False, "error": str(exc)}


def ha_rest_set_state(
    entity_id: str,
    state: str,
    attributes: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Set an entity state in Home Assistant's state machine."""
    try:
        return {
            "success": True,
            "result": home_assistant_client.set_state(entity_id, state, attributes),
        }
    except Exception as exc:
        logger.exception("REST set_state failed for entity_id=%s", entity_id)
        return {"success": False, "error": str(exc)}


def ha_rest_delete_state(entity_id: str) -> dict[str, Any]:
    """Delete an entity state from Home Assistant's state machine."""
    try:
        return {"success": True, "result": home_assistant_client.delete_state(entity_id)}
    except Exception as exc:
        logger.exception("REST delete_state failed for entity_id=%s", entity_id)
        return {"success": False, "error": str(exc)}


def ha_rest_handle_intent(intent: str, slots: dict[str, Any] | None = None) -> dict[str, Any]:
    """Handle a Home Assistant intent."""
    try:
        return {
            "success": True,
            "result": home_assistant_client.handle_intent(intent, slots),
        }
    except Exception as exc:
        logger.exception("REST handle_intent failed for intent=%s", intent)
        return {"success": False, "error": str(exc)}
