#!/usr/bin/env python3
"""Run source-level workshop-readiness checks on the local manuscript."""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAPER_DIR = ROOT / "paper"
PAPER = PAPER_DIR / "pipesense_urtc_5page.tex"
BIB = PAPER_DIR / "references.bib"
CHECKLIST = PAPER_DIR / "SUBMISSION_CHECKLIST.md"

PLACEHOLDERS = [
    "Paper Title",
    "Author Name",
    "Affiliation",
    "City, Country",
    "email@example.com",
    "Write the abstract here",
    "Add keywords here",
    "TODO",
    "TBD",
    "FIXME",
    "Lorem ipsum",
    "??",
]

REQUIRED_SECTION_PATTERNS = {
    "introduction": r"\bintroduction\b",
    "background or related work": r"\b(background|related work)\b",
    "design or methodology": r"\b(design|method|methodology|approach|architecture|implementation)\b",
    "evaluation": r"\b(evaluation|experiment|methodology)\b",
    "results": r"\b(results?|findings?)\b",
    "discussion or limitations": r"\b(discussion|limitations?|threats? to validity)\b",
    "conclusion": r"\bconclusions?\b",
}

FORBIDDEN_LAYOUT_PATTERNS = {
    "negative vertical spacing": r"\\vspace\s*\{\s*-",
    "manual page enlargement": r"\\enlargethispage\b",
    "document-wide tiny text": r"\\(?:tiny|scriptsize)\b",
    "manual text-area override": r"\\setlength\s*\{\\(?:textwidth|textheight|oddsidemargin|evensidemargin)",
    "geometry package override": r"\\usepackage(?:\[[^]]*\])?\{geometry\}",
}


def remove_comments(text: str) -> str:
    cleaned: list[str] = []
    for line in text.splitlines():
        cut = len(line)
        for index, char in enumerate(line):
            if char != "%":
                continue
            backslashes = 0
            cursor = index - 1
            while cursor >= 0 and line[cursor] == "\\":
                backslashes += 1
                cursor -= 1
            if backslashes % 2 == 0:
                cut = index
                break
        cleaned.append(line[:cut])
    return "\n".join(cleaned)


def visible_text(text: str) -> str:
    text = re.sub(r"\\begin\{[^}]+\}|\\end\{[^}]+\}", " ", text)
    text = re.sub(r"\\(?:cite|ref|eqref|label|url|path)\w*\{[^}]*\}", " ", text)
    text = re.sub(r"\\[A-Za-z@]+\*?(?:\[[^]]*\])?", " ", text)
    text = re.sub(r"[{}$&_~^#]", " ", text)
    text = text.replace("\\%", "%").replace("\\_", "_")
    return re.sub(r"\s+", " ", text).strip()


def words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9][A-Za-z0-9'-]*", visible_text(text))


def environment_content(tex: str, name: str) -> str | None:
    match = re.search(
        rf"\\begin\{{{re.escape(name)}\}}(.*?)\\end\{{{re.escape(name)}\}}",
        tex,
        flags=re.DOTALL,
    )
    return match.group(1) if match else None


def section_contents(tex: str) -> list[tuple[str, str]]:
    matches = list(re.finditer(r"\\section\*?\{([^}]+)\}", tex))
    sections: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(tex)
        content = tex[match.end() : end]
        content = re.split(r"\\bibliographystyle|\\bibliography|\\end\{document\}", content)[0]
        sections.append((visible_text(match.group(1)), content))
    return sections


def resolve_latex_asset(raw: str, extensions: tuple[str, ...]) -> bool:
    candidate = Path(raw)
    if candidate.is_absolute():
        bases = [candidate]
    else:
        bases = [PAPER_DIR / candidate]
    for base in bases:
        if base.suffix and base.exists():
            return True
        for extension in extensions:
            if base.with_suffix(extension).exists():
                return True
    return False


def run_checks() -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    if not PAPER.exists():
        return [f"Missing manuscript source: {PAPER}"], warnings
    if not BIB.exists():
        return [f"Missing bibliography: {BIB}"], warnings

    raw_tex = PAPER.read_text(encoding="utf-8")
    tex = remove_comments(raw_tex)
    bib = BIB.read_text(encoding="utf-8")
    checklist = CHECKLIST.read_text(encoding="utf-8") if CHECKLIST.exists() else ""
    if not CHECKLIST.exists():
        errors.append(f"Missing manual submission checklist: {CHECKLIST}")

    class_match = re.search(r"\\documentclass(?:\[([^]]*)\])?\{([^}]+)\}", tex)
    if not class_match or class_match.group(2) != "IEEEtran":
        errors.append("The manuscript must use the IEEEtran document class.")
    elif "conference" not in (class_match.group(1) or ""):
        errors.append("IEEEtran must be used in conference mode.")
    if class_match and re.search(r"(?:^|,)\s*(?:8|9)pt\s*(?:,|$)", class_match.group(1) or ""):
        errors.append("The venue requires at least 10-point type.")

    title_match = re.search(r"\\title\{([^}]*)\}", tex, flags=re.DOTALL)
    if not title_match or len(words(title_match.group(1))) < 3:
        errors.append("Add a specific paper title of at least three words.")
    author_match = re.search(r"\\IEEEauthorblockN\{([^}]*)\}", tex, flags=re.DOTALL)
    if not author_match or not visible_text(author_match.group(1)):
        errors.append("Add at least one author name in an IEEEauthorblockN block.")
    if not re.search(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", tex):
        errors.append("Add a valid contact email to the author block.")

    found_placeholders = [token for token in PLACEHOLDERS if token in raw_tex]
    if found_placeholders:
        errors.append("Unresolved placeholders: " + ", ".join(found_placeholders))

    for description, pattern in FORBIDDEN_LAYOUT_PATTERNS.items():
        if re.search(pattern, tex):
            errors.append(f"Template-bypassing layout command found: {description}.")

    abstract = environment_content(tex, "abstract")
    if abstract is None:
        errors.append("Missing abstract environment.")
    else:
        abstract_words = words(abstract)
        if len(abstract_words) < 50:
            errors.append(f"Abstract is incomplete ({len(abstract_words)} words; expected at least 50).")
        if len(abstract_words) > 500:
            errors.append(f"Abstract exceeds the 500-word venue limit ({len(abstract_words)} words).")
        elif len(abstract_words) > 250:
            warnings.append(f"Abstract is long for a five-page paper ({len(abstract_words)} words).")

    keyword_block = environment_content(tex, "IEEEkeywords")
    if keyword_block is None:
        errors.append("Missing IEEEkeywords environment.")
    else:
        keyword_text = visible_text(keyword_block)
        keyword_count = len([part for part in keyword_text.split(",") if part.strip()])
        if keyword_count < 3:
            errors.append(f"Add at least three specific keywords (found {keyword_count}).")
        elif keyword_count > 8:
            warnings.append(f"Keyword list is unusually long ({keyword_count} entries).")

    sections = section_contents(tex)
    normalized_titles = [title.lower() for title, _ in sections]
    for description, pattern in REQUIRED_SECTION_PATTERNS.items():
        if not any(re.search(pattern, title) for title in normalized_titles):
            errors.append(f"Missing a section covering {description}.")
    for title, content in sections:
        count = len(words(content))
        if count < 10:
            errors.append(f"Section '{title}' is empty or incomplete ({count} visible words).")

    body_word_count = sum(len(words(content)) for _, content in sections)
    if body_word_count < 1200:
        warnings.append(
            f"Body contains only {body_word_count} visible words; confirm that figures and tables provide enough substance."
        )

    cited: set[str] = set()
    for match in re.finditer(r"\\cite\w*\{([^}]+)\}", tex):
        cited.update(key.strip() for key in match.group(1).split(",") if key.strip())
    defined = set(re.findall(r"@\w+\s*\{\s*([^,\s]+)\s*,", bib))
    if not cited:
        errors.append("The manuscript contains no citations.")
    if cited and not re.search(r"\\bibliography\{[^}]+\}", tex):
        errors.append("The manuscript has citations but no bibliography command.")
    missing_citations = sorted(cited - defined)
    if missing_citations:
        errors.append("Citations missing from references.bib: " + ", ".join(missing_citations))
    unused = sorted(defined - cited)
    if unused:
        warnings.append("Unused bibliography entries: " + ", ".join(unused))

    expanded_tex = tex
    for raw in re.findall(r"\\input\{([^}]+)\}", tex):
        input_path = PAPER_DIR / raw
        if not input_path.suffix:
            input_path = input_path.with_suffix(".tex")
        if input_path.exists():
            expanded_tex += "\n" + remove_comments(input_path.read_text(encoding="utf-8"))

    labels = re.findall(r"\\label\{([^}]+)\}", expanded_tex)
    duplicate_labels = sorted(label for label, count in Counter(labels).items() if count > 1)
    if duplicate_labels:
        errors.append("Duplicate LaTeX labels: " + ", ".join(duplicate_labels))
    referenced = set(re.findall(r"\\(?:ref|eqref)\{([^}]+)\}", expanded_tex))
    missing_labels = sorted(referenced - set(labels))
    if missing_labels:
        errors.append("References to undefined labels: " + ", ".join(missing_labels))

    for raw in re.findall(r"\\input\{([^}]+)\}", tex):
        if not resolve_latex_asset(raw, (".tex",)):
            errors.append(f"Missing input file: {raw}")
    for raw in re.findall(r"\\includegraphics(?:\[[^]]*\])?\{([^}]+)\}", tex):
        if not resolve_latex_asset(raw, (".pdf", ".png", ".jpg", ".jpeg", ".eps")):
            errors.append(f"Missing figure asset: {raw}")

    prose = visible_text("\n".join(content for _, content in sections))
    first_person = sorted(set(re.findall(r"\b(?:I|we|our|ours|us)\b", prose, flags=re.IGNORECASE)))
    if first_person:
        warnings.append(
            "Latest published URTC guidance requests third-person writing; review: "
            + ", ".join(first_person)
        )

    checklist_items = re.findall(
        r"^\s*-\s*\[([ xX])\]\s+(.+)$",
        checklist,
        flags=re.MULTILINE,
    )
    if CHECKLIST.exists() and len(checklist_items) < 8:
        errors.append("Manual submission checklist is incomplete or malformed.")
    unchecked = [label for state, label in checklist_items if not state.strip()]
    if unchecked:
        errors.append(f"Manual submission checklist has {len(unchecked)} unchecked item(s).")

    return errors, warnings


def main() -> int:
    errors, warnings = run_checks()
    for message in warnings:
        print(f"WARN {message}")
    for message in errors:
        print(f"FAIL {message}")
    if errors:
        print(f"Paper source is not submission-ready: {len(errors)} error(s), {len(warnings)} warning(s).")
        return 1
    print(f"Paper source checks passed with {len(warnings)} warning(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
