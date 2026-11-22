"""Write SSE streams produced by the real presentation code, for the cross-repo site parser job.

`execute_run` renders a scripted v1 run (no database, no provider) twice: as a v1 client sees it
(no `X-Assistant-Progress`) and opted in. The output is the exact wire text, one string per stream.
Usage: python -m scripts.sse_sample --out artifacts/sse-sample.json
"""

import argparse
import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

from portfolio_assistant.presentation.http import execute_run


class FixedClock:
    def now(self) -> datetime:
        return datetime(2026, 11, 22, 12, 0, tzinfo=UTC)


RUN = UUID("00000000-0000-0000-0000-000000000001")
CONVERSATION = UUID("00000000-0000-0000-0000-000000000002")
MESSAGE = {"message_id": str(UUID(int=3)), "content": "Hello", "citations": []}
SCRIPTS = {
    "completed": [
        ("run.started", {"state": "running"}),
        ("run.status", {"phase": "evidence_found", "sources": 1}),
        ("message.delta", {"text": "Hel"}),
        ("message.delta", {"text": "lo"}),
        ("message.completed", MESSAGE),
        ("run.completed", {"state": "completed"}),
    ],
    "failed": [("run.started", {"state": "running"}), ("run.failed", {"code": "busy"})],
    "cancelled": [("run.started", {"state": "running"}), ("run.cancelled", {})],
}


def request_for(script: list[tuple[str, dict[str, object]]]) -> SimpleNamespace:
    async def execute(*_args: object):
        for name, payload in script:
            yield SimpleNamespace(name=name, payload=payload)

    runs = SimpleNamespace(execute=execute)
    return SimpleNamespace(
        state=SimpleNamespace(request_id="sample"),
        app=SimpleNamespace(state=SimpleNamespace(runs=runs, clock=FixedClock())),
    )


async def render(script: list[tuple[str, dict[str, object]]], *, progress: bool) -> str:
    stream = execute_run(request_for(script), RUN, CONVERSATION, "q", "en", progress=progress)
    return "".join([frame async for frame in stream])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)
    sample = {
        mode: {
            name: asyncio.run(render(script, progress=mode == "opt_in"))
            for name, script in SCRIPTS.items()
        }
        for mode in ("v1", "opt_in")
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(sample, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
