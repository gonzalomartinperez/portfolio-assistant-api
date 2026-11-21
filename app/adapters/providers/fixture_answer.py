import re
from dataclasses import dataclass, field

from app.domain.evidence import (
    ALIASES,
    asks_spoken_languages,
    requested_affiliation,
    tokens,
)
from app.domain.messages import insufficient_message


def metric_excerpts(content: str) -> list[str]:
    """Keep metric value, label and qualification together for output and attribution."""
    content = re.sub(r'"\s*\+\s*"', "", content)
    return [
        f"{label}: {value}. {qualifier}"
        for value, label, qualifier in re.findall(
            r'value:\s*"([^"\n]+)",\s*label:\s*"([^"\n]+)",\s*qualifier:\s*"([^"\n]+)"',
            content,
        )
    ]


def language_excerpts(content: str) -> list[str]:
    return [
        f"{language}: {level}"
        for language, level in re.findall(
            r'language:\s*"([^"\n]{1,100})",\s*level:\s*"([^"\n]{1,100})"', content
        )
    ]


def fixture_supports(content: str, answer: str, path: str) -> bool:
    """Match emitted deterministic excerpts, including short qualified metrics."""
    content = re.sub(r'"\s*\+\s*"', "", content)
    if any(text in answer for text in language_excerpts(content)):
        return True
    if any(text in answer for text in metric_excerpts(content)):
        return True
    if any(text in answer for text in re.findall(r'"([^"\n]{25,})"', content)):
        return True
    if any(label in answer for label in ("Documented technologies:", "Tecnologías documentadas:")):
        for stack in re.findall(r"technologyNames\(\[([^]]+)", content, re.DOTALL):
            names = re.findall(r'"([^"\n]+)"', stack)[:20]
            if names and ", ".join(names) in answer:
                return True
    return path == "README.md" and any(
        line.strip() in answer for line in content.splitlines() if len(line.strip()) > 40
    )


_REPEAT_REQUEST = re.compile(
    r"(?i)^\s*(?:repeat\s+generation\s+automatically|repite\s+(?:autom[aá]ticamente\s+)?(?:la\s+)?generaci[oó]n\s+autom[aá]ticamente)"
)
_COMPARISON_TERMS = {"compare", "comparison", "versus", "compara", "comparar", "between", "entre"}
_TECHNOLOGY_TERMS = {"technologies", "technology", "tecnologias", "stack"}
_METRIC_TERMS = {"performance", "improvements", "metrics", "metricas", "rendimiento"}
_PROFILE_QUESTION = re.compile(
    r"(?i)(tell me about|cu[eé]ntame sobre|who is|qui[eé]n es)\s+gonzalo"
)
_UNSAFE_PART = re.compile(r"(?i)https?://|ignore .*instructions|reveal .*secret|you are now")
_UNSAFE_QUOTE = re.compile(
    r"(?i)ignore (all |previous |prior )?instructions|reveal (the |your )?(system prompt|secret|api key)|you are now"
)


@dataclass
class _Scan:
    """Question-derived settings and the excerpts gathered across public source blocks."""

    question: str
    locale: str
    terms: set[str]
    expanded: set[str]
    concise: bool
    comparison: bool
    excerpts: list[str] = field(default_factory=list)
    subject: str = ""


def fixture_message(question: str, evidence: str, locale: str) -> str:
    # A deterministic excerpt viewer, not a model-quality simulation.
    insufficient = insufficient_message(locale)
    if not evidence:
        return _no_evidence_message(question, locale, insufficient)
    if "PUBLIC SOURCE " in evidence:
        return _public_source_message(question, evidence, locale, insufficient)
    return _quoted_message(question, evidence, locale, insufficient)


def _no_evidence_message(question: str, locale: str, insufficient: str) -> str:
    if not _REPEAT_REQUEST.search(question):
        return insufficient
    return (
        "No reintento generaciones automáticamente. Puedes volver a enviar la consulta de forma explícita; una nueva generación puede tener costo."
        if locale == "es"
        else "I don't retry generations automatically. You can explicitly submit the question again; a new generation may incur a cost."
    )


def _public_source_message(question: str, evidence: str, locale: str, insufficient: str) -> str:
    terms = tokens(question)
    scan = _Scan(
        question,
        locale,
        terms,
        terms | set().union(*(ALIASES.get(term, set()) for term in terms)),
        bool(terms & {"shorter", "brief", "breve"}),
        bool(terms & _COMPARISON_TERMS),
    )
    for block in evidence.split("PUBLIC SOURCE ")[1:3]:
        if _scan_block(scan, block):
            break
    if not scan.excerpts:
        return insufficient
    # Quotes preserve first-person attribution and qualifications from the source.
    heading = (
        "El perfil público lo describe así (extractos en modo de prueba):"
        if locale == "es"
        else "The public profile describes it this way (fixture excerpts):"
    )
    if scan.subject:
        heading += " " + scan.subject + "."
    shown = scan.excerpts[: 1 if scan.concise else 2]
    return heading + "\n\n" + "\n\n".join("> " + text for text in shown)


def _scan_block(scan: _Scan, block: str) -> bool:
    """Add the block's excerpts to the scan; return True when the scan should stop."""
    content = re.sub(r"/\*.*?\*/", "", block, flags=re.DOTALL)
    content = re.sub(r"^\s*(?:availability|seniority):.*$", "", content, flags=re.MULTILINE)
    selected = _requested_company_record(scan, content)
    if selected is None:
        return False
    # Join only literal concatenations; never evaluate source code.
    content = re.sub(r'"\s*\+\s*"', "", selected)
    if not scan.excerpts:
        names = re.findall(r'(?:name|company|tagline):\s*"([^"\n]{1,120})"', content)
        scan.subject = " — ".join(names[:2])
    special = _special_excerpts(scan, block, content)
    if special is not None:
        scan.excerpts.extend(special[0])
        return special[1]
    for text in _ranked_excerpts(scan, content):
        if text not in scan.excerpts:
            scan.excerpts.append(text)
    return False


def _requested_company_record(scan: _Scan, content: str) -> str | None:
    """Narrow to the requested employer's record, or None when that employer is absent."""
    affiliation = requested_affiliation(scan.question)
    companies = list(re.finditer(r'company:\s*"([^"\n]+)"', content))
    if not affiliation or scan.comparison or not companies:
        return content
    selected_company = next(
        (
            index
            for index, company in enumerate(companies)
            if tokens(affiliation) <= tokens(company[1])
        ),
        None,
    )
    if selected_company is None:
        return None
    # Fixed source spans can begin with the previous employer's metrics.
    # Quote only the requested record when its company boundary is visible.
    start = companies[selected_company].start()
    end = (
        companies[selected_company + 1].start()
        if selected_company + 1 < len(companies)
        else len(content)
    )
    return content[start:end]


def _special_excerpts(scan: _Scan, block: str, content: str) -> tuple[list[str], bool] | None:
    """Topic-specific excerpts and whether to stop scanning; None falls back to ranking."""
    terms = scan.terms
    if asks_spoken_languages(terms):
        languages = language_excerpts(content)
        return (["; ".join(languages)] if languages else []), False
    technologies = _technology_excerpt(scan, content)
    if technologies:
        return [technologies], False
    first_line = block.splitlines()[0]
    if first_line.startswith("README.md"):
        return _readme_excerpts(scan, content), False
    if _PROFILE_QUESTION.search(scan.question) and "/profile.ts" in first_line:
        return re.findall(r'(?:intro|summary):\s*"([^"\n]+)"', content)[:2], True
    if terms & _METRIC_TERMS:
        metrics = metric_excerpts(content)
        if metrics:
            return metrics[:2], True
    return None


def _technology_excerpt(scan: _Scan, content: str) -> str | None:
    if not scan.terms & _TECHNOLOGY_TERMS:
        return None
    stacks = re.findall(r"technologyNames\(\[([^]]*)", content, re.DOTALL)
    technologies = [name for stack in stacks for name in re.findall(r'"([^"\n]+)"', stack)]
    if not technologies:
        return None
    label = "Tecnologías documentadas: " if scan.locale == "es" else "Documented technologies: "
    return label + ", ".join(technologies[:20]) + "."


def _readme_excerpts(scan: _Scan, content: str) -> list[str]:
    prose = [
        line.strip()
        for line in content.splitlines()[1:]
        if len(line.strip()) > 40 and not line.startswith(("#", "```"))
    ]
    ranked_prose = sorted(prose, key=lambda line: -len(tokens(line) & scan.expanded))
    return ranked_prose[: 1 if scan.concise else 2]


def _ranked_excerpts(scan: _Scan, content: str) -> list[str]:
    candidates = [
        part for part in re.findall(r'"([^"\n]{25,})"', content) if not _UNSAFE_PART.search(part)
    ]
    ranked = sorted(
        enumerate(candidates),
        key=lambda item: (-len(tokens(item[1]) & scan.expanded), item[0]),
    )
    return [text for _, text in ranked[: 1 if scan.concise or scan.comparison else 2]]


def _quoted_message(question: str, evidence: str, locale: str, insufficient: str) -> str:
    keywords = query_terms(question)
    quoted = [
        part.strip()
        for part in re.findall(r'"([^"\n]{25,})"', evidence)
        if not part.startswith(("http:", "https:"))
        and "github.com/" not in part
        and not _UNSAFE_QUOTE.search(part)
    ]
    matching = [part for part in quoted if any(word in part.lower() for word in keywords)]
    excerpts = (matching or (quoted if "filomena" in question.lower() else []))[:3]
    if not excerpts:
        return insufficient
    heading = (
        "Resultado de prueba basado en fragmentos públicos:"
        if locale == "es"
        else "Fixture result from public source excerpts:"
    )
    return heading + "\n\n" + "\n".join(f"• {part[:250]}" for part in excerpts)


def query_terms(question: str) -> set[str]:
    stop = {
        "about",
        "could",
        "does",
        "donde",
        "estoy",
        "explain",
        "hacer",
        "please",
        "portfolio",
        "puedes",
        "sobre",
        "their",
        "these",
        "those",
        "where",
        "which",
        "would",
        "tell",
        "what",
    }
    return {
        word for word in re.findall(r"\w+", question.lower()) if len(word) >= 5 and word not in stop
    }
