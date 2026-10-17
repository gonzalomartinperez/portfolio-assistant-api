"""Manual opt-in composition, independent of API lifespan and provider configuration."""

import argparse
import json
import os
from pathlib import Path

from app.application.evaluation_export import EvaluationSummary, export_evaluation
from app.infrastructure.evaluation_export import LangSmithEvaluationExporter

DISABLED_TRACING_FLAGS = {
    'LANGSMITH_TRACING',
    'LANGSMITH_TRACING_V2',
    'LANGCHAIN_TRACING',
    'LANGCHAIN_TRACING_V2',
}


def run(path: Path, *, authorize_export: bool = False) -> str:
    with path.open('rb') as source:
        data = source.read(2049)
    if len(data) > 2048:
        raise ValueError('summary exceeds input limit')
    try:
        payload = json.loads(data)
    except ValueError, RecursionError:
        raise ValueError('invalid evaluation summary JSON') from None
    fields = {'source_commit', 'cases', 'completed', 'failed', 'total_ms', 'scope'}
    if not isinstance(payload, dict) or set(payload) != fields:
        raise ValueError('summary requires exactly the documented aggregate fields')
    summary = EvaluationSummary(**payload)
    if not authorize_export:
        return export_evaluation(summary, authorized=False)
    # Explicit keys only. Reject SDK environment overrides, profiles and tracing modes.
    if os.environ.get('ENVIRONMENT', 'development') != 'development' or any(
        name.startswith(('LANGSMITH_', 'LANGCHAIN_'))
        and value != ''
        and not (name in DISABLED_TRACING_FLAGS and value == 'false')
        for name, value in os.environ.items()
    ):
        raise ValueError('export requires a clean development evaluation environment')
    key = os.environ.get('EVALUATION_LANGSMITH_API_KEY', '')
    if not 16 <= len(key) <= 256 or not key.isascii() or any(c.isspace() for c in key):
        raise ValueError('explicit evaluation credential required')
    return export_evaluation(
        summary, authorized=True, exporter=LangSmithEvaluationExporter(key)
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('summary', type=Path)
    parser.add_argument('--authorize-export', action='store_true')
    args = parser.parse_args()
    try:
        result = run(args.summary, authorize_export=args.authorize_export)
    except ValueError, TypeError, OSError:
        parser.exit(2, 'Invalid evaluation summary or export configuration.\n')
    print(json.dumps({'status': result}))
    if result == 'unavailable':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
