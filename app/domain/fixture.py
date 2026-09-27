import re


def fixture_message(question: str, evidence: str, locale: str) -> str:
    # A deterministic excerpt viewer, not a model-quality simulation.
    insufficient = (
        'No encontré evidencia pública suficiente para responder con certeza.'
        if locale == 'es'
        else 'I could not find enough public evidence to answer confidently.'
    )
    if not evidence:
        return insufficient
    if 'PUBLIC SOURCE ' in evidence:
        from .evidence import ALIASES, tokens

        terms = tokens(question)
        expanded = terms | set().union(*(ALIASES.get(term, set()) for term in terms))
        excerpts = []
        for block in evidence.split('PUBLIC SOURCE ')[1:3]:
            lines = block.splitlines()[1:]
            intent = set()
            if terms & {'technology', 'technologies', 'tecnologias', 'stack'}:
                intent = {'stack', 'technologyNames'}
            elif terms & {'study', 'studied', 'estudio', 'estudios'}:
                intent = {'institution', 'qualification', 'institucion', 'titulo'}
            elif terms & {'work', 'trabajo', 'rampy'}:
                intent = {'contributions', 'context', 'position'}
            elif terms & {'built', 'build', 'portfolio'}:
                intent = {'Application', 'Engineering at a glance', 'Next.js'}
            ranked = sorted(
                range(len(lines)),
                key=lambda index: (
                    -3
                    * any(marker.lower() in lines[index].lower() for marker in intent)
                    - len(tokens(lines[index]) & expanded),
                    index,
                ),
            )
            if not ranked:
                continue
            if not (tokens(lines[ranked[0]]) & expanded) and not any(
                marker.lower() in lines[ranked[0]].lower() for marker in intent
            ):
                continue
            center = ranked[0]
            start = max(0, center - 2)
            end = min(len(lines), center + 13)
            snippet = '\n'.join(lines[start:end]).replace('```', '   ')
            if re.search(
                r'(?i)ignore (all |previous |prior )?instructions|reveal (the |your )?(system prompt|secret|api key)|you are now',
                snippet,
            ):
                continue
            excerpts.append(f'```text\n{snippet[:850]}\n```')
        if excerpts:
            heading = (
                'Fragmentos de fuentes públicas (modo de prueba):'
                if locale == 'es'
                else 'Public source excerpts (fixture mode):'
            )
            return heading + '\n\n' + '\n\n'.join(excerpts)
        return insufficient
    keywords = query_terms(question)
    quoted = [
        part.strip()
        for part in re.findall(r'"([^"\n]{25,})"', evidence)
        if not part.startswith(('http:', 'https:'))
        and 'github.com/' not in part
        and not re.search(
            r'(?i)ignore (all |previous |prior )?instructions|reveal (the |your )?(system prompt|secret|api key)|you are now',
            part,
        )
    ]
    matching = [
        part for part in quoted if any(word in part.lower() for word in keywords)
    ]
    excerpts = (
        matching if matching else quoted if 'filomena' in question.lower() else []
    )[:3]
    if not excerpts:
        return insufficient
    heading = (
        'Resultado de prueba basado en fragmentos públicos:'
        if locale == 'es'
        else 'Fixture result from public source excerpts:'
    )
    return heading + '\n\n' + '\n'.join(f'• {part[:250]}' for part in excerpts)


def query_terms(question: str) -> set[str]:
    stop = {
        'about',
        'could',
        'does',
        'donde',
        'estoy',
        'explain',
        'hacer',
        'please',
        'portfolio',
        'puedes',
        'sobre',
        'their',
        'these',
        'those',
        'where',
        'which',
        'would',
        'tell',
        'what',
    }
    return {
        word
        for word in re.findall(r'\w+', question.lower())
        if len(word) >= 5 and word not in stop
    }
