"""Opt-in `run.progress` phases derived from the v1 run events (contract v1.1, ADR 020).

The phases are a presentation of milestones the run already reports: `retrieving` right after the run
is claimed, `reading` once retrieval completes (also when no source was found), and `writing` before
the first answer text. They carry
no internal state, tool names or timing, and are never produced unless the client opted in.
"""

from collections.abc import Iterator
from dataclasses import dataclass

Frame = tuple[str, dict[str, object]]
TERMINAL = frozenset({"run.completed", "run.failed", "run.cancelled"})


@dataclass(slots=True)
class ProgressPhases:
    writing: bool = False

    def expand(self, name: str, payload: dict[str, object]) -> Iterator[Frame]:
        """Yield the v1 event, with any progress phase it implies in stream order."""
        if name in ("message.delta", "message.completed") and not self.writing:
            self.writing = True
            yield "run.progress", {"phase": "writing"}
        yield name, payload
        if name == "run.started":
            yield "run.progress", {"phase": "retrieving"}
        elif name == "run.status":
            yield "run.progress", {"phase": "reading"}
