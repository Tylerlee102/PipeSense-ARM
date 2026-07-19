#!/usr/bin/env python3
"""Fetch and patch the pinned Ibex source used by the PipeSense integration."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import stat
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "integrations" / "ibex"
DEFAULT_DEST = ROOT / "build" / "ibex"
DEFAULT_EMBENCH_DEST = ROOT / "build" / "embench-iot"


def run(command: list[str], cwd: Path | None = None) -> None:
    subprocess.run(command, cwd=cwd, check=True)


def remove_readonly(function, path: str, _error) -> None:
    os.chmod(path, stat.S_IWRITE)
    function(path)


def checkout(url: str, commit: str, dest: Path, clean: bool) -> None:
    if clean and dest.exists():
        build_root = (ROOT / "build").resolve()
        if not dest.is_relative_to(build_root):
            raise RuntimeError(f"refusing to remove checkout outside {build_root}: {dest}")
        shutil.rmtree(dest, onexc=remove_readonly)

    if not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        run([
            "git", "-c", "core.autocrlf=false", "clone", "--filter=blob:none",
            "--no-checkout", url, str(dest),
        ])

    run(["git", "config", "core.autocrlf", "false"], cwd=dest)
    run(["git", "fetch", "--depth", "1", "origin", commit], cwd=dest)
    run(["git", "checkout", "--detach", "--force", commit], cwd=dest)
    run(["git", "clean", "-fdx"], cwd=dest)

    actual = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=dest, text=True).strip()
    if actual != commit:
        raise RuntimeError(f"revision mismatch for {dest}: expected {commit}, found {actual}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dest", type=Path, default=DEFAULT_DEST)
    parser.add_argument("--embench-dest", type=Path, default=DEFAULT_EMBENCH_DEST)
    parser.add_argument("--clean", action="store_true")
    args = parser.parse_args()

    lock = json.loads((INTEGRATION / "lock.json").read_text(encoding="utf-8"))
    url = lock["ibex"]["url"]
    commit = lock["ibex"]["commit"]
    dest = args.dest.resolve()
    embench_dest = args.embench_dest.resolve()

    checkout(url, commit, dest, args.clean)
    for patch in sorted((INTEGRATION / "patches").glob("*.patch")):
        run(["git", "apply", "--check", str(patch)], cwd=dest)
        run(["git", "apply", str(patch)], cwd=dest)
    shutil.copy2(INTEGRATION / "rtl" / "pipesense_ibex_control.sv", dest / "rtl")
    software_root = dest / "examples" / "sw" / "simple_system"
    for software_source in (INTEGRATION / "sw").iterdir():
        if software_source.is_dir():
            shutil.copytree(software_source, software_root / software_source.name)

    checkout(lock["embench"]["url"], lock["embench"]["commit"], embench_dest, args.clean)

    print(f"Prepared PipeSense-Ibex at {dest} ({commit})")
    print(f"Prepared Embench at {embench_dest} ({lock['embench']['commit']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
