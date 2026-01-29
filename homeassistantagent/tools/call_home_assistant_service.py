import logging
from typing import Any

from pydantic_ai import RunContext
from pydantic_ai.exceptions import ApprovalRequired

from clients import HomeAssistantApiClient

logger = logging.getLogger(__name__)
home_assistant_client = HomeAssistantApiClient()


def call_home_assistant_service(
    ctx: RunContext[None],
    domain: str,
    service: str,
    service_data: dict[str, Any] | None = None,
    return_response: bool | None = False,
) -> dict[str, Any]:
    """Call a Home Assistant service and return changed states and optional response data.

    This tool invokes the Home Assistant Services API at
    `/api/services/{domain}/{service}` with optional `service_data`. It waits for the
    service to execute and returns the list of states that changed while the service
    ran. If the service supports response data, set `return_response=True` to request
    it (the API will return both `changed_states` and `service_response`).

    Args:
        domain: The service domain (for example, "light", "switch", "mqtt", "weather").
        service: The service name within the domain (for example, "turn_on", "publish",
            "get_forecasts").
        service_data: Optional JSON payload to send as service data (for example,
            {"entity_id": "light.study_light"}).
        return_response: When True, appends `?return_response` to the request URL to
            retrieve service response data for services that support it. If used with
            a service that does not return data, or omitted for a service that requires
            data, Home Assistant will return a 400 error.

    Returns:
        A dictionary with:
            - success: True when the request succeeds, False otherwise.
            - result: The raw service response (list of changed states or a dict
              containing `changed_states` and `service_response`) when successful.
            - error: Error message string when the request fails.
    """
    domain_value = str(domain).lower()
    service_value = str(service).lower()
    is_light_service = domain_value == "light" and service_value in {"turn_on", "turn_off", "toggle"}
    if not is_light_service and not ctx.tool_call_approved:
        raise ApprovalRequired

    try:
        response = home_assistant_client.call_service(
            domain=domain_value,
            service=service_value,
            service_data=service_data,
            return_response=bool(return_response),
        )
        return {"success": True, "result": response}
    except Exception as exc:
        logger.exception(
            "Service call failed for domain=%s service=%s data=%s return_response=%s",
            domain,
            service,
            service_data,
            return_response,
        )
        return {"success": False, "error": str(exc)}
