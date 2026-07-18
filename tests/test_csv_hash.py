#!/usr/bin/env python3
"""Regression tests for platform-independent CSV evidence hashes."""

from __future__ import annotations

import hashlib
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.evidence_hash import canonical_sha256  # noqa: E402


class CanonicalCsvHashTests(unittest.TestCase):
    def test_lf_crlf_and_cr_files_have_the_same_hash(self) -> None:
        lf_data = b"name,value\nalpha,1\nbeta,2\n"
        variants = {
            "lf.csv": lf_data,
            "crlf.csv": lf_data.replace(b"\n", b"\r\n"),
            "cr.csv": lf_data.replace(b"\n", b"\r"),
        }
        expected = hashlib.sha256(lf_data).hexdigest()

        with tempfile.TemporaryDirectory() as directory:
            hashes = []
            for name, data in variants.items():
                path = Path(directory) / name
                path.write_bytes(data)
                hashes.append(canonical_sha256(path))

        self.assertEqual(hashes, [expected, expected, expected])

    def test_different_csv_values_have_different_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "first.csv"
            second = Path(directory) / "second.csv"
            first.write_bytes(b"name,value\nalpha,1\n")
            second.write_bytes(b"name,value\nalpha,2\n")

            self.assertNotEqual(canonical_sha256(first), canonical_sha256(second))


if __name__ == "__main__":
    unittest.main()
