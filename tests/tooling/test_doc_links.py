"""Every relative link and heading anchor in tracked Markdown resolves (M3-2 link check).

`evals/corpus/` is excluded: it is a frozen copy of the portfolio repository's own files, whose
relative links point inside that repository.
"""

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXCLUDED = ("evals/corpus/",)
LINK = re.compile(r'!?\[[^\]]*\]\(\s*<?([^)\s>]+)>?(?:\s+"[^"]*")?\)')
REFERENCE = re.compile(r"^\s*\[[^\]]+\]:\s*(\S+)", re.MULTILINE)
ATTRIBUTE = re.compile(r'(?:src|href|srcset)="([^"]+)"')
EXTERNAL = re.compile(r"(https?:|mailto:|data:)")


def slug(heading: str) -> str:
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", heading)
    text = re.sub(r"<[^>]+>", "", text.replace("`", "").strip().lower())
    return re.sub(r"[^\w\- ]", "", text).replace(" ", "-")


def anchors(path: Path) -> set[str]:
    found: set[str] = set()
    seen: dict[str, int] = {}
    in_code = False
    for line in path.read_text(errors="ignore").splitlines():
        if line.startswith("```"):
            in_code = not in_code
        match = None if in_code else re.match(r"#{1,6}\s+(.*?)\s*#*$", line)
        if match:
            name = slug(match.group(1))
            count = seen.get(name, 0)
            seen[name] = count + 1
            found.add(name if count == 0 else f"{name}-{count}")
    return found


def markdown_files() -> list[Path]:
    tracked = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "*.md"], check=True, capture_output=True, text=True
    ).stdout.splitlines()
    return [ROOT / name for name in tracked if not name.startswith(EXCLUDED)]


def broken_links(path: Path) -> list[str]:
    text = re.sub(r"```.*?```", "", path.read_text(errors="ignore"), flags=re.DOTALL)
    text = re.sub(r"`[^`\n]*`", "", text)
    links = LINK.findall(text) + REFERENCE.findall(text) + ATTRIBUTE.findall(text)
    problems = []
    for link in links:
        if EXTERNAL.match(link):
            continue
        target_part, _, anchor = link.partition("#")
        target = path if not target_part else (path.parent / target_part).resolve()
        if not target.exists():
            problems.append(f"{path.relative_to(ROOT)}: {link} (missing)")
        elif anchor and target.suffix == ".md" and anchor.lower() not in anchors(target):
            problems.append(f"{path.relative_to(ROOT)}: {link} (anchor)")
    return problems


def test_relative_links_and_anchors_resolve():
    problems = [problem for path in markdown_files() for problem in broken_links(path)]
    assert problems == []
