## DOCS: docs/tool_specs/search_entities.md
import logging
import time
from typing import Any

from rapidfuzz import fuzz, process, utils

from clients import HomeAssistantApiClient

logger = logging.getLogger(__name__)
home_assistant_client = HomeAssistantApiClient()


def _as_str(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def _entity_domain(entity_id: str | None) -> str:
    if not entity_id:
        return ""
    return entity_id.split(".", 1)[0]


def _build_search_text(entity_id: str | None, name: str | None) -> str:
    parts = [part for part in (entity_id, name) if isinstance(part, str) and part]
    return " ".join(parts)


def search_entities(query: str, limit: int = 10) -> dict[str, Any]:
    """Fuzzy-search Home Assistant entities by query string."""
    start_time = time.perf_counter()
    if not isinstance(query, str) or not query.strip():
        logger.info(
            "search_entities completed in %.2fms (invalid input)",
            (time.perf_counter() - start_time) * 1000,
        )
        return {
            "ok": False,
            "error": {
                "code": "INVALID_INPUT",
                "message": "query must be a non-empty string.",
                "details": None,
            },
        }

    limit = max(0, int(limit))
    try:
        states = home_assistant_client.list_states()
    except Exception as exc:
        logger.exception("REST list_states failed for search_entities.")
        logger.info(
            "search_entities completed in %.2fms (error)",
            (time.perf_counter() - start_time) * 1000,
        )
        return {
            "ok": False,
            "error": {
                "code": "HA_REST_ERROR",
                "message": str(exc),
                "details": None,
            },
        }

    if not isinstance(states, list):
        logger.info(
            "search_entities completed in %.2fms (invalid response)",
            (time.perf_counter() - start_time) * 1000,
        )
        return {
            "ok": False,
            "error": {
                "code": "INVALID_RESPONSE",
                "message": "Home Assistant returned invalid entity list.",
                "details": None,
            },
        }

    entities: list[dict[str, Any]] = []
    candidates: list[str] = []
    for state in states:
        if not isinstance(state, dict):
            continue
        entity_id = _as_str(state.get("entity_id"))
        attributes = state.get("attributes") if isinstance(state.get("attributes"), dict) else {}
        name = _as_str(attributes.get("friendly_name"))
        search_text = _build_search_text(entity_id, name)
        if not search_text:
            continue
        entities.append(
            {
                "entity_id": entity_id,
                "name": name,
                "domain": _entity_domain(entity_id),
                "state": _as_str(state.get("state")),
            }
        )
        candidates.append(search_text)

    if not candidates or limit == 0:
        logger.info(
            "search_entities completed in %.2fms (no candidates)",
            (time.perf_counter() - start_time) * 1000,
        )
        return {
            "ok": True,
            "query": query,
            "count": 0,
            "matches": [],
        }

    matches = process.extract(
        query,
        candidates,
        scorer=fuzz.WRatio,
        processor=utils.default_process,
        limit=limit,
    )

    results = []
    for _candidate, score, index in matches:
        entity = entities[index]
        results.append({**entity, "score": float(score)})

    result = {
        "ok": True,
        "query": query,
        "count": len(results),
        "matches": results,
    }
    logger.info(
        "search_entities completed in %.2fms",
        (time.perf_counter() - start_time) * 1000,
    )
    return result
