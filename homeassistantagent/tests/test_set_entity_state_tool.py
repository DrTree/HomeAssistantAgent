import unittest
from unittest.mock import MagicMock, patch

from homeassistantagent.tools.set_entity_state import set_entity_state


class SetEntityStateToolTests(unittest.TestCase):
    def test_single_entity_valid_service_verified_success(self) -> None:
        with patch("homeassistantagent.tools.set_entity_state.home_assistant_client") as client:
            client.get_state = MagicMock(
                side_effect=[
                    {"state": "off", "last_changed": "t1"},
                    {"state": "on", "last_changed": "t2"},
                ]
            )
            client.call_service = MagicMock(return_value=None)
            result = set_entity_state(
                entity_ids=["light.kitchen"],
                service="light.turn_on",
                service_data={"brightness": 25},
                verify="basic",
            )

        client.call_service.assert_called_once_with(
            "light",
            "turn_on",
            {"brightness": 25, "target": {"entity_id": ["light.kitchen"]}},
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["processed_count"], 1)
        self.assertEqual(result["skipped_count"], 0)
        self.assertEqual(result["per_entity"][0]["before_state"], "off")
        self.assertEqual(result["per_entity"][0]["after_state"], "on")
        self.assertTrue(result["per_entity"][0]["changed"])

    def test_multiple_entities_single_service_call(self) -> None:
        with patch("homeassistantagent.tools.set_entity_state.home_assistant_client") as client:
            client.get_state = MagicMock(
                side_effect=[
                    {"state": "off", "last_changed": "t1"},
                    {"state": "off", "last_changed": "t2"},
                ]
            )
            client.call_service = MagicMock(return_value=None)
            result = set_entity_state(
                entity_ids=["switch.a", "switch.b"],
                service="switch.turn_on",
                verify="none",
            )

        client.call_service.assert_called_once_with(
            "switch",
            "turn_on",
            {"target": {"entity_id": ["switch.a", "switch.b"]}},
        )
        self.assertEqual(result["processed_count"], 2)
        self.assertEqual(len(result["per_entity"]), 2)

    def test_partial_missing_entities(self) -> None:
        with patch("homeassistantagent.tools.set_entity_state.home_assistant_client") as client:
            client.get_state = MagicMock(
                side_effect=[
                    {"state": "off", "last_changed": "t1"},
                    RuntimeError("Home Assistant API error 404: Not Found"),
                ]
            )
            client.call_service = MagicMock(return_value=None)
            result = set_entity_state(
                entity_ids=["light.kitchen", "light.missing"],
                service="light.turn_on",
                verify="none",
            )

        client.call_service.assert_called_once_with(
            "light",
            "turn_on",
            {"target": {"entity_id": ["light.kitchen"]}},
        )
        missing = [entry for entry in result["per_entity"] if entry["entity_id"] == "light.missing"][0]
        self.assertFalse(missing["ok"])
        self.assertEqual(missing["error_code"], "ENTITY_NOT_FOUND")
        self.assertTrue(missing["skipped"])

    def test_domain_not_allowlisted(self) -> None:
        with patch("homeassistantagent.tools.set_entity_state.home_assistant_client") as client:
            result = set_entity_state(
                entity_ids=["mqtt.topic"],
                service="mqtt.publish",
            )

        self.assertFalse(result["ok"])
        self.assertIn("DOMAIN_NOT_ALLOWED", result["errors"][0])
        client.call_service.assert_not_called()

    def test_domain_entity_mismatch(self) -> None:
        with patch("homeassistantagent.tools.set_entity_state.home_assistant_client") as client:
            client.get_state = MagicMock(return_value={"state": "off", "last_changed": "t1"})
            client.call_service = MagicMock(return_value=None)
            result = set_entity_state(
                entity_ids=["switch.kettle"],
                service="light.turn_on",
                verify="none",
            )

        client.call_service.assert_not_called()
        self.assertEqual(result["processed_count"], 0)
        self.assertEqual(result["per_entity"][0]["error_code"], "DOMAIN_ENTITY_MISMATCH")

    def test_dry_run_no_service_call(self) -> None:
        with patch("homeassistantagent.tools.set_entity_state.home_assistant_client") as client:
            client.get_state = MagicMock(return_value={"state": "off", "last_changed": "t1"})
            client.call_service = MagicMock(return_value=None)
            result = set_entity_state(
                entity_ids=["light.kitchen"],
                service="light.turn_on",
                dry_run=True,
            )

        client.call_service.assert_not_called()
        self.assertTrue(result["dry_run"])
        self.assertEqual(result["payload"]["target"]["entity_id"], ["light.kitchen"])
        self.assertEqual(result["per_entity"][0]["after_state"], "on")

    def test_skip_if_already(self) -> None:
        with patch("homeassistantagent.tools.set_entity_state.home_assistant_client") as client:
            client.get_state = MagicMock(return_value={"state": "on", "last_changed": "t1"})
            client.call_service = MagicMock(return_value=None)
            result = set_entity_state(
                entity_ids=["light.kitchen"],
                service="light.turn_on",
                skip_if_already=True,
            )

        client.call_service.assert_not_called()
        self.assertTrue(result["per_entity"][0]["skipped"])
        self.assertFalse(result["per_entity"][0]["changed"])
