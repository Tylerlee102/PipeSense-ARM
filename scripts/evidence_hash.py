#!/usr/bin/env python3
"""Canonical hashing for publication-evidence files."""

from __future__ import annotations

import hashlib
from pathlib import Path


def canonical_sha256(path: str | Path) -> str:
    """Return a SHA-256 digest after normalizing record endings to LF."""
    data = Path(path).read_bytes()
    data = data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(data).hexdigest()
