"""Only an explicitly trusted socket peer can supply a coarse edge-country label."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError
from starlette.requests import Request

from app.bootstrap.config import Settings
from app.domain.analytics_country import COUNTRIES, country_label
from app.presentation.analytics_country import country_from_edge


def request(
    peer='172.20.0.5',
    countries=('AR',),
    *,
    enabled=True,
    proxies='172.20.0.5',
    forwarded=None,
):
    config = Settings(
        _env_file=None,
        product_analytics_country_enabled=enabled,
        product_analytics_country_proxy_ips=proxies,
    )
    headers = [(b'cf-ipcountry', value.encode()) for value in countries]
    if forwarded:
        headers.append((b'x-forwarded-for', forwarded.encode()))
    return Request(
        {
            'type': 'http',
            'app': SimpleNamespace(state=SimpleNamespace(config=config)),
            'client': (peer, 50000) if peer is not None else None,
            'headers': headers,
        }
    )


def test_country_labels_are_closed_and_unknown_is_not_invented_location():
    assert len(COUNTRIES) == 249
    assert country_label('AR') == 'AR'
    assert country_label('US') == 'US'
    assert country_label('GB') == 'GB'
    for value in (None, 'XX', 'T1', 'UK', 'ZZ', 'ar', ' AR ', 'AR,US', 'Argentina'):
        assert country_label(value) == 'unknown'


def test_country_is_default_off_and_never_inferred_from_forwarded_client_or_locale():
    assert not Settings(_env_file=None).product_analytics_country_enabled
    assert country_from_edge(request(enabled=False)) == 'unknown'
    assert (
        country_from_edge(request(peer='203.0.113.7', forwarded='172.20.0.5'))
        == 'unknown'
    )
    assert country_from_edge(request(peer=None)) == 'unknown'
    assert country_from_edge(request(peer='testclient')) == 'unknown'
    assert country_from_edge(request()) == 'AR'
    assert country_from_edge(request(peer='::ffff:172.20.0.5')) == 'AR'


@pytest.mark.parametrize(
    'case',
    json.loads(Path('contracts/analytics-semantics.examples.json').read_text())[
        'country_cases'
    ],
    ids=lambda case: case['name'],
)
def test_shared_country_cases_match_the_actual_boundary(case):
    assert (
        country_from_edge(
            request(
                peer=case['peer'],
                countries=case['headers'],
                enabled=case['enabled'],
                proxies=case['trusted_peers'],
            )
        )
        == case['expected']
    )


@pytest.mark.parametrize(
    'proxies',
    [
        '',
        '*',
        '0.0.0.0/0',
        '::/0',
        '0.0.0.0',
        '::',
        '224.0.0.1',
        'proxy.example.invalid',
    ],
)
def test_enabled_country_requires_explicit_valid_socket_peer_addresses(proxies):
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            product_analytics_country_enabled=True,
            product_analytics_country_proxy_ips=proxies,
        )


def test_proxy_address_normalization_does_not_grant_address_ranges():
    config = Settings(
        _env_file=None,
        product_analytics_country_proxy_ips='172.20.0.5, ::ffff:172.20.0.5,::1',
    )
    assert config.product_analytics_country_proxy_ips == '172.20.0.5,::1'
    assert country_from_edge(request(peer='172.20.0.6')) == 'unknown'
