## DOCS: docs/tool_specs/ha_search_services.md
import logging
from typing import Any

from clients import HomeAssistantApiClient, HomeAssistantWebSocketClient
from clients.homeassistant_ws_client import HomeAssistantWsError

logger = logging.getLogger(__name__)
ws_client = HomeAssistantWebSocketClient()
rest_client = HomeAssistantApiClient()

_MAX_SERVICES_SCANNED = 10_000
_MAX_FIELDS_PER_SERVICE = 25
_MAX_DESC_LEN = 200
_MAX_FIELD_DESC_LEN = 120
_MAX_QUERY_TOKENS = 5


def _truncate(text: str | None, max_len: int) -> str | None:
    if not isinstance(text, str):
        return None
    if len(text) <= max_len:
        return text
    if max_len <= 1:
        return "…"
    return f"{text[: max_len - 1]}…"


def _normalize_token_text(text: str) -> str:
    return " ".join(text.lower().replace("_", " ").replace(".", " ").split())


def _tokenize_query(query: str) -> list[str]:
    normalized = _normalize_token_text(query)
    if not normalized:
        return []
    return normalized.split()[:_MAX_QUERY_TOKENS]


def _match_text(value: str, query: str, match_type: str) -> bool:
    if match_type == "exact":
        return value == query
    if match_type == "prefix":
        return value.startswith(query)
    return query in value


def _build_candidates(domain_text: str, domains: list[str]) -> list[str]:
    domain_text = domain_text.lower()
    prefix_matches = [domain for domain in domains if domain.startswith(domain_text)]
    if len(prefix_matches) >= 10:
        return prefix_matches[:10]
    try:
        import difflib

        close = difflib.get_close_matches(domain_text, domains, n=10, cutoff=0.4)
    except Exception:
        close = []
    merged: list[str] = []
    for item in prefix_matches + close:
        if item not in merged:
            merged.append(item)
    return merged[:10]


def _selector_type(selector: Any) -> str | None:
    if not isinstance(selector, dict):
        return None
    for key in selector:
        return str(key)
    return None


def _field_example(value: Any) -> str | int | float | bool | None:
    if isinstance(value, (str, int, float, bool)):
        return value
    return None


def _build_fields(fields: Any) -> tuple[list[dict[str, Any]], bool]:
    if not isinstance(fields, dict):
        return [], False
    items: list[dict[str, Any]] = []
    for field_name, meta in fields.items():
        if len(items) >= _MAX_FIELDS_PER_SERVICE:
            break
        if not isinstance(field_name, str) or not isinstance(meta, dict):
            continue
        items.append(
            {
                "field": field_name,
                "required": meta.get("required") if isinstance(meta.get("required"), bool) else None,
                "selector_type": _selector_type(meta.get("selector")),
                "description": _truncate(meta.get("description"), _MAX_FIELD_DESC_LEN),
                "example": _field_example(meta.get("example")),
            }
        )
    truncated = len(items) < len(fields)
    return items, truncated


def _extract_targets(target: Any) -> dict[str, bool]:
    if not isinstance(target, dict):
        return {
            "supports_entity_target": False,
            "supports_device_target": False,
            "supports_area_target": False,
        }
    return {
        "supports_entity_target": bool(target.get("entity")),
        "supports_device_target": bool(target.get("device")),
        "supports_area_target": bool(target.get("area")),
    }


def _service_entries_from_payload(payload: Any) -> dict[str, dict[str, Any]]:
    if isinstance(payload, dict) and all(isinstance(v, dict) for v in payload.values()):
        return payload
    if isinstance(payload, list):
        result: dict[str, dict[str, Any]] = {}
        for domain_entry in payload:
            if not isinstance(domain_entry, dict):
                continue
            domain = domain_entry.get("domain")
            services = domain_entry.get("services")
            if isinstance(domain, str) and isinstance(services, dict):
                result[domain] = services
        return result
    return {}


async def _fetch_services() -> tuple[dict[str, dict[str, Any]], dict[str, Any] | None]:
    try:
        response = await ws_client.send_command("get_services", {}, is_write=False, timeout_s=10)
        if not response.get("success", True):
            error_payload = response.get("error", {})
            return {}, {
                "code": "HA_UNAVAILABLE",
                "message": error_payload.get("message", "Home Assistant error."),
                "details": error_payload.get("code"),
            }
        services = _service_entries_from_payload(response.get("result"))
        if services:
            return services, None
    except HomeAssistantWsError as exc:
        if exc.code == "AUTH_INVALID":
            return {}, {"code": "HA_AUTH_FAILED", "message": exc.message, "details": exc.details}
        logger.info("WS get_services failed; falling back to REST: %s", exc)
    except Exception as exc:
        logger.exception("WS get_services failed; falling back to REST.")

    try:
        services = _service_entries_from_payload(rest_client.list_services())
        if services:
            return services, None
        return {}, {"code": "HA_UNAVAILABLE", "message": "No services returned.", "details": None}
    except Exception as exc:
        message = str(exc)
        code = "HA_UNAVAILABLE"
        if "token" in message.lower() or "401" in message or "403" in message:
            code = "HA_AUTH_FAILED"
        return {}, {"code": code, "message": message, "details": None}


async def ha_search_services(
    *,
    query: str = "",
    domain: str | None = None,
    include_fields: bool = False,
    include_targets: bool = False,
    limit: int = 25,
    offset: int = 0,
    sort: str = "relevance",
    match: str = "contains",
    return_raw: bool = False,
) -> dict[str, Any]:
    """Search Home Assistant services with optional filters and compact results."""
    if not isinstance(query, str):
        return {
            "ok": False,
            "code": "INVALID_ARGUMENT",
            "message": "query must be a string.",
            "details": None,
            "candidates": None,
        }
    query = query.strip()
    domain_input = domain.strip().lower() if isinstance(domain, str) and domain.strip() else None

    if sort not in {"relevance", "domain", "service"}:
        return {
            "ok": False,
            "code": "INVALID_ARGUMENT",
            "message": "sort must be one of relevance, domain, or service.",
            "details": None,
            "candidates": None,
        }
    if match not in {"contains", "prefix", "exact"}:
        return {
            "ok": False,
            "code": "INVALID_ARGUMENT",
            "message": "match must be one of contains, prefix, or exact.",
            "details": None,
            "candidates": None,
        }

    try:
        limit = int(limit)
        offset = int(offset)
    except (TypeError, ValueError):
        return {
            "ok": False,
            "code": "INVALID_ARGUMENT",
            "message": "limit and offset must be integers.",
            "details": None,
            "candidates": None,
        }

    if limit < 1:
        return {
            "ok": False,
            "code": "INVALID_ARGUMENT",
            "message": "limit must be between 1 and 50.",
            "details": None,
            "candidates": None,
        }
    if limit > 50:
        limit = 50
    if offset < 0 or offset > 10_000:
        return {
            "ok": False,
            "code": "INVALID_ARGUMENT",
            "message": "offset must be between 0 and 10000.",
            "details": None,
            "candidates": None,
        }

    if return_raw:
        logger.info("ha_search_services called with return_raw=True; still applying allowlists.")

    services_by_domain, error = await _fetch_services()
    if error:
        return {"ok": False, "candidates": None, **error}

    domains = sorted(services_by_domain.keys())

    if domain_input:
        normalized_domains = {domain_name.lower(): domain_name for domain_name in domains}
        if match != "exact":
            match_candidates = [
                domain_name
                for domain_name in domains
                if _match_text(domain_name.lower(), domain_input, match)
            ]
            if len(match_candidates) > 1:
                return {
                    "ok": False,
                    "code": "AMBIGUOUS_DOMAIN",
                    "message": "Multiple domains match the provided domain filter.",
                    "details": None,
                    "candidates": [{"domain": name} for name in match_candidates[:10]],
                }
        if domain_input not in normalized_domains:
            candidates = _build_candidates(domain_input, [d.lower() for d in domains])
            return {
                "ok": False,
                "code": "DOMAIN_NOT_FOUND",
                "message": "Domain not found.",
                "details": None,
                "candidates": candidates,
            }
        domains = [normalized_domains[domain_input]]

    query_tokens = _tokenize_query(query)
    query_normalized = _normalize_token_text(query)

    matches: list[dict[str, Any]] = []
    scanned = 0
    truncated_scan = False

    for domain_name in domains:
        services = services_by_domain.get(domain_name, {})
        if not isinstance(services, dict):
            continue
        for service_name, meta in services.items():
            if scanned >= _MAX_SERVICES_SCANNED:
                truncated_scan = True
                break
            scanned += 1
            if not isinstance(service_name, str) or not isinstance(meta, dict):
                continue

            service_text = _normalize_token_text(service_name)
            domain_text = _normalize_token_text(domain_name)
            domain_service_text = _normalize_token_text(f"{domain_name}.{service_name}")

            score = 0
            matched = False
            if query_tokens:
                if _match_text(domain_service_text, query_normalized, "exact"):
                    score += 10
                    matched = True
                if _match_text(service_text, query_normalized, "exact"):
                    score += 7
                    matched = True
                if _match_text(service_text, query_normalized, "prefix"):
                    score += 5
                    matched = True
                if _match_text(service_text, query_normalized, "contains"):
                    score += 3
                    matched = True

                description_text = ""
                if isinstance(meta.get("description"), str):
                    description_text = meta.get("description", "").lower()
                name_text = ""
                if isinstance(meta.get("name"), str):
                    name_text = meta.get("name", "").lower()

                if any(token in description_text or token in name_text for token in query_tokens):
                    score += 2
                    matched = True

                fields_meta = meta.get("fields") if isinstance(meta.get("fields"), dict) else {}
                field_text = " ".join(
                    f"{field_name} {field_meta.get('description', '')}"
                    for field_name, field_meta in fields_meta.items()
                    if isinstance(field_name, str) and isinstance(field_meta, dict)
                ).lower()
                if any(token in field_text for token in query_tokens):
                    score += 1
                    matched = True

                if not matched:
                    continue

            service_entry = {
                "domain": domain_name,
                "service": service_name,
                "name": meta.get("name") if isinstance(meta.get("name"), str) else None,
                "description": _truncate(meta.get("description"), _MAX_DESC_LEN),
                "score": score if (query_tokens or sort == "relevance") else None,
                "targets": _extract_targets(meta.get("target")) if include_targets else None,
                "fields": None,
                "fields_truncated": None,
            }

            if include_fields:
                fields, fields_truncated = _build_fields(meta.get("fields"))
                service_entry["fields"] = fields
                service_entry["fields_truncated"] = fields_truncated

            matches.append(service_entry)
        if truncated_scan:
            break

    if not query_tokens and domain_input is None:
        matches.sort(key=lambda item: (item["domain"], item["service"]))
        services_slice = matches[offset : offset + limit]
        total_available = len(matches) if not truncated_scan else None
        truncated = truncated_scan or (total_available is not None and offset + limit < total_available)
        return {
            "ok": True,
            "count": len(services_slice),
            "total_available": total_available,
            "offset": offset,
            "limit": limit,
            "truncated": truncated,
            "truncated_scan": truncated_scan,
            "note": f"Empty query; returning first {len(services_slice)} services. Provide query for relevance.",
            "services": services_slice,
        }

    if sort == "domain":
        matches.sort(key=lambda item: (item["domain"], item["service"]))
    elif sort == "service":
        matches.sort(key=lambda item: (item["service"], item["domain"]))
    else:
        matches.sort(key=lambda item: (-int(item.get("score") or 0), item["domain"], item["service"]))

    total_available = len(matches) if not truncated_scan else None
    services_slice = matches[offset : offset + limit]
    truncated = truncated_scan or (total_available is not None and offset + limit < total_available)

    return {
        "ok": True,
        "count": len(services_slice),
        "total_available": total_available,
        "offset": offset,
        "limit": limit,
        "truncated": truncated,
        "truncated_scan": truncated_scan,
        "services": services_slice,
    }
