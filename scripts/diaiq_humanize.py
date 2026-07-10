#!/usr/bin/env python3
"""Humanize text with the public DiaIQ Humanizer API."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


DEFAULT_API_URL = "https://humanizer.diaiq.com/api/humanize"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "text",
        nargs="*",
        help="Text to humanize. If a single value is an existing path, that file is read.",
    )
    source.add_argument("--file", help="Path to a UTF-8 text or markdown file to humanize.")
    parser.add_argument(
        "--passes",
        type=int,
        choices=(1, 2, 3),
        default=1,
        help="Number of humanization passes to request. Default: 1.",
    )
    parser.add_argument("--output", help="Optional path for the humanized text.")
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Confirm that file contents may be sent to the public DiaIQ API.",
    )
    parser.add_argument(
        "--literal",
        action="store_true",
        help="Treat positional input as literal text even if it names an existing file.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate input and print the request summary without calling DiaIQ.",
    )
    parser.add_argument("--api-url", default=DEFAULT_API_URL, help=argparse.SUPPRESS)
    parser.add_argument(
        "--timeout",
        type=float,
        default=60.0,
        help="HTTP timeout in seconds. Default: 60.",
    )
    return parser.parse_args()


def word_count(text: str) -> int:
    return len(text.split())


def read_source(args: argparse.Namespace) -> tuple[str, str, bool]:
    if args.file:
        path = Path(args.file)
        return path.read_text(encoding="utf-8"), str(path), True

    text = " ".join(args.text or [])
    if not text.strip():
        raise ValueError("No text was provided.")

    maybe_path = Path(text)
    if not args.literal and len(args.text or []) == 1 and maybe_path.exists():
        return maybe_path.read_text(encoding="utf-8"), str(maybe_path), True

    return text, "inline text", False


def confirm_file_upload(source_name: str, args: argparse.Namespace) -> None:
    if args.yes or args.dry_run:
        return
    if not sys.stdin.isatty():
        raise ValueError(
            "Refusing to send file contents without confirmation. "
            "Re-run with --yes if this file is safe to send to the public DiaIQ API."
        )

    print(
        f"DiaIQ will receive the contents of {source_name}. "
        "Only continue if the file contains no sensitive or private content.",
        file=sys.stderr,
    )
    print("Send this file to DiaIQ? [y/N] ", end="", file=sys.stderr, flush=True)
    answer = sys.stdin.readline()
    if not answer:
        raise ValueError(
            "Refusing to send file contents without confirmation. "
            "Re-run with --yes if this file is safe to send to the public DiaIQ API."
        )
    answer = answer.strip().lower()
    if answer not in {"y", "yes"}:
        raise ValueError("Canceled without sending content.")


def post_json(url: str, payload: dict[str, Any], timeout: float) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "pipesense-diaiq-tool/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"DiaIQ request failed with HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"DiaIQ request failed: {exc.reason}") from exc

    try:
        result = json.loads(body)
    except json.JSONDecodeError as exc:
        raise RuntimeError("DiaIQ returned invalid JSON.") from exc

    if not isinstance(result, dict):
        raise RuntimeError("DiaIQ returned an unexpected response shape.")
    return result


def write_result(text: str, output: str | None) -> None:
    if output:
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        print(f"Wrote humanized text to {path}")
        return

    print(text)


def main() -> int:
    args = parse_args()
    try:
        text, source_name, is_file = read_source(args)
        if is_file:
            confirm_file_upload(source_name, args)

        original_words = word_count(text)
        if args.dry_run:
            print(
                "DiaIQ dry run: "
                f"source={source_name}, words={original_words}, passes={args.passes}"
            )
            return 0

        result = post_json(
            args.api_url,
            {"text": text, "passes": args.passes},
            args.timeout,
        )
        humanized = result.get("text")
        if not isinstance(humanized, str) or not humanized.strip():
            raise RuntimeError("DiaIQ response did not include humanized text.")

        write_result(humanized, args.output)

        humanized_words = result.get("humanized_words", word_count(humanized))
        reported_original = result.get("original_words", original_words)
        reported_passes = result.get("passes", args.passes)
        print(
            f"DiaIQ words: {reported_original} -> {humanized_words}; "
            f"passes={reported_passes}",
            file=sys.stderr,
        )
        return 0
    except Exception as exc:
        print(f"FAIL {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
