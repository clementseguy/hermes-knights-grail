"""Le schéma public doit exposer les champs exigés par les validateurs."""
import importlib.util
import sys
import unittest
from pathlib import Path


class _Context:
    def __init__(self):
        self.schemas = {}

    def register_tool(self, name, _toolset, schema, _handler):
        self.schemas[name] = schema


class ToolSchemaTests(unittest.TestCase):
    def test_nested_source_and_metric_fields_are_exposed(self):
        root = Path(__file__).parents[1] / "plugins/leodagan-editorial"
        spec = importlib.util.spec_from_file_location(
            "leodagan_editorial_test", root / "__init__.py",
            submodule_search_locations=[str(root)])
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        context = _Context()
        module.register(context)
        review = context.schemas["editorial_review"]["parameters"]["properties"]
        source = review["sources"]["items"]
        self.assertEqual(set(source["required"]),
                         {"url", "access_status", "accessed_at", "critical_review"})
        self.assertEqual(set(source["properties"]["critical_review"]["required"]),
                         {"thesis", "evidence", "limits", "cto_objection", "executive_impact"})
        self.assertIn("final_url", source["properties"])
        save = context.schemas["editorial_save"]["parameters"]
        self.assertEqual(save["required"], ["identifier", "review_id"])
        feedback = context.schemas["editorial_feedback"]["parameters"]["properties"]
        metric = feedback["metrics"]["items"]
        self.assertEqual(set(metric["required"]), {"type", "value", "origin"})


if __name__ == "__main__":
    unittest.main()
