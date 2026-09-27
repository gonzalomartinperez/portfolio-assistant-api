"""Pure bilingual ranking and provenance policies."""

import hashlib
import re
import unicodedata
from typing import TypedDict
from urllib.parse import quote


class EvidenceRecord(TypedDict):
    path: str
    content: str
    start_line: int
    end_line: int
    url: str
    content_hash: str


STOP = {
    'about',
    'again',
    'como',
    'con',
    'cual',
    'cuales',
    'de',
    'del',
    'did',
    'does',
    'donde',
    'el',
    'ella',
    'en',
    'es',
    'esta',
    'fue',
    'gonzalo',
    'his',
    'how',
    'is',
    'la',
    'las',
    'los',
    'me',
    'que',
    'quien',
    'se',
    'the',
    'this',
    'una',
    'what',
    'when',
    'where',
    'which',
    'who',
    'with',
    'you',
    'your',
}
ALIASES = {
    'ai': {'agents', 'orchestration', 'retrieval', 'reranking'},
    'ia': {'agentes', 'orquestacion', 'recuperacion', 'memoria'},
    'construyo': {'built', 'contributions', 'desarrolle', 'implemente'},
    'performance': {'metrics', 'qualifier', 'baseline', 'measured', 'estimated'},
    'improvements': {'metrics', 'qualifier', 'baseline', 'measured', 'estimated'},
    'decision': {'architecture', 'trade', 'design', 'decision', 'decisiones'},
    'learn': {'education', 'qualification', 'studies'},
    'study': {'education', 'university', 'universidad', 'studies', 'estudios'},
    'studied': {'education', 'university', 'universidad', 'studies', 'estudios'},
    'estudio': {'education', 'university', 'universidad', 'estudios'},
    'estudios': {'education', 'university', 'universidad'},
    'built': {
        'architecture',
        'stack',
        'technology',
        'engineering',
        'application',
        'desarrollo',
    },
    'build': {
        'architecture',
        'stack',
        'technology',
        'engineering',
        'application',
        'desarrollo',
    },
    'technologies': {'stack', 'technology', 'tecnologias'},
    'tecnologias': {'stack', 'technology', 'technologies'},
    'work': {'role', 'experience', 'trabajo'},
    'trabajo': {'role', 'experience', 'work'},
}


def tokens(text: str) -> set[str]:
    normalized = unicodedata.normalize('NFKD', text.lower())
    normalized = ''.join(char for char in normalized if not unicodedata.combining(char))
    return {
        word
        for word in re.findall(r'[a-z0-9]+', normalized)
        if (len(word) > 2 or word in {'ai', 'ia'}) and word not in STOP
    }


def lexical_score(row: EvidenceRecord, terms: set[str], locale: str) -> float:
    content = tokens(row['content'])
    path = tokens(row['path'])
    if row['path'] == 'README.md':
        path.add('portfolio')
    expanded = terms | set().union(*(ALIASES.get(term, set()) for term in terms))
    anchors = expanded & (content | path)
    if not anchors:
        return 0
    score = (
        3.0 * len(terms & (content | path)) + len(anchors) + 2 * len(expanded & path)
    )
    if 'portfolio' in terms and row['path'] == 'README.md':
        score *= 2
        if 'Engineering at a glance' in row['content']:
            score *= 5
    if (
        terms & {'study', 'studied', 'estudio', 'estudios'}
        and row['path'].endswith('/education.ts')
        and row['start_line'] == 1
    ):
        score *= 5
    if (
        row['path'].endswith('/experience.ts')
        and 'contributions:' in row['content']
        and terms & content
    ):
        score *= 3
    if row['path'].endswith('/projects.ts') and terms & content:
        tech = bool(terms & {'technologies', 'technology', 'tecnologias', 'stack'})
        if (tech and 'stack: technologyNames' in row['content']) or (
            not tech and 'summary:' in row['content']
        ):
            score *= 3
    if row['path'].startswith(f'src/content/{locale}/'):
        score *= 1.35
    elif row['path'].startswith('src/content/'):
        score *= 0.45
    return score


def verified(row: EvidenceRecord, source_commit: str, known_paths: set[str]) -> bool:
    path = row['path']
    if (
        path not in known_paths
        or row['start_line'] < 1
        or row['end_line'] < row['start_line']
    ):
        return False
    expected = f'https://github.com/gonzalomartinperez/portfolio/blob/{source_commit}/{quote(path, safe="/")}#L{row["start_line"]}-L{row["end_line"]}'
    return (
        row['url'] == expected
        and hashlib.sha256(row['content'].encode()).hexdigest() == row['content_hash']
    )
