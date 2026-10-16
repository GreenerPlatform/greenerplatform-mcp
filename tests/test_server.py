import json
import unittest

import greenerplatform_mcp as gp


class TestAdapterContract(unittest.TestCase):
    def test_resource_deep_dive_is_explicitly_unsupported(self):
        result = json.loads(gp.sentinel_snapshot(resource="pod/example"))
        self.assertEqual(result["code"], "unsupported_resource")

    def test_warning_is_attached_to_json_object(self):
        result = json.loads(gp._attach_warnings('{"findings": []}', ["version drift"]))
        self.assertEqual(result["warnings"], ["version drift"])

    def test_invalid_output_is_not_rewritten(self):
        raw = "not-json"
        self.assertEqual(gp._attach_warnings(raw, ["version drift"]), raw)


if __name__ == "__main__":
    unittest.main()
