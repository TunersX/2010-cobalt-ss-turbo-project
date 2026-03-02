import json
import tempfile
import unittest
from pathlib import Path

from tunersx.orchestration.provider import run_active_operations_provider
from tunersx.policy.enforcer import PolicySnapshot
from tunersx.core.types import PipelineState, RiskClass


class ReadinessOrchestrationTests(unittest.TestCase):
    def test_j2534_policy_blocks_unknown_service(self):
        policy = PolicySnapshot(risk_class=RiskClass.PASSIVE, state=PipelineState.COMPLETE)
        ok, _, reason = policy.evaluate("j2534.routine_control")
        self.assertFalse(ok)
        self.assertIn("blocked", reason)

    def test_provider_wrapper_captures_outputs(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            res = run_active_operations_provider(["python", "-c", "print('hello')"], out)
            self.assertEqual(res["returncode"], 0)
            self.assertTrue((out / "provider_stdout.txt").exists())
            self.assertIn("hello", (out / "provider_stdout.txt").read_text(encoding="utf-8"))
            meta = json.loads((out / "provider_result.json").read_text(encoding="utf-8"))
            self.assertEqual(meta["stdout_file"], "provider_stdout.txt")


if __name__ == "__main__":
    unittest.main()
