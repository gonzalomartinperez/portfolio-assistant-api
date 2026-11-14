import json
import math
from pathlib import Path

import pytest

from evals.harness import retrieval as harness
from evals.harness.retrieval import (
    abstention_sweep,
    assemble_report,
    breakdown,
    compare_reports,
    decide_drop,
    graph_marginal,
    load_qrels,
    load_queries,
    locale_gap,
    mean_metrics,
    ranked_keys,
    recall_at,
    runs_from_records,
)


def query(qid, locale='en', kind='direct', family='answerable_core', **extra):
    return {
        'id': qid,
        'question': qid,
        'locale': locale,
        'kind': kind,
        'family': family,
        'pair_id': extra.pop('pair_id', qid),
        'expects_evidence': extra.pop('expects_evidence', True),
        **extra,
    }


def scores(recall, ndcg=None):
    return {
        'recall@5': recall,
        'ndcg@5': ndcg or recall,
        'mrr@10': recall,
        'hit@1': recall,
    }


def record(*keys, score=5.0):
    return {'sources': [{'key': k, 'score': score} for k in keys]}


def test_ranked_keys_dedupes_chunks_of_one_key_in_rank_order():
    rec = record('en/projects', 'en/experience', 'en/projects')
    assert ranked_keys(rec) == ['en/projects', 'en/experience']
    assert runs_from_records({'q': rec}) == {'q': ['en/projects', 'en/experience']}


def test_recall_at_counts_distinct_relevant_keys_in_top_k():
    assert recall_at(['a', 'b', 'c'], ['a', 'c']) == 1.0
    assert recall_at(['x', 'a'], ['a', 'c']) == 0.5
    assert recall_at(['x', 'y', 'z', 'w', 'v', 'a'], ['a']) == 0.0
    with pytest.raises(ValueError):
        recall_at(['a'], [])


def test_breakdown_groups_only_scored_queries():
    queries = [
        query('q1', 'en'),
        query('q2', 'es'),
        query('q3', 'es', cross_lingual=True),
        query('q4', 'en', kind='no-answer', expects_evidence=False),
    ]
    per_query = {'q1': scores(1.0), 'q2': scores(0.0), 'q3': scores(0.5)}
    by_locale = breakdown(per_query, queries, 'locale')
    assert by_locale['en']['n'] == 1
    assert by_locale['es']['recall@5'] == 0.25
    stratum = breakdown(per_query, queries, 'stratum')
    assert stratum['cross_lingual']['n'] == 1
    assert stratum['monolingual']['n'] == 2
    assert 'no-answer' not in breakdown(per_query, queries, 'kind')


def test_locale_gap_overall_and_paired_exclude_cross_lingual():
    queries = [
        query('e1', 'en', pair_id='p1'),
        query('s1', 'es', pair_id='p1'),
        query('e2', 'en', pair_id='p2'),
        query('s2', 'es', pair_id='p2'),
        query('e3', 'en', pair_id='p3'),
        query('x', 'es', cross_lingual=True, pair_id='x1'),
    ]
    per_query = {
        'e1': scores(1.0),
        's1': scores(0.5),
        'e2': scores(1.0),
        's2': scores(1.0),
        'e3': scores(0.0),
        'x': scores(0.0),
    }
    gap = locale_gap(per_query, queries)
    assert gap['n_en'] == 3 and gap['n_es'] == 2
    assert gap['gap'] == pytest.approx(2 / 3 - 0.75, abs=1e-4)
    assert gap['pairs'] == 2
    assert gap['paired_gap'] == 0.25


def test_graph_marginal_is_hybrid_minus_no_graph_per_kind():
    queries = [query('a', kind='multi-hop'), query('b', kind='multi-hop'), query('c')]
    hybrid = {'a': scores(1.0), 'b': scores(1.0), 'c': scores(1.0)}
    no_graph = {'a': scores(0.5), 'b': scores(1.0), 'c': scores(1.0)}
    marginal = graph_marginal(hybrid, no_graph, queries)
    assert marginal['by_kind']['multi-hop']['recall@5'] == 0.25
    assert marginal['by_kind']['direct']['recall@5'] == 0.0
    assert marginal['overall']['n'] == 3


def test_decide_drop_needs_a_lower_mean_and_a_significant_p():
    assert decide_drop(0.9, 0.8, 0.01) is True
    assert decide_drop(0.9, 0.8, 0.2) is False
    assert decide_drop(0.8, 0.9, 0.01) is False  # significant improvement
    assert decide_drop(0.9, 0.9, 0.01) is False
    assert decide_drop(0.9, 0.8, math.nan) is False
    assert decide_drop(0.9, 0.8, 0.05) is False  # strict p < alpha


def test_compare_reports_gates_only_golden_relevant_families():
    queries = [
        query('g1'),
        query('g2', family='graph_multihop'),
        query('a1', family='abstain'),
    ]
    qrels = {
        'g1': {'en/projects': 2},
        'g2': {'en/experience': 2},
        'a1': {'en/profile': 1},
    }
    baseline = {
        'runs': {
            'hybrid': {
                'g1': ['en/projects'],
                'g2': ['en/experience'],
                'a1': ['en/profile'],
            }
        }
    }
    current = {'hybrid': {'g1': ['en/x'], 'g2': ['en/experience'], 'a1': []}}
    seen = {}

    def fake_p(subset, base, cur):
        seen['qids'] = sorted(subset)
        return 0.01

    result = compare_reports(baseline, current, qrels, queries, p_value=fake_p)
    assert seen['qids'] == ['g1', 'g2']  # the abstain family is outside the gate
    hybrid = result['strategies']['hybrid']
    assert hybrid['baseline_recall@5'] == 1.0 and hybrid['current_recall@5'] == 0.5
    assert hybrid['significant_drop'] is True and result['failed'] is True

    insignificant = compare_reports(
        baseline, current, qrels, queries, p_value=lambda *_: 0.4
    )
    assert insignificant['failed'] is False


def test_compare_reports_fails_when_a_gated_strategy_is_missing():
    result = compare_reports({'runs': {}}, {'hybrid': {}}, {}, [])
    assert result['strategies']['hybrid']['status'].startswith('missing')
    assert result['failed'] is True


def test_reports_replace_nan_with_null(tmp_path):
    from evals.harness.retrieval import write_json

    path = tmp_path / 'r.json'
    write_json(path, {'gap': float('nan'), 'rows': [{'x': float('nan')}]})
    assert path.read_text().count('null') == 2


def test_abstention_sweep_finds_a_harmless_threshold():
    queries = [
        query('a1'),
        query('a2'),
        query('n1', kind='no-answer', family='abstain', expects_evidence=False),
        query(
            'n2',
            kind='no-answer',
            family='abstain',
            expects_evidence=False,
            **{'class': 'unsupported_employer'},
        ),
    ]
    qrels = {'a1': {'en/projects': 2}, 'a2': {'en/experience': 2}}
    records = {
        'a1': record('en/projects', score=12.0),
        'a2': record('en/experience', score=9.0),
        'n1': record('en/profile', score=2.0),
        'n2': record('en/profile', score=4.0),
    }
    result = abstention_sweep(records, queries, qrels, thresholds=(0, 3, 6, 10))
    sweep = {row['threshold']: row for row in result['sweep']}
    assert sweep[0]['no_answer_with_evidence'] == 2
    assert sweep[3]['no_answer_with_evidence'] == 1
    assert sweep[3]['unsupported_employer_with_evidence'] == 1
    assert sweep[6]['no_answer_with_evidence'] == 0 and sweep[6]['recall_drop'] == 0
    assert sweep[10]['recall_drop'] == 0.5
    assert result['best_threshold_without_recall_loss'] == 6
    assert result['spurious_removed_at_best'] == 2


def test_assemble_report_has_the_required_sections():
    queries = [query('q1', 'en', pair_id='p'), query('q2', 'es', pair_id='p')]
    qrels = {'q1': {'en/projects': 2}, 'q2': {'es/projects': 2}}
    per_query = {
        name: {'q1': scores(1.0), 'q2': scores(0.0)}
        for name in ('hybrid', 'hybrid_no_graph', 'vector')
    }
    records = {
        name: {'q1': record('en/projects'), 'q2': record('es/experience')}
        for name in per_query
    }
    report = assemble_report(queries, qrels, 'resolved', records, per_query, commit='c')
    assert report['qrels_source'] == 'resolved'
    hybrid = report['strategies']['hybrid']
    assert hybrid['overall']['recall@5'] == 0.5
    assert hybrid['en_es_gap']['gap'] == 1.0
    assert set(hybrid) >= {'by_locale', 'by_family', 'by_kind', 'by_stratum'}
    assert report['graph_marginal']['overall']['recall@5'] == 0.0
    assert set(report['abstention']) == {'hybrid', 'vector'}
    assert report['runs']['vector']['q2'] == ['es/experience']
    assert {'h1', 'h2', 'h3', 'h4', 'h5', 'graph'} <= set(report['ablations'])
    json.dumps(report)  # the report must be serializable


def test_mean_metrics_of_nothing_is_nan_not_a_crash():
    assert math.isnan(mean_metrics({}, ['q'])['recall@5'])


def test_ablations_without_a_seam_say_so():
    for name in ('h1', 'h2', 'h3', 'h4', 'h5'):
        assert (
            harness.ABLATIONS[name]['status'] == 'not implementable without app change'
        )
    assert harness.ABLATIONS['graph']['status'] == 'measured'


def test_load_qrels_prefers_resolved_and_falls_back_to_proposals(tmp_path: Path):
    candidates = tmp_path / 'c.jsonl'
    candidates.write_text(
        json.dumps(
            {
                'query_id': 'q1',
                'candidates': [
                    {'key': 'en/projects', 'proposed': 2},
                    {'key': 'en/profile', 'proposed': 0},
                ],
            }
        )
        + '\n',
        encoding='utf-8',
    )
    missing = tmp_path / 'qrels.jsonl'
    assert load_qrels(missing, candidates) == ({'q1': {'en/projects': 2}}, 'proposed')
    missing.write_text(
        json.dumps({'query_id': 'q1', 'key': 'en/profile', 'relevance': 1}) + '\n',
        encoding='utf-8',
    )
    assert load_qrels(missing, candidates) == ({'q1': {'en/profile': 1}}, 'resolved')


def test_ranx_scoring_and_paired_test_when_available():
    pytest.importorskip('ranx')
    qrels = {f'q{i}': {'en/projects': 2} for i in range(8)}
    good = {qid: ['en/projects'] for qid in qrels}
    bad = {qid: ['en/profile', 'en/projects'] for qid in list(qrels)[:6]}
    bad.update({qid: ['en/profile'] for qid in list(qrels)[6:]})
    per_query = harness.score_run(bad, qrels)
    assert per_query['q0']['recall@5'] == 1.0 and per_query['q0']['hit@1'] == 0.0
    assert per_query['q7']['recall@5'] == 0.0
    assert harness.paired_p_value(qrels, good, good) == 1.0
    p = harness.paired_p_value(qrels, good, {q: ['en/profile'] for q in qrels})
    assert p < 0.05
    result = compare_reports(
        {'runs': {'hybrid': good}},
        {'hybrid': {q: ['en/profile'] for q in qrels}},
        qrels,
        [query(q) for q in qrels],
    )
    assert result['failed'] is True


# ------------------------------------------------------------- committed query data

ROOT = Path(__file__).resolve().parents[2]
KINDS = {
    'direct',
    'relationship',
    'multi-hop',
    'temporal',
    'metric',
    'education',
    'no-answer',
}


def test_committed_queries_are_stratified_derived_and_not_holdout():
    queries = load_queries(ROOT / 'evals' / 'retrieval' / 'queries.jsonl')
    assert 140 <= len(queries) <= 170
    assert {q['kind'] for q in queries} == KINDS
    assert {q['locale'] for q in queries} == {'en', 'es'}
    assert sum(1 for q in queries if q['cross_lingual']) >= 20
    for q in queries:
        assert q['source_id'] and q['source_type'] in {
            'golden',
            'legacy_retrieval',
            'legacy_family',
        }
        assert 'holdout' not in q['source_id']
    golden_ids = {
        json.loads(line)['id']
        for line in (ROOT / 'evals' / 'golden' / 'golden.jsonl')
        .read_text()
        .splitlines()
    }
    for q in queries:
        if q['source_type'] == 'golden':
            assert q['source_id'].split('+')[0] in golden_ids


def test_candidates_cover_every_query_with_all_locale_topic_keys():
    queries = load_queries(ROOT / 'evals' / 'retrieval' / 'queries.jsonl')
    candidates = harness.read_jsonl(
        ROOT / 'evals' / 'retrieval' / 'qrels.candidates.jsonl'
    )
    assert [c['query_id'] for c in candidates] == [q['id'] for q in queries]
    expected = {
        f'{loc}/{t}'
        for loc in ('en', 'es')
        for t in ('profile', 'experience', 'projects', 'education')
    }
    for c in candidates:
        assert {item['key'] for item in c['candidates']} == expected
        assert all(item['proposed'] in (0, 1, 2) for item in c['candidates'])
    by_id = {q['id']: q for q in queries}
    for c in candidates:
        proposed = [i['key'] for i in c['candidates'] if i['proposed']]
        if not by_id[c['query_id']]['expects_evidence']:
            assert proposed == []
        else:
            assert proposed
            # relevance is proposed only in the locale the pipeline answers in
            assert all(
                k.startswith(by_id[c['query_id']]['locale'] + '/') for k in proposed
            )


def test_derivation_is_deterministic():
    from evals.harness.derive_queries import build, dumps

    builder = build()
    assert (
        dumps(builder.queries) == (ROOT / 'evals/retrieval/queries.jsonl').read_text()
    )
    assert (
        dumps(builder.candidates)
        == (ROOT / 'evals/retrieval/qrels.candidates.jsonl').read_text()
    )
