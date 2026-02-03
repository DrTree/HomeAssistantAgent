import importlib
import unittest
from unittest.mock import MagicMock, patch

search_entities_module = importlib.import_module("homeassistantagent.tools.search_entities")


class SearchEntitiesToolTests(unittest.TestCase):
    def test_search_entities_returns_ranked_matches(self) -> None:
        states = [
            {
                "entity_id": "light.bedroom_ceiling",
                "state": "on",
                "attributes": {"friendly_name": "Bedroom Ceiling"},
            },
            {
                "entity_id": "switch.kitchen",
                "state": "off",
                "attributes": {"friendly_name": "Kitchen Switch"},
            },
            {
                "entity_id": "light.bedroom_lamp",
                "state": "off",
                "attributes": {"friendly_name": "Bedroom Lamp"},
            },
        ]
        with patch.object(search_entities_module, "home_assistant_client") as client:
            client.list_states = MagicMock(return_value=states)
            result = search_entities_module.search_entities("bedroom ceiling", limit=2)

        self.assertTrue(result["ok"])
        self.assertEqual(result["count"], 2)
        self.assertEqual(result["matches"][0]["entity_id"], "light.bedroom_ceiling")
        self.assertEqual(result["matches"][0]["name"], "Bedroom Ceiling")
        self.assertEqual(result["matches"][0]["domain"], "light")
        self.assertEqual(result["matches"][0]["state"], "on")
        self.assertIsInstance(result["matches"][0]["score"], float)

    def test_search_entities_handles_invalid_query(self) -> None:
        result = search_entities_module.search_entities("   ")

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "INVALID_INPUT")

    def test_search_entities_handles_invalid_state_response(self) -> None:
        with patch.object(search_entities_module, "home_assistant_client") as client:
            client.list_states = MagicMock(return_value={"not": "a list"})
            result = search_entities_module.search_entities("bedroom")

        self.assertFalse(result["ok"])
        self.assertEqual(result["error"]["code"], "INVALID_RESPONSE")
