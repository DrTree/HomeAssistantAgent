import logging
from typing import Any

from clients import HomeAssistantApiClient

logger = logging.getLogger(__name__)
home_assistant_client = HomeAssistantApiClient()


def render_home_assistant_template(
    template: str, variables: dict | None = None
) -> dict[str, str | bool | dict[str, Any]]:
    """Render a home assistant template.
    Useful for quickly computing values based on Home Assistant's templating engine.

    @param template: The template to render.
    @param variables: The variables to use in the template.
    @return: A dict with the result of the rendering.
    """
    try:
        response = home_assistant_client.render_template(template, variables)
        if isinstance(response, str):
            return {"success": True, "result": response}
        if isinstance(response, dict):
            message = response.get("message", "Template rendering failed.")
            return {"success": False, "error": message, "response": response}
        return {"success": False, "error": "Unexpected response from template API: {response}."}
    except Exception as exc:
        logger.exception(
            "Template render failed for template=%s variables=%s", template, variables
        )
        return {"success": False, "error": str(exc)}
