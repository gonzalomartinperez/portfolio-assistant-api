"""Compare fixture retrieval with real indexes; does not call a model."""

import json
import time
from pathlib import Path

from tests.support import retrieve


def main():
    cases = json.loads(Path('evals/retrieval.json').read_text())
    results = []
    for strategy in ('vector', 'graph', 'hybrid'):
        for case in cases:
            start = time.perf_counter()
            rows, _ = retrieve(case['question'], case['locale'], strategy=strategy)
            paths = {r['path'] for r in rows}
            content = '\n'.join(r['content'] for r in rows)
            passed = (
                (
                    all(p in paths for p in case['paths'])
                    and all(n in content for n in case['contains'])
                )
                if case['paths']
                else not rows
            )
            results.append(
                {
                    'strategy': strategy,
                    'case': case['id'],
                    'kind': case['kind'],
                    'passed': passed,
                    'elapsed_ms': round((time.perf_counter() - start) * 1000, 1),
                    'sources': len(rows),
                    'paths': sorted(paths),
                }
            )
    print(
        json.dumps(
            {
                'mode': 'fixture embeddings; real PostgreSQL and Neo4j; no model calls',
                'results': results,
            },
            indent=2,
        )
    )


if __name__ == '__main__':
    main()
