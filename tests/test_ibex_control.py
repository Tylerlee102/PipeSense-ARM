import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class IbexControlTest(unittest.TestCase):
    @unittest.skipUnless(shutil.which("iverilog") and shutil.which("vvp"), "iverilog is unavailable")
    def test_repeated_drain_protected_switches(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "control.vvp"
            subprocess.run([
                "iverilog", "-g2012", "-s", "pipesense_ibex_control_tb",
                "-o", str(output),
                str(ROOT / "integrations/ibex/rtl/pipesense_ibex_control.sv"),
                str(ROOT / "integrations/ibex/verif/pipesense_ibex_control_tb.sv"),
            ], check=True, cwd=ROOT)
            result = subprocess.run(["vvp", str(output)], check=True, cwd=ROOT,
                                    text=True, capture_output=True)
            self.assertIn("PIPESENSE_IBEX_CONTROL_PASS transitions=2", result.stdout)


if __name__ == "__main__":
    unittest.main()
