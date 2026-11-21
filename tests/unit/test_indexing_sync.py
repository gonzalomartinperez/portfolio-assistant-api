"""Characterization of the knowledge sync orchestration with recording fakes.

The trace pins the order of SQL statements, transaction boundaries, projection calls and
resource cleanup of `indexing._sync`. Paths that need PostgreSQL or Neo4j for real are
covered by tests/integration/test_knowledge.py and test_index_identity_integration.py.
"""

from contextlib import contextmanager
from threading import Event
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, Literal
from unittest.mock import Mock

import pytest

from app.adapters.portfolio import indexing

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

COMMIT = "a" * 40
README = "# Public fixture\nAn approved synthetic public profile for identity tests."
PROJECTION = '{"facts": [{"a": 1}], "personal": {"b": 2}}'
REMOTE = b"https://github.com/gonzalomartinperez/portfolio.git"
NEO4J_TEST_FIXTURE_VALUE = "fixture"


def _short(sql: str) -> str:
    return sql[:48]


class Harness:
    """Recording fakes for git, PostgreSQL, Neo4j, embeddings and projection."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        self.events: list[Any] = []
        self.tmp_path = tmp_path
        self.files: dict[str, str] = {"README.md": README}
        self.sizes: dict[str, int] = {}
        self.answers: dict[str, Any] = {}
        self.remote = REMOTE
        self.commit = COMMIT.encode()
        self.encode_error: Exception | None = None
        self.stop_after_sql: tuple[str, Event] | None = None
        self.project_error: Exception | None = None
        self.fail_prepare_graph = False
        self.stop_on_client: Event | None = None
        self._install(monkeypatch)

    # -- fakes -------------------------------------------------------------------------
    def _git(self, repo: Path, *args: str) -> bytes:
        self.events.append(("git", args[0]))
        if args[:2] == ("remote", "get-url"):
            return self.remote
        if args[0] == "rev-parse":
            return self.commit
        if args[0] == "ls-tree":
            return "\n".join(
                f"100644 blob {index:040x}\t{path}" for index, path in enumerate(self.files, 1)
            ).encode()
        blob = {f"{index:040x}": path for index, path in enumerate(self.files, 1)}[args[-1]]
        if args[1] == "-s":
            return str(self.sizes.get(blob, len(self.files[blob].encode()))).encode()
        return self.files[blob].encode()

    def _execute(self, sql: str, values: tuple[object, ...] | None = None) -> SimpleNamespace:
        self.events.append(("sql", _short(sql), values))
        if self.stop_after_sql and _short(sql) == self.stop_after_sql[0]:
            self.stop_after_sql[1].set()
        answer = self.answers.get(_short(sql))
        row = answer["row"] if answer else None
        rows = answer["rows"] if answer else []
        if sql.startswith("SELECT count(*)"):
            inserted = sum(
                1
                for e in self.events
                if isinstance(e, tuple) and e[0] == "sql" and e[1] == INSERT_CHUNK
            )
            row = {"n": self.answers.get("count", inserted)}
        return SimpleNamespace(fetchone=lambda: row, fetchall=lambda: rows)

    def _install(self, monkeypatch: pytest.MonkeyPatch) -> None:
        events = self.events
        harness = self

        @contextmanager
        def connection() -> Iterator[SimpleNamespace]:
            events.append("conn_open")
            try:
                yield SimpleNamespace(execute=harness._execute)
            except BaseException as exc:
                events.append(("conn_error", type(exc).__name__))
                raise
            events.append("conn_commit")

        self.connection = connection

        class Encoder:
            provider = "openai"
            model = "text-embedding-3-small"
            dimensions = 1536

            def __init__(self, client: Mock, accounting: str | None) -> None:
                events.append(("encoder", accounting is not None))

            def encode(self, text: str, purpose: str) -> tuple[float, ...]:
                events.append(("encode", purpose))
                if harness.encode_error:
                    raise harness.encode_error
                return (0.5,) * 1536

        client = Mock()
        client.close.side_effect = lambda: events.append("client_close")

        def create_client(**kwargs: object) -> Mock:
            events.append(("client", kwargs))
            if harness.stop_on_client:
                harness.stop_on_client.set()
            return client

        driver = Mock()
        driver.verify_connectivity.side_effect = lambda: events.append("verify")
        driver.close.side_effect = lambda: events.append("driver_close")
        driver.session.return_value.__enter__ = Mock(return_value="SESSION")
        driver.session.return_value.__exit__ = Mock(return_value=False)

        def make_driver(*args: object, **kwargs: object) -> Mock:
            events.append("driver")
            return driver

        def project(
            session: str,
            version: str,
            records: list[dict[str, Any]],
            documents: dict[str, str],
            **kw: object,
        ) -> int:
            events.append(
                ("project", session, version, [r["path"] for r in records], sorted(documents), kw)
            )
            if harness.project_error:
                raise harness.project_error
            return 7

        def prepare_graph(
            drv: Mock, config: indexing.IndexConfiguration, version: str, document_id: str
        ) -> None:
            events.append(("prepare_graph", version, document_id))
            if harness.fail_prepare_graph:
                raise RuntimeError("graph down")

        monkeypatch.setattr(indexing, "git", self._git)
        monkeypatch.setattr(indexing, "OpenAIEmbeddings", Encoder)
        monkeypatch.setattr(indexing, "create_sync_client", create_client)
        monkeypatch.setattr(indexing, "EmbeddingAccounting", lambda *args: "ACCOUNTING")
        monkeypatch.setattr(indexing.GraphDatabase, "driver", make_driver)
        monkeypatch.setattr(indexing, "project", project)
        monkeypatch.setattr(indexing, "prepare_graph", prepare_graph)
        monkeypatch.setattr(indexing, "facts_for", lambda documents: "FACTS_FOR")

        def graph_facts(structured: str, documents: dict[str, str]) -> str:
            events.append(("graph_facts", sorted(documents)))
            return "GRAPH_FACTS"

        monkeypatch.setattr(indexing, "graph_facts", graph_facts)
        monkeypatch.setattr(
            indexing.PublicProjection, "model_validate_json", lambda content: "STRUCTURED"
        )

    # -- driving -----------------------------------------------------------------------
    def run(
        self,
        provider: Literal["fixture", "openai"] = "fixture",
        *,
        watched: bool = False,
        stop: Event | None = None,
        snapshot: bool = False,
    ) -> dict[str, Any]:
        configuration = SimpleNamespace(
            embeddings_provider=provider,
            openai_api_key=None,
            reserve_cutoff_usd="1",
            embedding_usd_per_million="0.02",
            neo4j_uri="bolt://fixture.invalid",
            neo4j_user="fixture",
            neo4j_password=NEO4J_TEST_FIXTURE_VALUE,
            neo4j_database="neo4jdb",
        )
        return indexing._sync(
            self.tmp_path,
            "HEAD",
            configuration=configuration,
            connection=self.connection,
            watched=watched,
            stop=stop,
            snapshot=snapshot,
        )

    def sql(self) -> list[str]:
        return [event[1] for event in self.events if isinstance(event, tuple) and event[0] == "sql"]


@pytest.fixture
def harness(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Harness:
    return Harness(monkeypatch, tmp_path)


def kinds(harness: Harness) -> list[Any]:
    """Event trace with bulky payloads reduced to their kind."""
    out: list[Any] = []
    for event in harness.events:
        if isinstance(event, tuple) and event[0] == "sql":
            out.append(event[1])
        elif isinstance(event, tuple) and event[0] == "project":
            out.append(("project", event[1], event[2], event[3], event[4], event[5]))
        else:
            out.append(event)
    return out


INSERT_VERSION = "INSERT INTO knowledge_versions(id,status,source_commit) VALUES"[:48]
SELECT_STATUS = "SELECT status FROM knowledge_versions WHERE id=%s"[:48]
SELECT_ACTIVE = "SELECT id FROM knowledge_versions WHERE status='active' ORDER"[:48]
SELECT_COUNT = "SELECT count(*) AS n FROM chunks WHERE knowledge_version=%s"[:48]
UPDATE_PROVIDER = "UPDATE knowledge_versions SET embedding_provider=%s,embedding_model"[:48]
DELETE_CHUNKS = "DELETE FROM chunks WHERE knowledge_version=%s"[:48]
DELETE_FILES = "DELETE FROM source_files WHERE knowledge_version=%s"[:48]
INSERT_FILE = "INSERT INTO source_files(knowledge_version,path,blob_sha,sha256"[:48]
INSERT_CHUNK = "INSERT INTO chunks(id,knowledge_version,content,title,url"[:48]
RETIRE = "UPDATE knowledge_versions SET status='retired' WHERE status='active'"[:48]
ACTIVATE = "UPDATE knowledge_versions SET status='active' WHERE id=%s"[:48]
CACHE_SELECT = "SELECT embedding AS semantic_embedding FROM public_embedding_cache"[:48]
CACHE_INSERT = "INSERT INTO public_embedding_cache(content_hash,provider,model"[:48]
WATCH = "SELECT observed_commit FROM knowledge_watch WHERE singleton FOR UPDATE"[:48]
CHUNK_DOC = "SELECT id FROM chunks WHERE knowledge_version=%s LIMIT 1"[:48]
OLD_FILES = "SELECT * FROM source_files WHERE knowledge_version=%s"[:48]
OLD_CHUNKS = "SELECT * FROM chunks WHERE knowledge_version=%s AND path=%s"[:48]


def test_fixture_sync_trace_and_result(harness: Harness) -> None:
    result = harness.run()
    version = result["knowledge_version"]
    assert version == indexing.corpus_identity(COMMIT, "fixture")[0]
    record = result["manifest"][0]
    assert result == {
        "knowledge_version": version,
        "source_commit": COMMIT,
        "changed": True,
        "files": 1,
        "chunks": 1,
        "embedded_chunks": 1,
        "reused_files": 0,
        "manifest": [record],
        "graph_facts": 7,
    }
    assert record["path"] == "README.md"
    assert record["bytes"] == len(README)
    assert kinds(harness) == [
        ("git", "remote"),
        ("git", "rev-parse"),
        ("git", "ls-tree"),
        "conn_open",
        SELECT_STATUS,
        SELECT_ACTIVE,
        "conn_commit",
        ("git", "cat-file"),
        ("git", "cat-file"),
        "conn_open",
        INSERT_VERSION,
        UPDATE_PROVIDER,
        DELETE_CHUNKS,
        DELETE_FILES,
        INSERT_FILE,
        INSERT_CHUNK,
        "conn_commit",
        "driver",
        "verify",
        (
            "project",
            "SESSION",
            version,
            ["README.md"],
            ["README.md"],
            {"explicit_facts": "FACTS_FOR"},
        ),
        ("prepare_graph", version, _chunk_id(harness)),
        "driver_close",
        "conn_open",
        SELECT_COUNT,
        RETIRE,
        ACTIVATE,
        "conn_commit",
    ]


def _chunk_id(harness: Harness) -> str:
    return next(
        event[2][0]
        for event in harness.events
        if isinstance(event, tuple) and event[0] == "sql" and event[1] == INSERT_CHUNK
    )


def test_sql_parameters_for_staging_rows(harness: Harness) -> None:
    result = harness.run()
    version = result["knowledge_version"]
    by_sql = {
        event[1]: event[2]
        for event in harness.events
        if isinstance(event, tuple) and event[0] == "sql"
    }
    assert by_sql[INSERT_VERSION] == (version, COMMIT)
    assert by_sql[UPDATE_PROVIDER] == ("fixture", "hash64-v1", version)
    assert by_sql[DELETE_CHUNKS] == (version,)
    assert by_sql[DELETE_FILES] == (version,)
    item = result["manifest"][0]
    assert by_sql[INSERT_FILE] == (
        version,
        "README.md",
        item["blob_sha"],
        item["sha256"],
        item["bytes"],
        f"markdown_sections:{indexing.CHUNKER_VERSION}",
    )
    chunk = by_sql[INSERT_CHUNK]
    assert chunk[1] == version
    assert chunk[2] == README
    assert chunk[3] == "README.md"
    assert chunk[10:12] == ("fixture", "hash64-v1")
    assert chunk[13] is None
    assert by_sql[SELECT_COUNT] == (version,)
    assert by_sql[ACTIVATE] == (version,)


def test_markdown_files_record_markdown_sections_quality(harness: Harness) -> None:
    harness.files = {"README.md": README, "docs/development.md": README + " docs"}
    result = harness.run()
    assert result["files"] == 2
    assert result["chunks"] == 2
    assert result["embedded_chunks"] == 2
    rows = [e[2] for e in harness.events if isinstance(e, tuple) and e[1:2] == (INSERT_FILE,)]
    assert [row[5] for row in rows] == [f"markdown_sections:{indexing.CHUNKER_VERSION}"] * 2


@pytest.mark.parametrize(
    ("path", "quality"),
    [
        ("README.md", "markdown_sections"),
        ("src/data/projects.ts", "text_fallback"),
        ("docs/notes.txt", "text_fallback"),
    ],
)
def test_parser_quality_depends_on_the_markdown_suffix(path: str, quality: str) -> None:
    assert indexing._parser_quality(path) == f"{quality}:{indexing.CHUNKER_VERSION}"


def test_remote_not_allowed(harness: Harness) -> None:
    harness.remote = b"https://github.com/someone/else"
    with pytest.raises(ValueError, match=r"^only the public portfolio repository is allowed$"):
        harness.run()
    assert kinds(harness) == [("git", "remote")]


def test_invalid_commit(harness: Harness) -> None:
    harness.commit = b"HEAD"
    with pytest.raises(ValueError, match=r"^invalid commit$"):
        harness.run()
    assert kinds(harness) == [("git", "remote"), ("git", "rev-parse")]


def test_snapshot_source_is_used_without_git(
    harness: Harness, monkeypatch: pytest.MonkeyPatch
) -> None:
    blobs = {"b1": README.encode()}
    monkeypatch.setattr(
        indexing,
        "snapshot_source",
        lambda root: (
            COMMIT,
            [("README.md", "b1")],
            blobs.__getitem__,
            lambda sha: len(blobs[sha]),
        ),
    )
    result = harness.run(snapshot=True)
    assert result["source_commit"] == COMMIT
    assert result["changed"] is True
    assert not [e for e in harness.events if isinstance(e, tuple) and e[0] == "git"]


def test_active_version_with_projection_is_prepared_not_rebuilt(harness: Harness) -> None:
    version = indexing.corpus_identity(COMMIT, "fixture")[0]
    harness.answers[SELECT_STATUS] = {"row": {"status": "active"}, "rows": []}
    harness.answers[CHUNK_DOC] = {"row": {"id": "doc-1"}, "rows": []}
    assert harness.run() == {"knowledge_version": version, "changed": False, "files": 1}
    assert kinds(harness) == [
        ("git", "remote"),
        ("git", "rev-parse"),
        ("git", "ls-tree"),
        "conn_open",
        SELECT_STATUS,
        CHUNK_DOC,
        "driver",
        ("prepare_graph", version, "doc-1"),
        "driver_close",
        "conn_commit",
    ]


def test_active_version_without_projection_fails(harness: Harness) -> None:
    harness.answers[SELECT_STATUS] = {"row": {"status": "active"}, "rows": []}
    with pytest.raises(ValueError, match=r"^public graph projection unavailable$"):
        harness.run()
    assert "driver" not in harness.events
    assert harness.events[-1] == ("conn_error", "ValueError")


def test_active_version_graph_failure_closes_driver(harness: Harness) -> None:
    harness.answers[SELECT_STATUS] = {"row": {"status": "active"}, "rows": []}
    harness.answers[CHUNK_DOC] = {"row": {"id": "doc-1"}, "rows": []}
    harness.fail_prepare_graph = True
    with pytest.raises(RuntimeError, match=r"^graph down$"):
        harness.run()
    assert harness.events[-3:] == [
        ("prepare_graph", indexing.corpus_identity(COMMIT, "fixture")[0], "doc-1"),
        "driver_close",
        ("conn_error", "RuntimeError"),
    ]


def test_previous_version_files_and_reuse_queries(harness: Harness) -> None:
    harness.answers[SELECT_ACTIVE] = {"row": {"id": "prev"}, "rows": []}
    harness.answers[OLD_FILES] = {"row": None, "rows": []}
    harness.run()
    old_files_call = [e for e in harness.events if isinstance(e, tuple) and e[1:2] == (OLD_FILES,)]
    assert old_files_call == [("sql", OLD_FILES, ("prev",))]


def _reuse(harness: Harness, quality: str, blob_sha: str | None = None) -> dict[str, Any]:
    old = next(indexing.chunks("README.md", README, COMMIT))
    old["id"] = "old"
    blob = blob_sha or f"{1:040x}"
    harness.answers[SELECT_ACTIVE] = {"row": {"id": "prev"}, "rows": []}
    harness.answers[OLD_FILES] = {
        "row": None,
        "rows": [
            {
                "path": "README.md",
                "blob_sha": blob,
                "parser_quality": quality,
                "sha256": "OLDSHA",
                "bytes": 99,
            }
        ],
    }
    harness.answers[OLD_CHUNKS] = {"row": None, "rows": [old]}
    return harness.run()


def test_unchanged_file_is_reused_with_old_manifest_values(harness: Harness) -> None:
    result = _reuse(harness, f"markdown_sections:{indexing.CHUNKER_VERSION}")
    assert result["reused_files"] == 1
    assert result["embedded_chunks"] == 0
    assert result["manifest"] == [
        {"path": "README.md", "blob_sha": f"{1:040x}", "sha256": "OLDSHA", "bytes": 99}
    ]
    reuse_query = [e for e in harness.events if isinstance(e, tuple) and e[1:2] == (OLD_CHUNKS,)]
    assert reuse_query == [("sql", OLD_CHUNKS, ("prev", "README.md"))]
    assert harness.events.count("conn_open") == 4


def test_changed_quality_or_blob_is_not_reused(harness: Harness) -> None:
    assert _reuse(harness, "stale-quality")["reused_files"] == 0


def test_changed_blob_is_not_reused(harness: Harness) -> None:
    result = _reuse(harness, f"markdown_sections:{indexing.CHUNKER_VERSION}", "f" * 40)
    assert result["reused_files"] == 0
    assert result["embedded_chunks"] == 1


def test_cancel_before_first_file(harness: Harness) -> None:
    stop = Event()
    stop.set()
    with pytest.raises(RuntimeError, match=r"^sync_cancelled$"):
        harness.run(stop=stop)
    assert "driver" not in harness.events
    assert harness.sql() == [SELECT_STATUS, SELECT_ACTIVE]


def test_stop_unset_does_not_cancel(harness: Harness) -> None:
    assert harness.run(stop=Event())["changed"] is True


@pytest.mark.parametrize(
    ("path", "size"),
    [("README.md", 60_001), ("public/assistant-knowledge.json", 500_001)],
)
def test_source_size_limit(harness: Harness, path: str, size: int) -> None:
    harness.files = {path: PROJECTION if path.endswith(".json") else README}
    harness.sizes = {path: size}
    with pytest.raises(ValueError, match=r"^source size limit exceeded$"):
        harness.run()


def test_knowledge_json_may_exceed_markdown_limit(harness: Harness) -> None:
    harness.files = {"public/assistant-knowledge.json": PROJECTION}
    harness.sizes = {"public/assistant-knowledge.json": 60_001}
    assert harness.run()["changed"] is True


def test_possible_secret_is_rejected(harness: Harness) -> None:
    harness.files = {"README.md": "# Title\napi_key = abcdef and more text to pass thirty chars"}
    with pytest.raises(ValueError, match=r"^possible secret in README.md$"):
        harness.run()


def test_invalid_utf8_is_rejected(harness: Harness, monkeypatch: pytest.MonkeyPatch) -> None:
    original = harness._git

    def git(repo: Path, *args: str) -> bytes:
        return b"\xff\xfe" if args[:2] == ("cat-file", "blob") else original(repo, *args)

    monkeypatch.setattr(indexing, "git", git)
    with pytest.raises(UnicodeDecodeError):
        harness.run()
    assert "driver" not in harness.events


def test_structured_projection_file_uses_graph_facts(harness: Harness) -> None:
    harness.files = {"public/assistant-knowledge.json": PROJECTION, "README.md": README}
    result = harness.run()
    version = result["knowledge_version"]
    paths = [m["path"] for m in result["manifest"]]
    assert paths == ["public/assistant-knowledge.json", "README.md"]
    assert result["chunks"] == 3
    assert result["embedded_chunks"] == 1
    assert result["manifest"][0]["bytes"] == len(PROJECTION)
    project = next(e for e in harness.events if isinstance(e, tuple) and e[0] == "project")
    assert project[2] == version
    assert project[3] == ["public/assistant-knowledge.json"] * 2 + ["README.md"]
    assert project[5] == {"explicit_facts": "GRAPH_FACTS"}
    assert ("graph_facts", ["README.md", "public/assistant-knowledge.json"]) in harness.events
    graph_calls = [i for i, e in enumerate(harness.events) if e[0] == "graph_facts"]
    assert len(graph_calls) == 2  # validation before staging, then explicit projection facts
    assert graph_calls[0] < harness.events.index("driver")


def test_oversized_embedding_input(harness: Harness) -> None:
    harness.files = {
        "public/assistant-knowledge.json": '{"facts": [' + '"' + "x" * 8100 + '"], "personal": {}}'
    }
    harness.sizes = {}
    with pytest.raises(
        ValueError, match=r"^complete source spans must fit the embedding input bound$"
    ):
        harness.run()


def test_empty_corpus_is_rejected(harness: Harness) -> None:
    harness.files = {"README.md": "short"}
    with pytest.raises(ValueError, match=r"^corpus must contain between 1 and 500 chunks$"):
        harness.run()
    assert "driver" not in harness.events


def test_too_many_chunks_are_rejected(harness: Harness) -> None:
    body = "\n\n".join(f"# Section {i}\n" + "text " * 10 for i in range(501))
    harness.files = {"README.md": body}
    with pytest.raises(ValueError, match=r"^corpus must contain between 1 and 500 chunks$"):
        harness.run()


def test_openai_cache_miss_encodes_and_stores(harness: Harness) -> None:
    result = harness.run("openai")
    version = result["knowledge_version"]
    assert version == indexing.corpus_identity(COMMIT, "openai")[0]
    assert kinds(harness)[9:20] == [
        ("client", {"api_key": None}),
        ("encoder", True),
        "conn_open",
        CACHE_SELECT,
        "conn_commit",
        ("encode", "index"),
        "conn_open",
        CACHE_INSERT,
        "conn_commit",
        "client_close",
        "conn_open",
    ]
    by_sql = {e[1]: e[2] for e in harness.events if isinstance(e, tuple) and e[0] == "sql"}
    record_hash = by_sql[CACHE_SELECT][0]
    assert by_sql[CACHE_SELECT] == (record_hash, "openai", "text-embedding-3-small")
    vector_text = by_sql[CACHE_INSERT][3]
    assert by_sql[CACHE_INSERT] == (record_hash, "openai", "text-embedding-3-small", vector_text)
    assert vector_text == indexing.vector((0.5,) * 1536)
    assert by_sql[INSERT_CHUNK][13] == vector_text
    assert by_sql[UPDATE_PROVIDER] == ("openai", "text-embedding-3-small", version)


def test_openai_cache_hit_skips_encoding(harness: Harness) -> None:
    harness.answers[CACHE_SELECT] = {"row": {"semantic_embedding": [1, 2]}, "rows": []}
    result = harness.run("openai")
    assert ("encode", "index") not in harness.events
    assert CACHE_INSERT not in harness.sql()
    assert "client_close" in harness.events
    inserted = next(
        e[2] for e in harness.events if isinstance(e, tuple) and e[1:2] == (INSERT_CHUNK,)
    )
    assert inserted[13] == "[1, 2]"
    assert result["changed"] is True


def test_openai_encode_failure_closes_client_before_staging(harness: Harness) -> None:
    harness.encode_error = RuntimeError("provider down")
    with pytest.raises(RuntimeError, match=r"^provider down$"):
        harness.run("openai")
    assert kinds(harness)[-2:] == [("encode", "index"), "client_close"]
    assert INSERT_VERSION not in harness.sql()


def test_fixture_provider_creates_no_client(harness: Harness) -> None:
    harness.run()
    assert not [e for e in harness.events if isinstance(e, tuple) and e[0] == "client"]
    assert "client_close" not in harness.events


def test_cancel_during_embedding_loop_closes_client(harness: Harness) -> None:
    stop = Event()
    harness.stop_on_client = stop
    with pytest.raises(RuntimeError, match=r"^sync_cancelled$"):
        harness.run("openai", stop=stop)
    assert harness.events[-3:] == [("client", {"api_key": None}), ("encoder", True), "client_close"]
    assert INSERT_VERSION not in harness.sql()


def test_projection_failure_closes_driver_and_leaves_staging(harness: Harness) -> None:
    harness.project_error = RuntimeError("neo4j down")
    with pytest.raises(RuntimeError, match=r"^neo4j down$"):
        harness.run()
    assert harness.events[-1] == "driver_close"
    assert ACTIVATE not in harness.sql()
    assert RETIRE not in harness.sql()


def test_incomplete_vector_projection(harness: Harness) -> None:
    harness.answers["count"] = 0
    with pytest.raises(RuntimeError, match=r"^vector projection incomplete$"):
        harness.run()
    assert harness.events[-1] == ("conn_error", "RuntimeError")
    assert ACTIVATE not in harness.sql()


def test_cancel_after_projection_prevents_activation(harness: Harness) -> None:
    stop = Event()
    harness.stop_after_sql = (SELECT_COUNT, stop)
    with pytest.raises(RuntimeError, match=r"^sync_cancelled$"):
        harness.run(stop=stop)
    assert harness.sql()[-1] == SELECT_COUNT
    assert harness.events[-1] == ("conn_error", "RuntimeError")


def test_watched_activation_when_observed_commit_matches(harness: Harness) -> None:
    harness.answers[WATCH] = {"row": {"observed_commit": COMMIT}, "rows": []}
    result = harness.run(watched=True)
    assert result["changed"] is True
    assert harness.sql()[-4:] == [SELECT_COUNT, WATCH, RETIRE, ACTIVATE]


@pytest.mark.parametrize("observed", [None, {"observed_commit": "b" * 40}])
def test_watched_superseded_returns_without_activation(
    harness: Harness, observed: dict[str, str] | None
) -> None:
    harness.answers[WATCH] = {"row": observed, "rows": []}
    result = harness.run(watched=True)
    assert result == {
        "knowledge_version": indexing.corpus_identity(COMMIT, "fixture")[0],
        "changed": False,
        "superseded": True,
    }
    assert harness.sql()[-2:] == [SELECT_COUNT, WATCH]
    assert harness.events[-1] == "conn_commit"


def test_unwatched_skips_watch_query(harness: Harness) -> None:
    harness.run()
    assert WATCH not in harness.sql()
