"""Run the Locust SSE load against the stubbed app, write a JSON report and enforce budgets.

    uv run --group load python -m tests.load.run_load --profile smoke
    uv run --group load python -m tests.load.run_load --profile full --report load-report.json

A metric over its budget fails the run unless `baseline` in budgets.json records an accepted
higher value (ADR 024); baselines may only be tightened.
"""

import argparse
import csv
import json
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).parent
# users, seconds; the full profile is 3x the expected 10 concurrent streams and a 15-minute soak.
PROFILES = {'smoke': (5, 20), 'full': (30, 900)}
SOAK_SECONDS = 600
BUDGET_KEYS = ('ttfe_p95_ms', 'gap_p95_ms', 'error_rate', 'rss_growth')
# Each user should complete at least one stream every 20 s, or the run proved nothing.
MIN_STREAM_DIVISOR = 20


def rss_kb(pid):
    for line in Path(f'/proc/{pid}/status').read_text().splitlines():
        if line.startswith('VmRSS:'):
            return int(line.split()[1])
    return 0


def metrics(rows, rss_start, rss_end):
    """Reduce Locust stats rows (by name) and RSS samples to the budgeted numbers."""
    stream = rows.get('stream', {})
    requests = int(stream.get('Request Count', 0))
    failures = int(stream.get('Failure Count', 0)) + int(
        rows.get('setup', {}).get('Failure Count', 0)
    )

    def p95(name):
        row = rows.get(name)
        return float(row['95%']) if row else None

    return {
        'ttfe_p95_ms': p95('ttfe'),
        'gap_p95_ms': p95('gap'),
        'streams': requests - int(stream.get('Failure Count', 0)),
        'error_rate': failures / max(requests + failures, 1),
        'rss_growth': (rss_end - rss_start) / max(rss_start, 1),
    }


def load_budgets(path=HERE / 'budgets.json'):
    config = json.loads(Path(path).read_text())
    if set(config['budgets']) != set(BUDGET_KEYS):
        raise ValueError(f'budgets must define exactly {sorted(BUDGET_KEYS)}')
    if not set(config['baseline']) <= set(config['budgets']):
        raise ValueError('baseline keys must be budget keys')
    return config


def verdict(measured, budgets, baseline, duration, users=1):
    """Return the failing metrics; RSS growth is only meaningful for a soak."""
    limits = {**budgets, **baseline}
    skipped = {'rss_growth'} if duration < SOAK_SECONDS else set()
    over = {}
    for name, limit in limits.items():
        value = measured.get(name)
        if name in skipped:
            continue
        if value is None:
            over[name] = {'value': None, 'limit': limit, 'reason': 'no samples'}
        elif value > limit:
            over[name] = {'value': value, 'limit': limit}
    needed = max(1, users * duration // MIN_STREAM_DIVISOR)
    if measured['streams'] < needed:
        over['streams'] = {
            'value': measured['streams'],
            'limit': needed,
            'reason': 'too few completed streams',
        }
    return over


def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--profile', choices=PROFILES, default='smoke')
    parser.add_argument('--users', type=int)
    parser.add_argument('--duration', type=int)
    parser.add_argument('--report', default='load-report.json')
    args = parser.parse_args(argv)
    users, duration = (
        args.users or PROFILES[args.profile][0],
        args.duration or PROFILES[args.profile][1],
    )
    config = load_budgets()
    port = free_port()
    server = subprocess.Popen(
        [
            sys.executable,
            '-m',
            'uvicorn',
            'tests.load.stub_app:app',
            '--port',
            str(port),
            '--log-level',
            'warning',
        ]
    )
    locust = None
    rows, rss_start, rss_end = {}, 0, 0
    try:
        host = f'http://127.0.0.1:{port}'
        for _ in range(300):
            if server.poll() is not None:
                print('stub server exited during start-up', file=sys.stderr)
                return 1
            try:
                socket.create_connection(('127.0.0.1', port), 0.2).close()
                break
            except OSError:
                time.sleep(0.2)
        else:
            print('stub server never became ready', file=sys.stderr)
            return 1
        with tempfile.TemporaryDirectory() as out:
            locust = subprocess.Popen(
                [
                    sys.executable,
                    '-m',
                    'locust',
                    '-f',
                    str(HERE / 'locustfile.py'),
                    '--headless',
                    '--host',
                    host,
                    '-u',
                    str(users),
                    '-r',
                    str(users),
                    '-t',
                    f'{duration}s',
                    '--csv',
                    f'{out}/run',
                    '--only-summary',
                ]
            )
            time.sleep(min(10, duration / 4))  # warm-up before the RSS reference
            rss_start = rss_kb(server.pid)
            locust.wait()
            rss_end = rss_kb(server.pid)
            stats = Path(f'{out}/run_stats.csv')
            if stats.exists():
                with stats.open() as handle:
                    rows = {row['Name']: row for row in csv.DictReader(handle)}
    finally:
        if locust and locust.poll() is None:
            locust.terminate()
            locust.wait()
        server.terminate()
        server.wait()
    measured = metrics(rows, rss_start, rss_end)
    over = verdict(measured, config['budgets'], config['baseline'], duration, users)
    report = {
        'profile': args.profile,
        'users': users,
        'duration_s': duration,
        'measured': measured,
        'budgets': config['budgets'],
        'baseline': config['baseline'],
        'over_budget': over,
    }
    Path(args.report).write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
    return 1 if over else 0


if __name__ == '__main__':
    sys.exit(main())
