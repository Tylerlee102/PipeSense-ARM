import csv
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def canonical_bytes(path: Path) -> bytes:
    return path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")


class IbexFuzzGenerationTest(unittest.TestCase):
    def test_500_seed_artifacts_are_reproducible(self):
        committed_c = ROOT / "integrations/ibex/sw/pipesense_fuzz/pipesense_fuzz.c"
        committed_csv = ROOT / "integrations/ibex/verif/fuzz_expected.csv"
        with tempfile.TemporaryDirectory() as temp_dir:
            generated_c = Path(temp_dir) / "pipesense_fuzz.c"
            generated_csv = Path(temp_dir) / "fuzz_expected.csv"
            subprocess.run([
                sys.executable, str(ROOT / "scripts/generate_ibex_fuzz.py"),
                "--seeds", "500", "--c-output", str(generated_c),
                "--csv-output", str(generated_csv),
            ], cwd=ROOT, check=True, capture_output=True, text=True)
            self.assertEqual(canonical_bytes(committed_c), canonical_bytes(generated_c))
            self.assertEqual(canonical_bytes(committed_csv), canonical_bytes(generated_csv))

        with committed_csv.open(newline="", encoding="ascii") as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(500, len(rows))
        self.assertEqual(list(range(500)), [int(row["seed"]) for row in rows])


if __name__ == "__main__":
    unittest.main()
