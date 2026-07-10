#!/usr/bin/env python3
"""Build and render the local workshop manuscript."""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAPER_DIR = ROOT / "paper"
PAPER_NAME = "pipesense_urtc_5page.tex"
PAPER = PAPER_DIR / PAPER_NAME
OUTPUT_DIR = ROOT / "output" / "paper_preview"
BUILD_DIR = OUTPUT_DIR / "build"
BUILD_SOURCE = BUILD_DIR / "source"
PAGES_DIR = OUTPUT_DIR / "pages"
DOCKERFILE = PAPER_DIR / "Dockerfile"
DEFAULT_IMAGE = "pipesense-paper:latest"


def run(command: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    print("+ " + " ".join(command))
    return subprocess.run(
        command,
        cwd=cwd,
        text=True,
        check=check,
    )


def prepare_build_tree() -> None:
    if not PAPER.exists():
        raise RuntimeError(f"Missing manuscript source: {PAPER}")
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    BUILD_SOURCE.mkdir(parents=True)
    PAGES_DIR.mkdir(parents=True)
    shutil.copytree(PAPER_DIR, BUILD_SOURCE, dirs_exist_ok=True)


def latexmk_arguments() -> list[str]:
    arguments = [
        "-pdf",
        "-interaction=nonstopmode",
        "-halt-on-error",
        "-file-line-error",
    ]
    sources: list[str] = []
    for path in PAPER_DIR.rglob("*.tex"):
        source = path.read_text(encoding="utf-8")
        sources.extend(re.sub(r"(?<!\\)%.*$", "", line) for line in source.splitlines())
    source = "\n".join(sources)
    if not re.search(r"\\cite\w*\{", source):
        arguments.append("-bibtex-")
    arguments.append(PAPER_NAME)
    return arguments


def build_local() -> None:
    latexmk = shutil.which("latexmk")
    if not latexmk:
        raise RuntimeError("latexmk is not available on PATH")
    run([latexmk] + latexmk_arguments(), cwd=BUILD_SOURCE)


def docker_image_exists(image: str) -> bool:
    result = subprocess.run(
        ["docker", "image", "inspect", image],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def ensure_docker_image(image: str, rebuild: bool) -> None:
    if not shutil.which("docker"):
        raise RuntimeError("Neither local latexmk nor Docker is available")
    if rebuild or not docker_image_exists(image):
        run(
            [
                "docker",
                "build",
                "--file",
                str(DOCKERFILE),
                "--tag",
                image,
                str(ROOT),
            ]
        )


def docker_base(image: str) -> list[str]:
    return [
        "docker",
        "run",
        "--rm",
        "--volume",
        f"{ROOT}:/workspace",
        "--workdir",
        "/workspace/output/paper_preview/build/source",
        image,
    ]


def build_docker(image: str, rebuild: bool) -> None:
    ensure_docker_image(image, rebuild)
    run(docker_base(image) + ["latexmk"] + latexmk_arguments())


def copy_build_outputs() -> Path:
    stem = Path(PAPER_NAME).stem
    built_pdf = BUILD_SOURCE / f"{stem}.pdf"
    if not built_pdf.exists():
        raise RuntimeError(f"LaTeX completed without producing {built_pdf}")
    for suffix in [".pdf", ".log", ".aux", ".bbl", ".blg", ".fls", ".fdb_latexmk"]:
        source = BUILD_SOURCE / f"{stem}{suffix}"
        if source.exists():
            shutil.copy2(source, OUTPUT_DIR / source.name)
    return OUTPUT_DIR / built_pdf.name


def render_pages(pdf: Path, engine: str, image: str) -> None:
    prefix = PAGES_DIR / "page"
    pdftoppm = shutil.which("pdftoppm") if engine == "local" else None
    if pdftoppm:
        run([pdftoppm, "-png", "-r", "150", str(pdf), str(prefix)])
        return
    ensure_docker_image(image, rebuild=False)
    run(
        docker_base(image)
        + [
            "pdftoppm",
            "-png",
            "-r",
            "150",
            f"/workspace/output/paper_preview/{pdf.name}",
            "/workspace/output/paper_preview/pages/page",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--engine",
        choices=["auto", "local", "docker"],
        default="auto",
        help="Use local latexmk, Docker, or automatically choose an available engine.",
    )
    parser.add_argument("--image", default=DEFAULT_IMAGE, help="Docker image name.")
    parser.add_argument("--rebuild-image", action="store_true", help="Rebuild the TeX image.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    prepare_build_tree()
    engine = args.engine
    if engine == "auto":
        engine = "local" if shutil.which("latexmk") else "docker"
    if engine == "local":
        build_local()
    else:
        build_docker(args.image, args.rebuild_image)
    pdf = copy_build_outputs()
    render_pages(pdf, engine, args.image)
    page_count = len(list(PAGES_DIR.glob("page-*.png")))
    print(f"Built {pdf}")
    print(f"Rendered {page_count} page image(s) under {PAGES_DIR}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"FAIL {exc}")
        raise SystemExit(1)
