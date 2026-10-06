"""Exercise provider-neutral role routing without granting new authority."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from schema_validation import validate_instance

spec = importlib.util.spec_from_file_location("runtime_resolver", ROOT / "scripts/resolve-runtime.py")
resolver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(resolver)


class ModelPortabilityTest(unittest.TestCase):
    def setUp(self):
        self.routing = json.loads((ROOT / "examples/model-neutral/runtime-routing.json").read_text())
        self.request = json.loads((ROOT / "examples/model-neutral/request.json").read_text())

    def test_neutral_policy_preserves_contract_requirements(self):
        schema = json.loads((ROOT / "docs/agent/schemas/runtime-routing.schema.json").read_text())
        self.assertEqual(validate_instance(self.routing, schema), [])
        canonical = json.loads((ROOT / "docs/agent/runtime-routing.json").read_text())
        self.assertEqual(self.routing["policy"], canonical["policy"])
        fields = ("id", "stage", "role", "required_model_capabilities")
        self.assertEqual(
            [{key: route[key] for key in fields} for route in self.routing["routes"]],
            [{key: route[key] for key in fields} for route in canonical["routes"]],
        )

    def test_each_role_selects_operator_primary_or_explicit_fallback(self):
        for route in self.routing["routes"]:
            for target, fallback in (("operator-primary", False), ("operator-fallback", True)):
                with self.subTest(role=route["role"], target=target):
                    request = {"stage": "analyze" if route["stage"] == "*" else route["stage"],
                               "role": route["role"], "available_targets": [target]}
                    result = resolver.resolve(self.routing, request)
                    self.assertEqual(result["target_id"], target)
                    self.assertEqual(result["fallback"], fallback)
                    self.assertEqual(result["role"], route["role"])
                    self.assertEqual(set(result["required_model_capabilities"]),
                                     set(route["required_model_capabilities"]))
                    self.assertEqual(bool(result["fallback_reason"]), fallback)

    def test_operator_model_binding_is_independent_of_role_authority(self):
        for adapter in ("custom", "openai-compatible", "ollama", "lm-studio"):
            routing = copy.deepcopy(self.routing)
            routing["targets"][0].update(adapter=adapter, model_ref="env:PILOT_MODEL",
                                         endpoint_ref="env:PILOT_ENDPOINT")
            with self.subTest(adapter=adapter):
                result = resolver.resolve(routing, self.request)
                self.assertEqual(result["adapter"], adapter)
                self.assertEqual(result["model_ref"], "env:PILOT_MODEL")
                self.assertEqual(result["endpoint_ref"], "env:PILOT_ENDPOINT")
                self.assertEqual(result["role"], "implementer")
                self.assertEqual(result["stage"], "green_code")
                self.assertFalse(result["overlay_applied"])

    def test_incompatible_available_primary_blocks_instead_of_falling_back(self):
        self.routing["targets"][0]["capabilities"].remove("code_generation")
        self.request["available_targets"] = ["operator-primary", "operator-fallback"]
        with self.assertRaisesRegex(ValueError, "lacks required model capabilities"):
            resolver.resolve(self.routing, self.request)

    def test_repository_cannot_choose_the_model_or_add_a_target(self):
        self.request.update(available_targets=["operator-primary", "operator-fallback"],
                            overlay={"implementer": "operator-fallback"}, overlay_source="repository")
        with self.assertRaisesRegex(ValueError, "repository content cannot select a runtime"):
            resolver.resolve(self.routing, self.request)
        self.request["overlay_source"] = "operator"
        self.assertEqual(resolver.resolve(self.routing, self.request)["target_id"], "operator-fallback")
        self.request["available_targets"].append("unregistered-model")
        with self.assertRaisesRegex(ValueError, "unknown target ids"):
            resolver.resolve(self.routing, self.request)


if __name__ == "__main__":
    unittest.main()
