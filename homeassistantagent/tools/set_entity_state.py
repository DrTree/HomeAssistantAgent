import logging
from typing import Any

from clients import HomeAssistantApiClient

logger = logging.getLogger(__name__)
home_assistant_client = HomeAssistantApiClient()

ALLOWED_DOMAINS = {
    "light",
    "switch",
    "climate",
    "cover",
    "lock",
    "fan",
    "media_player",
    "scene",
    "script",
    "vacuum",
    "humidifier",
    "water_heater",
    "alarm_control_panel",
    "input_boolean",
    "input_number",
    "input_select",
    "input_text",
    "counter",
    "number",
    "select",
}

MAX_ENTITY_IDS = 20
MAX_SERVICE_DATA_KEYS = 20
IDEMPOTENT_SERVICES = {"turn_on", "turn_off"}


def _is_primitive(value: Any) -> bool:
    return isinstance(value, (str, int, float, bool)) or value is None


def _is_primitive_list(value: Any) -> bool:
    if isinstance(value, tuple):
        value = list(value)
    if not isinstance(value, list):
        return False
    return all(_is_primitive(item) for item in value)


def _validate_service_data(service_data: Any) -> tuple[bool, dict[str, Any], str | None]:
    if service_data is None:
        return True, {}, None
    if not isinstance(service_data, dict):
        return False, {}, "service_data must be an object."
    if len(service_data) > MAX_SERVICE_DATA_KEYS:
        return False, {}, "service_data has too many keys."

    cleaned: dict[str, Any] = {}
    for key, value in service_data.items():
        if not isinstance(key, str) or not key:
            return False, {}, "service_data keys must be non-empty strings."
        if isinstance(value, dict):
            return False, {}, "service_data must be shallow (no nested objects)."
        if isinstance(value, (list, tuple)):
            if not _is_primitive_list(value):
                return False, {}, "service_data arrays must contain primitives only."
            cleaned[key] = list(value)
            continue
        if not _is_primitive(value):
            return False, {}, "service_data values must be JSON-serializable primitives."
        cleaned[key] = value
    return True, cleaned, None


def _parse_service(service: Any) -> tuple[bool, str, str, str | None]:
    if not isinstance(service, str) or "." not in service:
        return False, "", "", "service must be formatted as '<domain>.<service>'."
    domain, service_name = service.split(".", 1)
    domain = domain.strip().lower()
    service_name = service_name.strip().lower()
    if not domain or not service_name:
        return False, "", "", "service must be formatted as '<domain>.<service>'."
    return True, domain, service_name, None


def _normalize_entity_ids(entity_ids: Any) -> tuple[bool, list[str], bool, str | None]:
    if not isinstance(entity_ids, list):
        return False, [], False, "entity_ids must be a list."
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in entity_ids:
        if not isinstance(value, str):
            return False, [], False, "entity_ids must contain only strings."
        value = value.strip()
        if not value:
            return False, [], False, "entity_ids must be non-empty."
        if value in seen:
            return False, [], False, "entity_ids must be unique."
        cleaned.append(value)
        seen.add(value)
    if not cleaned:
        return False, [], False, "entity_ids must be non-empty."

    truncated = False
    if len(cleaned) > MAX_ENTITY_IDS:
        cleaned = cleaned[:MAX_ENTITY_IDS]
        truncated = True
    return True, cleaned, truncated, None


def _error_response(
    code: str,
    message: str,
    service_label: str,
    requested_count: int,
    truncated: bool,
    dry_run: bool,
) -> dict[str, Any]:
    return {
        "ok": False,
        "service": service_label,
        "requested_count": requested_count,
        "processed_count": 0,
        "skipped_count": 0,
        "truncated": truncated,
        "dry_run": dry_run,
        "per_entity": [],
        "errors": [f"{code}: {message}"],
    }


def _extract_state(state_payload: Any) -> str | None:
    if not isinstance(state_payload, dict):
        return None
    state = state_payload.get("state")
    return state if isinstance(state, str) else None


def _get_entity_domain(entity_id: str) -> str:
    return entity_id.split(".", 1)[0].lower()


def _finalize_errors(errors: list[str]) -> list[str] | None:
    if not errors:
        return None
    unique: list[str] = []
    seen: set[str] = set()
    for error in errors:
        if error and error not in seen:
            unique.append(error)
            seen.add(error)
    return unique or None


def _with_errors(response: dict[str, Any], errors: list[str]) -> dict[str, Any]:
    finalized = _finalize_errors(errors)
    if finalized is None:
        response.pop("errors", None)
    else:
        response["errors"] = finalized
    return response


def set_entity_state(
    entity_ids: list[str],
    service: str,
    service_data: dict[str, Any] | None = None,
    dry_run: bool = False,
    verify: str = "basic",
    skip_if_already: bool = False,
) -> dict[str, Any]:
    """Invoke Home Assistant services for known entity ids via the REST API."""
    requested_count = len(entity_ids) if isinstance(entity_ids, list) else 0
    entity_ok, cleaned_entities, truncated, entity_error = _normalize_entity_ids(entity_ids)
    if not entity_ok:
        return _error_response(
            "INVALID_INPUT",
            entity_error or "Invalid entity_ids.",
            service,
            requested_count,
            truncated,
            bool(dry_run),
        )

    service_ok, domain, service_name, service_error = _parse_service(service)
    service_label = f"{domain}.{service_name}" if service_ok else service
    if not service_ok:
        return _error_response(
            "INVALID_INPUT",
            service_error or "Invalid service.",
            service_label,
            requested_count,
            truncated,
            bool(dry_run),
        )

    if domain not in ALLOWED_DOMAINS:
        return _error_response(
            "DOMAIN_NOT_ALLOWED",
            f"Domain '{domain}' is not allowed.",
            service_label,
            requested_count,
            truncated,
            bool(dry_run),
        )

    if verify not in {"none", "basic"}:
        return _error_response(
            "INVALID_INPUT",
            "verify must be 'none' or 'basic'.",
            service_label,
            requested_count,
            truncated,
            bool(dry_run),
        )

    data_ok, cleaned_service_data, service_data_error = _validate_service_data(service_data)
    if not data_ok:
        return _error_response(
            "INVALID_INPUT",
            service_data_error or "Invalid service_data.",
            service_label,
            requested_count,
            truncated,
            bool(dry_run),
        )

    non_idempotent = service_name == "toggle" or (
        domain in {"scene", "script"} and service_name == "turn_on"
    )
    skip_applicable = skip_if_already and service_name in IDEMPOTENT_SERVICES

    errors: list[str] = []
    if skip_if_already and non_idempotent:
        errors.append("skip_if_already ignored for non-idempotent service")
    elif skip_if_already and not skip_applicable:
        errors.append("skip_if_already ignored for unsupported service")

    before_states: dict[str, str | None] = {}
    missing_entities: set[str] = set()
    read_failures: dict[str, str] = {}
    for entity_id in cleaned_entities:
        try:
            state_payload = home_assistant_client.get_state(entity_id)
            before_states[entity_id] = _extract_state(state_payload)
        except Exception as exc:
            message = str(exc)
            if "404" in message:
                missing_entities.add(entity_id)
            else:
                read_failures[entity_id] = message

    per_entity: list[dict[str, Any]] = []
    entry_by_entity: dict[str, dict[str, Any]] = {}
    to_call: list[str] = []
    skipped_count = 0

    for entity_id in cleaned_entities:
        before_state = before_states.get(entity_id)
        if entity_id in missing_entities:
            entry = {
                "entity_id": entity_id,
                "ok": False,
                "skipped": True,
                "error_code": "ENTITY_NOT_FOUND",
                "before_state": before_state,
            }
            per_entity.append(entry)
            entry_by_entity[entity_id] = entry
            skipped_count += 1
            continue
        if entity_id in read_failures:
            entry = {
                "entity_id": entity_id,
                "ok": False,
                "skipped": True,
                "error_code": "SERVICE_CALL_FAILED",
                "before_state": before_state,
            }
            per_entity.append(entry)
            entry_by_entity[entity_id] = entry
            errors.append("Failed to read one or more entity states")
            skipped_count += 1
            continue
        if _get_entity_domain(entity_id) != domain:
            entry = {
                "entity_id": entity_id,
                "ok": False,
                "skipped": True,
                "error_code": "DOMAIN_ENTITY_MISMATCH",
                "before_state": before_state,
            }
            per_entity.append(entry)
            entry_by_entity[entity_id] = entry
            skipped_count += 1
            continue
        if skip_applicable:
            if service_name == "turn_on" and before_state == "on":
                entry = {
                    "entity_id": entity_id,
                    "ok": True,
                    "skipped": True,
                    "before_state": before_state,
                    "after_state": before_state,
                    "changed": False,
                }
                per_entity.append(entry)
                entry_by_entity[entity_id] = entry
                skipped_count += 1
                continue
            if service_name == "turn_off" and before_state == "off":
                entry = {
                    "entity_id": entity_id,
                    "ok": True,
                    "skipped": True,
                    "before_state": before_state,
                    "after_state": before_state,
                    "changed": False,
                }
                per_entity.append(entry)
                entry_by_entity[entity_id] = entry
                skipped_count += 1
                continue
        entry = {
            "entity_id": entity_id,
            "ok": True,
            "skipped": False,
            "before_state": before_state,
        }
        per_entity.append(entry)
        entry_by_entity[entity_id] = entry
        to_call.append(entity_id)

    payload = dict(cleaned_service_data)
    payload["target"] = {"entity_id": to_call}

    if dry_run:
        for entity_id in to_call:
            before_state = before_states.get(entity_id)
            after_state: str | None = None
            changed: bool | None = None
            if service_name == "turn_on":
                after_state = "on"
                changed = before_state != after_state
            elif service_name == "turn_off":
                after_state = "off"
                changed = before_state != after_state
            entry = entry_by_entity.get(entity_id)
            if entry is None:
                entry = {
                    "entity_id": entity_id,
                    "ok": True,
                    "skipped": False,
                    "before_state": before_state,
                }
                per_entity.append(entry)
                entry_by_entity[entity_id] = entry
            entry["after_state"] = after_state
            entry["changed"] = changed
        response = {
            "ok": True,
            "service": service_label,
            "requested_count": requested_count,
            "processed_count": 0,
            "skipped_count": skipped_count,
            "truncated": truncated,
            "dry_run": True,
            "per_entity": per_entity,
            "payload": payload,
            "errors": [],
        }
        return _with_errors(response, errors)

    if not to_call:
        response = {
            "ok": True,
            "service": service_label,
            "requested_count": requested_count,
            "processed_count": 0,
            "skipped_count": skipped_count,
            "truncated": truncated,
            "dry_run": False,
            "per_entity": per_entity,
            "errors": [],
        }
        return _with_errors(response, errors)

    try:
        home_assistant_client.call_service(domain, service_name, payload)
    except Exception as exc:
        logger.exception("Service call failed for %s", service_label)
        error_message = str(exc)
        errors.append("Service call failed")
        for entity_id in to_call:
            before_state = before_states.get(entity_id)
            entry = entry_by_entity.get(entity_id)
            if entry is None:
                entry = {
                    "entity_id": entity_id,
                    "ok": False,
                    "skipped": False,
                    "before_state": before_state,
                }
                per_entity.append(entry)
                entry_by_entity[entity_id] = entry
            entry["ok"] = False
            entry["skipped"] = False
            entry["error_code"] = "SERVICE_CALL_FAILED"
            entry["before_state"] = before_state
        response = {
            "ok": False,
            "service": service_label,
            "requested_count": requested_count,
            "processed_count": 0,
            "skipped_count": skipped_count,
            "truncated": truncated,
            "dry_run": False,
            "per_entity": per_entity,
            "errors": [],
        }
        return _with_errors(response, errors or [error_message])

    processed_count = len(to_call)
    if verify == "basic":
        for entity_id in to_call:
            before_state = before_states.get(entity_id)
            after_state = None
            changed = None
            ok = True
            error_code = None
            try:
                state_payload = home_assistant_client.get_state(entity_id)
                after_state = _extract_state(state_payload)
                if before_state is not None and after_state is not None:
                    changed = before_state != after_state
            except Exception:
                ok = False
                error_code = "SERVICE_CALL_FAILED"
                errors.append("Post-call state read failed")
            entry = entry_by_entity.get(entity_id)
            if entry is None:
                entry = {
                    "entity_id": entity_id,
                    "ok": ok,
                    "skipped": False,
                    "before_state": before_state,
                }
                per_entity.append(entry)
                entry_by_entity[entity_id] = entry
            entry["ok"] = ok
            entry["skipped"] = False
            entry["before_state"] = before_state
            entry["after_state"] = after_state
            entry["changed"] = changed
            if error_code:
                entry["error_code"] = error_code
    else:
        for entity_id in to_call:
            before_state = before_states.get(entity_id)
            entry = entry_by_entity.get(entity_id)
            if entry is None:
                entry = {
                    "entity_id": entity_id,
                    "ok": True,
                    "skipped": False,
                    "before_state": before_state,
                }
                per_entity.append(entry)
                entry_by_entity[entity_id] = entry
            entry["ok"] = True
            entry["skipped"] = False
            entry["before_state"] = before_state

    response = {
        "ok": True,
        "service": service_label,
        "requested_count": requested_count,
        "processed_count": processed_count,
        "skipped_count": skipped_count,
        "truncated": truncated,
        "dry_run": False,
        "per_entity": per_entity,
        "errors": [],
    }
    return _with_errors(response, errors)
