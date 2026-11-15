"""README.md follows the ecosystem README template (engineering-standards readme-check v1).

The check below is copied from the ``readme`` job of engineering-standards
``.github/workflows/docs.yml`` (v1) so the template is enforced offline as well as in the docs
profile. Keep it identical to the shared block; change the shared check first.
"""

import re
from pathlib import Path

MIN_LINES = 80
MAX_LINES = 180

# Required level-2 headings in order; alternatives are separated by "|" (template 14.1).
REQUIRED = [
    "Why",
    "Highlights",
    "Architecture",
    "Quickstart",
    "Usage|Demo*|Where it runs*",
    "Quality",
    "Documentation",
    "Ecosystem",
    "Contributing and security",
    "Scope and limits",
    "License",
]

ECOSYSTEM_TABLE = """\
| Repository | Role |
|---|---|
| [portfolio](https://github.com/gonzalomartinperez/portfolio) | Public bilingual portfolio site |
| [portfolio-assistant-api](https://github.com/gonzalomartinperez/portfolio-assistant-api) | Portfolio assistant API (RAG, evals) |
| [portfolio-backoffice](https://github.com/gonzalomartinperez/portfolio-backoffice) | Portfolio backoffice (IAM, operations) |
| [pequeverso](https://github.com/gonzalomartinperez/pequeverso) | Pequeverso public store site |
| [pequeverso-assistant-api](https://github.com/gonzalomartinperez/pequeverso-assistant-api) | Pequeverso shopping assistant API |
| [pequeverso-backoffice](https://github.com/gonzalomartinperez/pequeverso-backoffice) | Pequeverso backoffice (IAM, operations) |
| vps-ops (private) | Operations CLI and deploy contract |
"""


def heading_matches(heading, spec):
    for alt in spec.split("|"):
        if alt.endswith("*") and heading.lower().startswith(alt[:-1].lower()):
            return True
        if heading.lower() == alt.lower():
            return True
    return False


def check(text, min_lines, max_lines):
    errors = []
    lines = text.splitlines()
    if not min_lines <= len(lines) <= max_lines:
        errors.append(f"README has {len(lines)} lines; expected {min_lines}-{max_lines}")
    in_code, headings = False, []
    for line in lines:
        if line.startswith("```"):
            in_code = not in_code
        elif not in_code and line.startswith("## "):
            headings.append(line[3:].strip())
    pos = 0
    for spec in REQUIRED:
        found = next(
            (i for i in range(pos, len(headings)) if heading_matches(headings[i], spec)),
            None,
        )
        if found is None:
            errors.append(f"missing or out-of-order heading: ## {spec.split('|')[0].rstrip('*')}")
        else:
            pos = found + 1
    badges = len(re.findall(r'<img[^>]*alt=["\'](CI|Release|License)["\']', text, re.IGNORECASE))
    badges += len(
        re.findall(
            r"!\[[^\]]*\]\(https://(img\.shields\.io|github\.com/[^)]*/badge\.svg)",
            text,
        )
    )
    if badges > 3:
        errors.append(f"{badges} badges; at most 3 (CI, release, license)")
    if re.search(r"\bTODO\b", text):
        errors.append("README contains TODO")
    for img in re.findall(r"<img\b[^>]*>", text, re.IGNORECASE):
        if not re.search(r"\balt=", img):
            errors.append(f"image without alt attribute: {img[:60]}")
    return errors


def test_readme_matches_the_ecosystem_template():
    text = Path("README.md").read_text(encoding="utf-8")
    assert check(text, MIN_LINES, MAX_LINES) == []


def test_ecosystem_table_is_the_shared_standard():
    assert ECOSYSTEM_TABLE in Path("README.md").read_text(encoding="utf-8")


def test_check_rejects_a_missing_heading_and_a_todo():
    text = "\n".join(f"## {spec.split('|')[0]}" for spec in REQUIRED[1:]) + "\nTODO"
    errors = check(text, 1, 100)
    assert "missing or out-of-order heading: ## Why" in errors
    assert "README contains TODO" in errors


def test_check_rejects_images_without_alt_and_a_fourth_badge():
    badges = '<img alt="CI" src="a"><img alt="Release" src="b"><img alt="License" src="c">'
    errors = check(f'{badges}\n![x](https://img.shields.io/y)\n<img src="z">', 1, 100)
    assert any(error.startswith("4 badges") for error in errors)
    assert any(error.startswith("image without alt") for error in errors)
