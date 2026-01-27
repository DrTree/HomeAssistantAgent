import logging

from clients import HomeAssistantApiClient

logger = logging.getLogger(__name__)
home_assistant_client = HomeAssistantApiClient()


def render_home_assistant_template(
    template: str, variables: dict | None = None
) -> dict[str, str | bool]:
    """Render a Home Assistant Jinja2 template using the built-in template API."""
    try:
        response = home_assistant_client.render_template(template, variables)
        if isinstance(response, str):
            return {"success": True, "result": response}
        if isinstance(response, dict):
            message = response.get("message", "Template rendering failed.")
            return {"success": False, "error": message}
        return {"success": False, "error": "Unexpected response from template API."}
    except Exception as exc:
        logger.exception(
            "Template render failed for template=%s variables=%s", template, variables
        )
        return {"success": False, "error": str(exc)}
