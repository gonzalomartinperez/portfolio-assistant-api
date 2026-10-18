"""The local demo rejects unsafe destinations and writes only private fixture config."""

import argparse
import socket
import stat
import subprocess
import sys

import pytest

from scripts.analytics_demo import private_environment, require_port, site_origin


@pytest.mark.parametrize(
    'origin',
    [
        'http://127.0.0.1:3381',
        'https://shared.invalid:3381',
        'https://127.0.0.1',
        'https://127.0.0.1:3381/path',
        'https://127.0.0.1:3381?query=synthetic',
        'https://127.0.0.1:3381#fragment',
        'https://fixture:synthetic@127.0.0.1:3381',
        'https://127.0.0.1:99999',
    ],
)
def test_site_origin_is_exact_local_tls_without_echoing_input(origin):
    with pytest.raises(argparse.ArgumentTypeError) as failure:
        site_origin(origin)
    assert origin not in str(failure.value)


def test_approved_origins_and_occupied_ports_never_stop_other_services():
    assert site_origin('https://127.0.0.1:3381') == 'https://127.0.0.1:3381'
    assert site_origin('https://localhost:3381') == 'https://localhost:3381'
    with socket.socket() as occupied:
        occupied.bind(('127.0.0.1', 0))
        with pytest.raises(ValueError, match='occupied'):
            require_port(occupied.getsockname()[1])
    with pytest.raises(ValueError, match='unprivileged'):
        require_port(1)


def test_private_environment_is_exclusive_0600_and_rejects_injected_lines(tmp_path):
    destination = tmp_path / 'fixture.env'
    private_environment(destination, {'SYNTHETIC_VALUE': 'disposable'})
    assert destination.read_text() == 'SYNTHETIC_VALUE=disposable\n'
    assert stat.S_IMODE(destination.stat().st_mode) == 0o600
    with pytest.raises(FileExistsError):
        private_environment(destination, {'SYNTHETIC_VALUE': 'replacement'})
    assert destination.read_text() == 'SYNTHETIC_VALUE=disposable\n'
    for values in ({'BAD\nNAME': 'value'}, {'SAFE_NAME': 'bad\nvalue'}):
        rejected = tmp_path / 'rejected.env'
        with pytest.raises(ValueError, match='invalid demo'):
            private_environment(rejected, values)
        assert not rejected.exists()


def test_sigterm_replay_unwinds_external_fixture_cleanup(tmp_path):
    marker = tmp_path / 'cleaned'
    program = f"""
import os
import signal
from contextlib import ExitStack
from pathlib import Path
import uvicorn
from scripts.analytics_demo import cleanup_signals
previous = signal.getsignal(signal.SIGTERM)
try:
    with cleanup_signals(), ExitStack() as cleanup:
        cleanup.callback(Path({str(marker)!r}).write_text, 'done')
        with uvicorn.Server(uvicorn.Config('not.imported:app')).capture_signals():
            os.kill(os.getpid(), signal.SIGTERM)
except KeyboardInterrupt:
    assert signal.getsignal(signal.SIGTERM) == previous
else:
    raise AssertionError('SIGTERM was swallowed')
"""
    result = subprocess.run(
        [sys.executable, '-c', program], check=False, capture_output=True, timeout=10
    )
    assert result.returncode == 0
    assert marker.read_text() == 'done'
