"""Compile authored intent families into evaluation cases, never runtime evidence."""

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KINDS = ('direct', 'conversational', 'evidence', 'brief', 'evidence_limits')
SUFFIXES = {
    'brief': {
        'en': 'Keep the answer concise and include a public source if available.',
        'es': 'Responde de forma breve e incluye una fuente pública si está disponible.',
    },
    'evidence_limits': {
        'en': 'Distinguish documented facts from anything the available sources cannot establish.',
        'es': 'Distingue los hechos documentados de lo que las fuentes disponibles no permiten respaldar.',
    },
}
RUBRIC = ('correctness', 'source_support', 'scope', 'language', 'helpfulness')


def compile_bank(source: dict) -> dict:
    if (
        set(source)
        != {
            'schema_version',
            'source_policy',
            'public_reference',
            'families',
            'adversarial',
        }
        or source['schema_version'] != '2'
    ):
        raise ValueError('invalid question-bank metadata')
    cases = []
    seen_families = set()
    seen_questions = set()
    for family in source['families']:
        identifier = family['id']
        if (
            set(family) != {'id', 'topic', 'split', 'variants'}
            or not re.fullmatch(r'[a-z][a-z0-9-]{1,79}', identifier)
            or identifier in seen_families
            or family['split'] not in ('development', 'holdout')
            or len(family['variants']) != 3
        ):
            raise ValueError('invalid or duplicate intent family')
        seen_families.add(identifier)
        for index, kind in enumerate(KINDS):
            pair = family['variants'][index if index < 3 else 0]
            if set(pair) != {'en', 'es'}:
                raise ValueError('each authored variation requires English and Spanish')
            for locale in ('en', 'es'):
                question = pair[locale]
                if kind in SUFFIXES:
                    question += ' ' + SUFFIXES[kind][locale]
                normalized = re.sub(r'\W+', '', question.casefold())
                if not 1 <= len(question) <= 2000 or normalized in seen_questions:
                    raise ValueError(
                        f'empty, oversized or duplicate question: {identifier}'
                    )
                seen_questions.add(normalized)
                cases.append(
                    {
                        'id': f'{identifier}-{locale}'
                        if index == 0
                        else f'{identifier}-v{index + 1}-{locale}',
                        'family_id': identifier,
                        'variation': kind,
                        'locale': locale,
                        'question': question,
                        'split': family['split'],
                        'topic': family['topic'],
                        'rubric': list(RUBRIC),
                        'review_status': 'pending_real_answer_review',
                    }
                )
    return {
        'schema_version': source['schema_version'],
        'source_policy': source['source_policy'],
        'public_reference': source['public_reference'],
        'cases': cases,
        'adversarial': source['adversarial'],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--check', action='store_true', help='Fail on generated artifact drift'
    )
    args = parser.parse_args()
    source = json.loads((ROOT / 'evals/assistant-intents.json').read_text())
    target = ROOT / 'evals/assistant.json'
    rendered = json.dumps(compile_bank(source), ensure_ascii=False, indent=2) + '\n'
    if args.check:
        if target.read_text() != rendered:
            raise SystemExit(
                'question bank drift: run python -m scripts.build_assistant_bank'
            )
    else:
        target.write_text(rendered)


if __name__ == '__main__':
    main()
