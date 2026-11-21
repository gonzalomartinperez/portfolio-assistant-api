"""Explicit, bounded sync of approved files from the public portfolio repository."""

import hashlib
import json
import os
import re
import subprocess
from dataclasses import dataclass, field
from decimal import Decimal
from itertools import pairwise
from typing import TYPE_CHECKING, Any, Literal, Protocol, cast
from urllib.parse import quote

from neo4j import READ_ACCESS, Driver, GraphDatabase

from app.adapters.neo4j.projection import project
from app.adapters.neo4j.read_queries import prepare_reads
from app.adapters.portfolio.projection import PublicProjection, graph_facts
from app.adapters.portfolio.source_format import facts_for
from app.adapters.postgres.ledger import EmbeddingAccounting
from app.adapters.providers.embedding import (
    FixtureEmbeddings,
    OpenAIEmbeddings,
    embed,
    vector,
)
from app.adapters.providers.http import create_sync_client
from app.domain.portfolio_paths import (
    PROFILE_PATH_PATTERN,
    corpus_version,
    profile_parts,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from pathlib import Path
    from threading import Event

    from psycopg import Connection
    from psycopg.rows import DictRow

    from app.adapters.postgres.db import Connect


class IndexConfiguration(Protocol):
    embeddings_provider: Literal["fixture", "openai"]
    openai_api_key: str | None
    reserve_cutoff_usd: str
    embedding_usd_per_million: str
    neo4j_uri: str
    neo4j_user: str
    neo4j_password: str
    neo4j_database: str


ROOT_PATTERNS = (
    re.compile(r"^public/assistant-knowledge\.json$"),
    re.compile(PROFILE_PATH_PATTERN),
    re.compile(r"^docs/(development|public-content|editorial-guidelines)\.md$"),
    re.compile(r"^README\.md$"),
)
SECRET_PATTERN = re.compile(
    r"(?i)(api[_-]?key\s*[=:]|password\s*[=:]|secret\s*[=:]|BEGIN [A-Z ]+PRIVATE KEY)"
)
ALLOWED_REMOTES = (
    "https://github.com/gonzalomartinperez/portfolio",
    "https://github.com/gonzalomartinperez/portfolio.git",
    "git@github.com:gonzalomartinperez/portfolio.git",
)
MAX_FILES = 80
MAX_BYTES = 60_000
CHUNKER_VERSION = "sections35-v6"


def graph_driver(config: IndexConfiguration) -> Driver:
    return GraphDatabase.driver(
        config.neo4j_uri,
        auth=(config.neo4j_user, config.neo4j_password),
        connection_timeout=3,
        connection_acquisition_timeout=5,
        max_transaction_retry_time=0,
        disable_auto_commit_retries=True,
        telemetry_disabled=True,
    )


def prepare_graph(
    driver: Driver, config: IndexConfiguration, version: str, document_id: str
) -> None:
    with driver.session(
        database=config.neo4j_database,
        default_access_mode=READ_ACCESS,
        disable_auto_commit_retries=True,
    ) as graph:
        prepare_reads(graph, version, document_id)


def git(repo: Path, *args: str) -> bytes:
    return subprocess.check_output(
        ["git", "-C", str(repo), *args],
        timeout=30,
        env={
            "PATH": os.defpath,
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_TERMINAL_PROMPT": "0",
        },
    )


def manifest_at_commit(repo: Path, commit: str) -> list[tuple[str, str]]:
    listed = git(repo, "ls-tree", "-r", commit).decode().splitlines()
    allowed = []
    profiles = set()
    for line in listed:
        metadata, path = line.split("\t", 1)
        mode, kind, blob_sha = metadata.split()
        if any(pattern.fullmatch(path) for pattern in ROOT_PATTERNS):
            if kind != "blob" or mode not in ("100644", "100755"):
                raise ValueError(f"unsupported file type: {path}")
            profile = profile_parts(path)
            if profile is not None:
                if profile in profiles:
                    raise ValueError("ambiguous public profile source layouts")
                profiles.add(profile)
            allowed.append((path, blob_sha))
    if len(allowed) > MAX_FILES:
        raise ValueError("file limit exceeded")
    return allowed


def snapshot_source(
    root: Path,
) -> tuple[str, list[tuple[str, str]], Callable[[str], bytes], Callable[[str], int]]:
    """Read the frozen corpus directory (ADR016) as the same (commit, files) a Git ref gives.

    Blob ids are Git object ids of the bytes, so they equal the portfolio repository's own
    and citations keep pointing at the real source commit recorded in the manifest.
    """
    manifest = json.loads((root / "manifest.json").read_text())
    commit = manifest["commit"]
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("invalid commit")
    if manifest["repository"] != "gonzalomartinperez/portfolio":
        raise ValueError("only the public portfolio repository is allowed")
    blobs: dict[str, bytes] = {}
    files: list[tuple[str, str]] = []
    profiles = set()
    for item in sorted(manifest["files"], key=lambda entry: entry["path"]):
        path = item["path"]
        if not any(pattern.fullmatch(path) for pattern in ROOT_PATTERNS):
            raise ValueError(f"unapproved snapshot path: {path}")
        target = root / path
        if target.stat().st_size > (
            500000 if path == "public/assistant-knowledge.json" else MAX_BYTES
        ):
            raise ValueError("source size limit exceeded")
        data = target.read_bytes()
        if hashlib.sha256(data).hexdigest() != item["sha256"]:
            raise ValueError(f"snapshot file does not match its manifest: {path}")
        profile = profile_parts(path)
        if profile is not None:
            if profile in profiles:
                raise ValueError("ambiguous public profile source layouts")
            profiles.add(profile)
        blob_sha = hashlib.sha1(b"blob %d\0" % len(data) + data, usedforsecurity=False).hexdigest()
        blobs[blob_sha] = data
        files.append((path, blob_sha))
    if len(files) > MAX_FILES:
        raise ValueError("file limit exceeded")
    return commit, files, blobs.__getitem__, lambda blob_sha: len(blobs[blob_sha])


def citation_url(commit: str, path: str, start: int, end: int) -> str:
    return f"https://github.com/gonzalomartinperez/portfolio/blob/{commit}/{quote(path, safe='/')}#L{start}-L{end}"


def chunk_id(commit: str, path: str, start: int, content_hash: str) -> str:
    return hashlib.sha256(
        f"{CHUNKER_VERSION}:{commit}:{path}:{start}:{content_hash}".encode()
    ).hexdigest()


def corpus_identity(commit: str, provider: str) -> tuple[str, str]:
    if provider == "fixture":
        encoder: type[FixtureEmbeddings | OpenAIEmbeddings] = FixtureEmbeddings
        expected = ("fixture", "hash64-v1", 64)
    elif provider == "openai":
        encoder = OpenAIEmbeddings
        expected = ("openai", "text-embedding-3-small", 1536)
    else:
        raise ValueError("unsupported embedding provider")
    if (encoder.provider, encoder.model, encoder.dimensions) != expected:
        raise ValueError("embedding profile requires a reviewed schema/cache migration")
    # New versions preserve legacy corpus rows and graph documents during upgrades.
    version = corpus_version(commit, provider)
    return version, json.dumps((version, *expected), separators=(",", ":"))


def projection_spans(content: str) -> Iterator[tuple[int, int, str]]:
    decoder = json.JSONDecoder()
    array = re.search(r'"facts"\s*:\s*\[', content)
    if array is None:
        raise ValueError("public projection requires facts")
    position = array.end()
    while True:
        while content[position].isspace() or content[position] == ",":
            position += 1
        if content[position] == "]":
            break
        _, end = decoder.raw_decode(content, position)
        yield (
            content[:position].count("\n") + 1,
            content[:end].count("\n") + 1,
            content[position:end],
        )
        position = end
    personal = re.search(r'"personal"\s*:\s*(?=\{)', content)
    if personal is not None:
        _, end = decoder.raw_decode(content, personal.end())
        yield (
            content[: personal.start()].count("\n") + 1,
            content[:end].count("\n") + 1,
            content[personal.start() : end],
        )


def chunks(path: str, content: str, commit: str) -> Iterator[dict[str, Any]]:
    lines = content.splitlines()
    if path == "public/assistant-knowledge.json":
        for start, end, block in projection_spans(content):
            content_hash = hashlib.sha256(block.encode()).hexdigest()
            yield {
                "id": chunk_id(commit, path, start, content_hash),
                "content": block,
                "title": "Approved public profile",
                "url": citation_url(commit, path, start, end),
                "source_type": "page",
                "path": path,
                "start_line": start,
                "end_line": end,
                "content_hash": content_hash,
                "embedding": embed(block),
            }
        return
    boundaries = [0]
    if path.endswith(".md"):
        boundaries.extend(
            index for index, line in enumerate(lines) if index > 0 and re.match(r"^#{1,6} ", line)
        )
    boundaries.append(len(lines))
    for section_start, section_end in pairwise(boundaries):
        for start in range(section_start, section_end, 35):
            end = min(start + 35, section_end)
            block = "\n".join(lines[start:end]).strip()
            if len(block) < 30:
                continue
            content_hash = hashlib.sha256(block.encode()).hexdigest()
            yield {
                "id": chunk_id(commit, path, start + 1, content_hash),
                "content": block,
                "title": path,
                "url": citation_url(commit, path, start + 1, end),
                "source_type": "code" if path.endswith((".ts", ".tsx")) else "page",
                "path": path,
                "start_line": start + 1,
                "end_line": end,
                "content_hash": content_hash,
                "embedding": embed(block),
            }


def reused_record(old: dict[str, Any], commit: str) -> dict[str, Any]:
    path = old["path"]
    return {
        **old,
        "id": chunk_id(commit, path, old["start_line"], old["content_hash"]),
        "url": citation_url(commit, path, old["start_line"], old["end_line"]),
    }


def sync(
    repo: Path,
    ref: str = "HEAD",
    *,
    configuration: IndexConfiguration,
    connection: Connect,
    watched: bool = False,
    stop: Event | None = None,
    snapshot: bool = False,
) -> dict[str, Any]:
    # The lock spans both projections; only activation changes the authoritative pointer.
    with connection() as lock:
        lock.autocommit = True
        lock.execute("SELECT pg_advisory_lock(472022)")
        try:
            return _sync(
                repo,
                ref,
                configuration=configuration,
                connection=connection,
                watched=watched,
                stop=stop,
                snapshot=snapshot,
            )
        finally:
            lock.execute("SELECT pg_advisory_unlock(472022)")


@dataclass
class _Source:
    commit: str
    files: list[tuple[str, str]]
    read_blob: Callable[[str], bytes]
    blob_size: Callable[[str], int]


@dataclass
class _Gathered:
    manifest: list[dict[str, Any]] = field(default_factory=list)
    records: list[dict[str, Any]] = field(default_factory=list)
    documents: dict[str, str] = field(default_factory=dict)
    structured: PublicProjection | None = None
    embedded_chunks: int = 0
    reused_files: int = 0


def _git_source(repo: Path, ref: str) -> _Source:
    remote = git(repo, "remote", "get-url", "origin").decode().strip()
    if remote not in ALLOWED_REMOTES:
        raise ValueError("only the public portfolio repository is allowed")
    commit = (
        git(repo, "rev-parse", "--verify", "--end-of-options", ref + "^{commit}").decode().strip()
    )
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("invalid commit")
    files = manifest_at_commit(repo, commit)

    def read_blob(blob_sha: str) -> bytes:
        return git(repo, "cat-file", "blob", blob_sha)

    def blob_size(blob_sha: str) -> int:
        return int(git(repo, "cat-file", "-s", blob_sha))

    return _Source(commit, files, read_blob, blob_size)


def _parser_quality(path: str) -> str:
    return f"{'markdown_sections' if path.endswith('.md') else 'text_fallback'}:{CHUNKER_VERSION}"


def _manifest_entry(path: str, blob_sha: str, sha256: str, size: int) -> dict[str, Any]:
    return {"path": path, "blob_sha": blob_sha, "sha256": sha256, "bytes": size}


def _sync(
    repo: Path,
    ref: str,
    *,
    configuration: IndexConfiguration,
    connection: Connect,
    watched: bool = False,
    stop: Event | None = None,
    snapshot: bool = False,
) -> dict[str, Any]:
    repo = repo.resolve(strict=True)
    source = _Source(*snapshot_source(repo)) if snapshot else _git_source(repo, ref)
    commit = source.commit
    version, namespace = corpus_identity(commit, configuration.embeddings_provider)
    with connection() as conn:
        active = _active_result(conn, configuration, version, source)
        if active is not None:
            return active
        previous_version, old_files = _previous_state(conn)
    gathered = _gather(source, connection, previous_version, old_files, stop)
    records = gathered.records
    _validate_records(gathered)
    for record in records:
        record["id"] = hashlib.sha256(f"{namespace}:{record['id']}".encode()).hexdigest()
    encoder = _embed_records(records, configuration, connection, stop)
    _stage(connection, version, commit, encoder, gathered)
    facts_count = _project_graph(configuration, version, gathered)
    with connection() as conn:
        superseded = _promote(conn, version, commit, len(records), watched, stop)
    if superseded is not None:
        return superseded
    return {
        "knowledge_version": version,
        "source_commit": commit,
        "changed": True,
        "files": len(gathered.manifest),
        "chunks": len(records),
        "embedded_chunks": gathered.embedded_chunks,
        "reused_files": gathered.reused_files,
        "manifest": gathered.manifest,
        "graph_facts": facts_count,
    }


def _active_result(
    conn: Connection[DictRow], config: IndexConfiguration, version: str, source: _Source
) -> dict[str, Any] | None:
    """Re-prepare the graph when this exact version is already active; None otherwise."""
    existing = conn.execute(
        "SELECT status FROM knowledge_versions WHERE id=%s", (version,)
    ).fetchone()
    if not (existing and existing["status"] == "active"):
        return None
    document = conn.execute(
        "SELECT id FROM chunks WHERE knowledge_version=%s LIMIT 1", (version,)
    ).fetchone()
    if not document:
        raise ValueError("public graph projection unavailable")
    driver = graph_driver(config)
    try:
        prepare_graph(driver, config, version, document["id"])
    finally:
        driver.close()
    return {"knowledge_version": version, "changed": False, "files": len(source.files)}


def _previous_state(conn: Connection[DictRow]) -> tuple[str | None, dict[str, Any]]:
    previous = conn.execute(
        "SELECT id FROM knowledge_versions WHERE status='active' ORDER BY created_at DESC LIMIT 1"
    ).fetchone()
    previous_version = previous["id"] if previous else None
    old_files = (
        {
            row["path"]: row
            for row in conn.execute(
                "SELECT * FROM source_files WHERE knowledge_version=%s",
                (previous_version,),
            ).fetchall()
        }
        if previous_version
        else {}
    )
    return previous_version, old_files


def _gather(
    source: _Source,
    connection: Connect,
    previous_version: str | None,
    old_files: dict[str, Any],
    stop: Event | None,
) -> _Gathered:
    gathered = _Gathered()
    for path, blob_sha in source.files:
        if stop is not None and stop.is_set():
            raise RuntimeError("sync_cancelled")
        _gather_file(gathered, source, connection, previous_version, old_files, path, blob_sha)
    return gathered


def _gather_file(
    gathered: _Gathered,
    source: _Source,
    connection: Connect,
    previous_version: str | None,
    old_files: dict[str, Any],
    path: str,
    blob_sha: str,
) -> None:
    if source.blob_size(blob_sha) > (
        500000 if path == "public/assistant-knowledge.json" else MAX_BYTES
    ):
        raise ValueError("source size limit exceeded")
    data = source.read_blob(blob_sha)
    content = data.decode("utf-8")
    if SECRET_PATTERN.search(content):
        raise ValueError(f"possible secret in {path}")
    gathered.documents[path] = content
    sha256 = hashlib.sha256(data).hexdigest()
    if path == "public/assistant-knowledge.json":
        gathered.structured = PublicProjection.model_validate_json(content)
        gathered.manifest.append(_manifest_entry(path, blob_sha, sha256, len(data)))
        gathered.records.extend(chunks(path, content, source.commit))
        return
    old_file = old_files.get(path)
    if (
        old_file
        and old_file["blob_sha"] == blob_sha
        and old_file["parser_quality"] == _parser_quality(path)
    ):
        with connection() as conn:
            old_chunks = conn.execute(
                "SELECT * FROM chunks WHERE knowledge_version=%s AND path=%s ORDER BY start_line",
                (previous_version, path),
            ).fetchall()
        gathered.records.extend(reused_record(row, source.commit) for row in old_chunks)
        gathered.manifest.append(
            _manifest_entry(path, blob_sha, old_file["sha256"], old_file["bytes"])
        )
        gathered.reused_files += 1
        return
    fresh = list(chunks(path, content, source.commit))
    gathered.records.extend(fresh)
    gathered.embedded_chunks += len(fresh)
    gathered.manifest.append(_manifest_entry(path, blob_sha, sha256, len(data)))


def _validate_records(gathered: _Gathered) -> None:
    if gathered.structured is not None:
        graph_facts(gathered.structured, gathered.documents)
    records = gathered.records
    if any(len(record["content"].encode("utf-8")) > 8000 for record in records):
        raise ValueError("complete source spans must fit the embedding input bound")
    if not records or len(records) > 500:
        raise ValueError("corpus must contain between 1 and 500 chunks")


def _embed_records(
    records: list[dict[str, Any]],
    config: IndexConfiguration,
    connection: Connect,
    stop: Event | None,
) -> FixtureEmbeddings | OpenAIEmbeddings:
    embedding_client = None
    encoder: FixtureEmbeddings | OpenAIEmbeddings = FixtureEmbeddings()
    if config.embeddings_provider == "openai":
        embedding_client = create_sync_client(api_key=config.openai_api_key)
        encoder = OpenAIEmbeddings(
            embedding_client,
            EmbeddingAccounting(
                connection,
                Decimal(config.reserve_cutoff_usd),
                Decimal(config.embedding_usd_per_million),
            ),
        )
    try:
        for record in records:
            if stop is not None and stop.is_set():
                raise RuntimeError("sync_cancelled")
            if config.embeddings_provider == "openai":
                _semantic_embedding(record, encoder, connection)
    finally:
        if embedding_client:
            embedding_client.close()
    return encoder


def _semantic_embedding(
    record: dict[str, Any], encoder: FixtureEmbeddings | OpenAIEmbeddings, connection: Connect
) -> None:
    with connection() as conn:
        cached = conn.execute(
            "SELECT embedding AS semantic_embedding FROM public_embedding_cache WHERE content_hash=%s AND provider=%s AND model=%s",
            (record["content_hash"], encoder.provider, encoder.model),
        ).fetchone()
    record["semantic_embedding"] = (
        str(cached["semantic_embedding"])
        if cached
        else vector(encoder.encode(record["content"], "index"))
    )
    if not cached:
        with connection() as conn:
            conn.execute(
                "INSERT INTO public_embedding_cache(content_hash,provider,model,embedding) VALUES (%s,%s,%s,%s::vector) ON CONFLICT DO NOTHING",
                (
                    record["content_hash"],
                    encoder.provider,
                    encoder.model,
                    record["semantic_embedding"],
                ),
            )


def _stage(
    connection: Connect,
    version: str,
    commit: str,
    encoder: FixtureEmbeddings | OpenAIEmbeddings,
    gathered: _Gathered,
) -> None:
    with connection() as conn:
        conn.execute(
            "INSERT INTO knowledge_versions(id,status,source_commit) VALUES (%s,'staging',%s) ON CONFLICT(id) DO UPDATE SET status='staging'",
            (version, commit),
        )
        conn.execute(
            "UPDATE knowledge_versions SET embedding_provider=%s,embedding_model=%s WHERE id=%s",
            (encoder.provider, encoder.model, version),
        )
        conn.execute("DELETE FROM chunks WHERE knowledge_version=%s", (version,))
        conn.execute("DELETE FROM source_files WHERE knowledge_version=%s", (version,))
        for item in gathered.manifest:
            conn.execute(
                "INSERT INTO source_files(knowledge_version,path,blob_sha,sha256,bytes,parser_quality) VALUES (%s,%s,%s,%s,%s,%s)",
                (
                    version,
                    item["path"],
                    item["blob_sha"],
                    item["sha256"],
                    item["bytes"],
                    _parser_quality(item["path"]),
                ),
            )
        for record in gathered.records:
            _insert_chunk(conn, version, encoder, record)


def _insert_chunk(
    conn: Connection[DictRow],
    version: str,
    encoder: FixtureEmbeddings | OpenAIEmbeddings,
    record: dict[str, Any],
) -> None:
    conn.execute(
        "INSERT INTO chunks(id,knowledge_version,content,title,url,source_type,path,start_line,end_line,content_hash,embedding_provider,embedding_model,embedding,semantic_embedding) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::vector,%s::vector)",
        (
            record["id"],
            version,
            record["content"],
            record["title"],
            record["url"],
            record["source_type"],
            record["path"],
            record["start_line"],
            record["end_line"],
            record["content_hash"],
            encoder.provider,
            encoder.model,
            record["embedding"],
            record.get("semantic_embedding"),
        ),
    )


def _project_graph(config: IndexConfiguration, version: str, gathered: _Gathered) -> int:
    records = gathered.records
    documents = gathered.documents
    structured = gathered.structured
    driver = graph_driver(config)
    try:
        driver.verify_connectivity()
        with driver.session(database=config.neo4j_database) as session:
            facts_count = project(
                session,
                version,
                records,
                documents,
                explicit_facts=(
                    facts_for(documents)
                    if structured is None
                    else graph_facts(structured, documents)
                ),
            )
        prepare_graph(driver, config, version, records[0]["id"])
    finally:
        driver.close()
    return facts_count


def _promote(
    conn: Connection[DictRow],
    version: str,
    commit: str,
    expected: int,
    watched: bool,
    stop: Event | None,
) -> dict[str, Any] | None:
    """Activate the staged version; return a superseded result instead when the watch moved."""
    # An ungrouped COUNT always returns one row.
    row = conn.execute(
        "SELECT count(*) AS n FROM chunks WHERE knowledge_version=%s", (version,)
    ).fetchone()
    count = cast("DictRow", row)["n"]
    if count != expected:
        raise RuntimeError("vector projection incomplete")
    if stop is not None and stop.is_set():
        raise RuntimeError("sync_cancelled")
    if watched:
        observed = conn.execute(
            "SELECT observed_commit FROM knowledge_watch WHERE singleton FOR UPDATE"
        ).fetchone()
        if not observed or observed["observed_commit"] != commit:
            return {"knowledge_version": version, "changed": False, "superseded": True}
    conn.execute("UPDATE knowledge_versions SET status='retired' WHERE status='active'")
    conn.execute("UPDATE knowledge_versions SET status='active' WHERE id=%s", (version,))
    return None
