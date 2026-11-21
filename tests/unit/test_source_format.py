"""Pin the conservative TypeScript fact extraction, including line spans and caps."""

from portfolio_assistant.adapters.portfolio.source_format import facts, facts_for
from portfolio_assistant.domain.graph import Fact

PROJECTS = """export const projects = [
  {
    slug: "alpha",
    name: "Alpha",
    stack: technologyNames(["Python", "Rust"]),
    contributions: ["Built the parser", "Wrote docs"],
  },
  {
    slug: "nameless",
    other: "x",
  },
  {
    slug: "beta",
    name: "Beta",
  },
];
"""
EXPERIENCE = """export const experience = [
  {
    slug: "one",
    company: "Rampy",
    stack: technologyNames(["Go"]),
    contributions: ["Shipped it"],
  },
];
"""
EDUCATION = """export const education = [
  {
    qualification: "BSc Computing",
    institution: "Some University",
  },
];
"""
DOC = "src/data/projects.ts"


def test_projects_extract_stack_contributions_and_identity_in_order() -> None:
    assert facts(DOC, PROJECTS) == (
        Fact("Project", "Alpha", "USES", "Technology", "Python", 4, 5),
        Fact("Project", "Alpha", "USES", "Technology", "Rust", 4, 5),
        Fact("Project", "Alpha", "CONTRIBUTED", "Contribution", "Built the parser", 4, 6),
        Fact("Project", "Alpha", "CONTRIBUTED", "Contribution", "Wrote docs", 4, 6),
        Fact("Project", "Alpha", "DOCUMENTED_IN", "PublicDocument", DOC, 4, 4),
        Fact("Project", "Beta", "DOCUMENTED_IN", "PublicDocument", DOC, 14, 14),
    )


def test_experience_uses_company_and_has_no_identity_fact() -> None:
    assert facts("src/data/experience.ts", EXPERIENCE) == (
        Fact("Role", "Rampy", "USES", "Technology", "Go", 4, 5),
        Fact("Role", "Rampy", "CONTRIBUTED", "Contribution", "Shipped it", 4, 6),
    )


def test_education_returns_single_institution_fact() -> None:
    assert facts("src/data/education.ts", EDUCATION) == (
        Fact(
            "Education", "BSc Computing", "AT_INSTITUTION", "Institution", "Some University", 3, 4
        ),
    )


def test_unmatched_education_unknown_path_and_missing_slugs_are_empty() -> None:
    assert facts("src/data/education.ts", "nothing") == ()
    assert facts("src/data/other.ts", PROJECTS) == ()
    assert facts(DOC, "no slugs") == ()


def test_education_only_matches_within_the_bounded_window() -> None:
    far = 'qualification: "Q",' + " " * 300 + 'institution: "I"'
    assert facts("x/education.ts", far) == ()


def test_slug_blocks_are_capped_at_twenty() -> None:
    content = "\n".join(f'{{ slug: "s{i}", name: "N{i}" }}' for i in range(22))
    result = facts("a/projects.ts", content)
    assert len(result) == 20
    assert result[-1] == Fact(
        "Project", "N19", "DOCUMENTED_IN", "PublicDocument", "a/projects.ts", 20, 20
    )


def test_contributions_are_capped_at_twenty() -> None:
    items = ", ".join(f'"item{i}"' for i in range(22))
    result = facts("a/experience.ts", f'{{ slug: "c", company: "C", contributions: [{items}] }}')
    assert len(result) == 20
    assert result[-1] == Fact("Role", "C", "CONTRIBUTED", "Contribution", "item19", 1, 1)


def test_facts_for_maps_every_document() -> None:
    assert facts_for({DOC: PROJECTS, "other.txt": "x"}) == {
        DOC: facts(DOC, PROJECTS),
        "other.txt": (),
    }
