"""The activation tool's prompt, parsing, scoring and merge logic run without the CLI."""

import json
import subprocess

import pytest
import yaml

from scripts import skill_activation_eval as tool
from tests.support import ROOT

CATALOG = {
    "write-adr": "Writes a decision record. Not for changelogs.",
    "review-change": "Reviews a diff. Not for fixes.",
}


def test_prompt_lists_every_skill_and_the_query():
    prompt = tool.build_prompt(CATALOG, "Record this decision")
    assert "- write-adr: Writes a decision record. Not for changelogs." in prompt
    assert "- review-change: Reviews a diff. Not for fixes." in prompt
    assert "Request: Record this decision" in prompt
    assert "`none`" in prompt


@pytest.mark.parametrize(
    ("answer", "expected"),
    [
        ("write-adr", "write-adr"),
        ("  `Review-Change`\n", "review-change"),
        ("I would load **write-adr** here.", "write-adr"),
        ("none", "none"),
        ("None - nothing applies", "none"),
        ("write-adr-extra", "none"),
        ("something else entirely", "none"),
        ("", "none"),
    ],
)
def test_parse_answer(answer, expected):
    assert tool.parse_answer(answer, list(CATALOG)) == expected


def test_parse_prefers_the_longest_matching_name():
    names = ["api-change", "api-change-stream"]
    assert tool.parse_answer("api-change-stream", names) == "api-change-stream"


@pytest.mark.parametrize(
    ("should_trigger", "share", "passed"),
    [
        (True, 1.0, True),
        (True, 0.5, True),
        (True, 0.34, False),
        (False, 0.0, True),
        (False, 0.34, True),
        (False, 0.5, False),
    ],
)
def test_pass_rule_uses_the_half_threshold(should_trigger, share, passed):
    assert tool.judge(should_trigger, share) is passed


def queries():
    return [
        {"query": "a", "should_trigger": True, "split": "validation"},
        {"query": "b", "should_trigger": True, "split": "validation"},
        {"query": "c", "should_trigger": False, "split": "validation"},
        {"query": "d", "should_trigger": False, "split": "validation"},
        {"query": "e", "should_trigger": True, "split": "train"},
    ]


def test_scoring_reports_precision_recall_and_accuracy_per_split():
    picks = {
        "a": ["s", "s", "s"],
        "b": ["x", "none", "s"],
        "c": ["s", "s", "x"],
        "d": ["x", "x", "x"],
        "e": ["none"] * 3,
    }
    scored = tool.score_skill("s", queries(), picks)
    validation = scored["splits"]["validation"]
    assert (validation["tp"], validation["fn"]) == (1, 1)
    assert (validation["fp"], validation["tn"]) == (1, 1)
    assert validation["precision"] == 0.5
    assert validation["recall"] == 0.5
    assert validation["accuracy"] == 0.5
    assert scored["splits"]["train"]["recall"] == 0.0
    assert [row["passed"] for row in scored["queries"]] == [
        True,
        False,
        False,
        True,
        False,
    ]


def test_empty_denominators_are_none_not_a_crash():
    empty = tool.summarize([])
    assert empty["precision"] is None
    assert empty["recall"] is None
    assert empty["accuracy"] is None


def test_overall_pools_counts_of_all_skills():
    row = {"should_trigger": True, "triggered_fraction": 1.0, "split": "validation"}
    skills = {
        "a": {"queries": [row]},
        "b": {"queries": [{**row, "triggered_fraction": 0}]},
    }
    pooled = tool.overall(skills, "validation")
    assert (pooled["tp"], pooled["fn"], pooled["queries"]) == (1, 1, 2)


def test_merge_keeps_first_and_replaces_final():
    first = {"splits": {"validation": {"accuracy": 0.5}}}
    second = {"splits": {"validation": {"accuracy": 0.9}}}
    existing = {
        "skills": {
            "a": {"first": first, "final": first},
            "b": {"first": first, "final": first},
        }
    }
    fresh = {"generated": "now", "skills": {"a": {"first": second, "final": second}}}
    merged = tool.merge(existing, fresh)
    assert merged["generated"] == "now"
    assert merged["skills"]["a"] == {"first": first, "final": second}
    assert merged["skills"]["b"]["final"] == first


def test_merge_without_a_previous_file_uses_the_new_numbers_twice():
    fresh = {"skills": {"a": {"first": 1, "final": 1}}}
    assert tool.merge(None, fresh)["skills"]["a"] == {"first": 1, "final": 1}


def test_table_shows_first_and_final_and_an_overall_row():
    empty_split = {"validation": {"accuracy": 0.5, "precision": 1.0, "recall": None, "queries": 2}}
    final_split = {"validation": {"accuracy": 1.0, "precision": 1.0, "recall": 1.0, "queries": 2}}
    results = {
        "skills": {
            "a": {
                "first": {"splits": empty_split, "queries": []},
                "final": {"splits": final_split, "queries": []},
            }
        }
    }
    text = tool.table(results)
    assert "| `a` | 0.50 | 1.00 | 1.00 | 1.00 | 2 |" in text
    assert "**overall**" in text


def test_real_catalog_frontmatter_matches_the_yaml_parser():
    catalog = tool.load_catalog()
    assert len(catalog) >= 12
    for name, description in catalog.items():
        data = yaml.safe_load(
            (ROOT / ".agents/skills" / name / "SKILL.md").read_text().split("---")[1]
        )
        assert data["name"] == name
        assert data["description"] == description


def test_every_skill_ships_well_formed_trigger_queries():
    for name in tool.load_catalog():
        items, runs = tool.load_queries(name)
        assert runs == 3
        assert 10 <= len(items) <= 30
        for split in tool.SPLITS:
            chosen = [i for i in items if i["split"] == split]
            assert any(i["should_trigger"] for i in chosen), (name, split)
            assert any(not i["should_trigger"] for i in chosen), (name, split)
        validation = sum(i["split"] == "validation" for i in items)
        assert 0.3 <= validation / len(items) <= 0.5, name


def test_every_skill_ships_output_evals_with_assertions():
    for name in tool.load_catalog():
        path = ROOT / ".agents/skills" / name / "evals/evals.json"
        data = json.loads(path.read_text())
        assert data["skill"] == name
        assert len(data["evals"]) >= 3
        assert all(e["prompt"] and e["assertions"] for e in data["evals"])


def test_dry_run_prints_a_prompt_and_calls_no_router(monkeypatch, capsys):
    def forbidden(*args, **kwargs):
        raise AssertionError("router must not run in a dry run")

    monkeypatch.setattr(tool, "ask_router", forbidden)
    with pytest.raises(SystemExit) as exit_info:
        tool.main(["--dry-run", "--skills", "write-adr"])
    assert exit_info.value.code == 0
    shown = capsys.readouterr().out
    assert "- write-adr:" in shown
    assert "Request:" in shown


def test_run_scores_with_a_fake_router(monkeypatch, tmp_path):
    monkeypatch.setattr(tool, "ask_router", lambda prompt: "write-adr")
    out = tmp_path / "result.json"
    assert tool.main(["--skills", "write-adr", "--runs", "1", "--out", str(out)]) == 0
    saved = json.loads(out.read_text())
    entry = saved["skills"]["write-adr"]
    assert entry["first"] == entry["final"]
    validation = entry["final"]["splits"]["validation"]
    assert validation["recall"] == 1.0
    assert validation["precision"] < 1.0


def test_router_env_removes_every_anthropic_credential_and_override():
    source = {
        "PATH": "/usr/bin",
        "HOME": "/tmp/home",
        "ANTHROPIC_API_KEY": "k",
        "ANTHROPIC_AUTH_TOKEN": "t",
        "ANTHROPIC_FOO_KEY": "x",
        "ANTHROPIC_BASE_URL": "https://gateway.invalid",
        "CLAUDE_CODE_USE_BEDROCK": "1",
        "CLAUDE_CODE_OAUTH_TOKEN": "subscription",
    }
    cleaned = tool.router_env(source)
    assert cleaned == {
        "PATH": "/usr/bin",
        "HOME": "/tmp/home",
        "CLAUDE_CODE_OAUTH_TOKEN": "subscription",
    }


def test_ask_router_runs_the_cli_without_api_keys(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sentinel-key")
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "sentinel-token")
    seen = {}

    def fake_run(command, **kwargs):
        seen.update(kwargs)
        seen["command"] = command
        return subprocess.CompletedProcess(command, 0, stdout="write-adr\n", stderr="")

    monkeypatch.setattr(tool.subprocess, "run", fake_run)
    assert tool.ask_router("prompt") == "write-adr\n"
    assert not any(name.startswith("ANTHROPIC_") for name in seen["env"])
    assert "sentinel" not in str(seen["env"])
    assert seen["command"][:2] == ("claude", "-p")
    assert seen["input"] == "prompt"


def test_ask_router_retries_a_timeout_then_succeeds(monkeypatch):
    calls = []

    def fake_run(command, **kwargs):
        calls.append(1)
        if len(calls) == 1:
            raise subprocess.TimeoutExpired(command, kwargs["timeout"])
        return subprocess.CompletedProcess(command, 0, stdout="none", stderr="")

    monkeypatch.setattr(tool.subprocess, "run", fake_run)
    assert tool.ask_router("prompt") == "none"
    assert len(calls) == 2


def test_ask_router_returns_error_after_repeated_timeouts(monkeypatch):
    def fake_run(command, **kwargs):
        raise subprocess.TimeoutExpired(command, kwargs["timeout"])

    monkeypatch.setattr(tool.subprocess, "run", fake_run)
    assert tool.ask_router("prompt", attempts=2) == tool.ERROR


@pytest.mark.parametrize(("code", "out"), [(1, "write-adr"), (0, ""), (0, "  \n")])
def test_ask_router_treats_failure_or_empty_output_as_error(monkeypatch, code, out):
    def fake_run(command, **kwargs):
        return subprocess.CompletedProcess(command, code, stdout=out, stderr="boom")

    monkeypatch.setattr(tool.subprocess, "run", fake_run)
    assert tool.ask_router("prompt", attempts=2) == tool.ERROR


def test_failed_calls_are_excluded_from_the_fraction():
    assert tool.fraction([tool.ERROR, "s", "x"], "s") == 0.5
    assert tool.fraction([tool.ERROR, tool.ERROR], "s") is None


def test_a_query_with_only_failed_calls_is_not_scored_as_not_triggered():
    items = [
        {"query": "a", "should_trigger": True, "split": "validation"},
        {"query": "b", "should_trigger": True, "split": "validation"},
    ]
    picks = {"a": [tool.ERROR] * 3, "b": ["s", "s", tool.ERROR]}
    scored = tool.score_skill("s", items, picks)
    summary = scored["splits"]["validation"]
    assert (summary["queries"], summary["errored"]) == (1, 1)
    assert summary["recall"] == 1.0
    assert scored["errors"] == 4
    assert [row["passed"] for row in scored["queries"]] == [None, True]


def test_run_exits_non_zero_and_records_the_error_count(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(tool, "ask_router", lambda prompt: tool.ERROR)
    out = tmp_path / "result.json"
    code = tool.main(["--skills", "write-adr", "--runs", "1", "--out", str(out)])
    assert code == 1
    saved = json.loads(out.read_text())
    validation = saved["skills"]["write-adr"]["final"]["splits"]["validation"]
    assert saved["errors"] == saved["skills"]["write-adr"]["final"]["errors"] > 0
    assert validation["queries"] == 0
    assert validation["errored"] == saved["errors"]
    assert validation["recall"] is None
    assert "router calls failed" in capsys.readouterr().err
