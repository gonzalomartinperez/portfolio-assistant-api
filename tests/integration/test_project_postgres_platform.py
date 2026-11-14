"""Real candidate capabilities and same-platform logical recovery, not PGDATA portability."""

import os

import psycopg
import pytest

from scripts.project_postgres_fixture import locale_metadata, project_fixture


def test_locale_receipt_retains_observed_provider_and_nullable_catalog_version():
    assert locale_metadata(('c', 'C.UTF-8', 'C.UTF-8', None)) == {
        'datlocprovider': 'c',
        'datcollate': 'C.UTF-8',
        'datctype': 'C.UTF-8',
        'datcollversion': None,
    }
    assert (
        locale_metadata(('i', 'en_US.UTF-8', 'en_US.UTF-8', '153.120'))[
            'datcollversion'
        ]
        == '153.120'
    )


@pytest.mark.parametrize(
    'values',
    [
        None,
        1234,
        'cCCv',
        ('c', 'C', 'C'),
        ('unexpected', 'C', 'C', None),
        ('c', 'x' * 129, 'C', None),
        ('c', 'C\nprivate', 'C', None),
        ('c', 'postgres://user:private@host/db', 'C', None),
        ('c', 'C', 'C', 2.42),
    ],
)
def test_locale_receipt_rejects_ambiguous_or_unsafe_metadata(values):
    with pytest.raises(ValueError, match='locale metadata'):
        locale_metadata(values)


@pytest.mark.integration
@pytest.mark.skipif(
    os.getenv('TEST_INTEGRATION') != '1', reason='requires owned local project image'
)
def test_unicode_xml_icu_and_vector_survive_both_database_restores_and_restart():
    image = os.getenv('PROJECT_POSTGRES_IMAGE', 'portfolio-assistant-postgres:18.6')
    text = 'Español: niño — 東京 🦊'
    document = '<public>' + text + '</public>'
    roles = {
        'portfolio_assistant': 'portfolio_api_migrator',
        'portfolio_iam': 'portfolio_iam_migrator',
    }
    with project_fixture(image, authorized=True) as target:
        expected = target.verify_platform()
        for role in roles.values():
            with psycopg.connect(target.connection_info(role)) as connection:
                connection.execute(
                    "CREATE COLLATION public.fixture_roundtrip_icu (provider=icu,locale='und',deterministic=true)"
                )
                connection.execute(
                    'CREATE TABLE public.fixture_platform_roundtrip (label text COLLATE public.fixture_roundtrip_icu,document xml)'
                )
                connection.execute(
                    'INSERT INTO public.fixture_platform_roundtrip VALUES (%s,XMLPARSE(CONTENT %s))',
                    (text, document),
                )
        for database in roles:
            archive = target.dump(database)
            target.restore(database, archive)
        target.restart()
        assert target.verify_platform() == expected
        for role in roles.values():
            with psycopg.connect(target.connection_info(role)) as connection:
                assert connection.execute(
                    'SELECT label,XMLSERIALIZE(CONTENT document AS text) FROM public.fixture_platform_roundtrip ORDER BY label'
                ).fetchall() == [(text, document)]
                assert connection.execute(
                    "SELECT collprovider,collisdeterministic FROM pg_collation WHERE oid='public.fixture_roundtrip_icu'::regcollation"
                ).fetchone() == ('i', True)
