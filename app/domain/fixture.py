import re


def metric_excerpts(content: str) -> list[str]:
    """Keep metric value, label and qualification together for output and attribution."""
    content = re.sub(r'"\s*\+\s*"', '', content)
    return [
        f'{label}: {value}. {qualifier}'
        for value, label, qualifier in re.findall(
            r'value:\s*"([^"\n]+)",\s*label:\s*"([^"\n]+)",\s*qualifier:\s*"([^"\n]+)"',
            content,
        )
    ]


def fixture_supports(content: str, answer: str, path: str) -> bool:
    """Match emitted deterministic excerpts, including short qualified metrics."""
    content = re.sub(r'"\s*\+\s*"', '', content)
    if any(text in answer for text in metric_excerpts(content)):
        return True
    if any(text in answer for text in re.findall(r'"([^"\n]{25,})"', content)):
        return True
    if any(
        label in answer
        for label in ('Documented technologies:', 'Tecnologías documentadas:')
    ):
        for stack in re.findall(r'technologyNames\(\[([^]]+)', content, re.DOTALL):
            names = re.findall(r'"([^"\n]+)"', stack)[:20]
            if names and ', '.join(names) in answer:
                return True
    return path == 'README.md' and any(
        line.strip() in answer
        for line in content.splitlines()
        if len(line.strip()) > 40
    )


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
        excerpts: list[str] = []
        subject = ''
        concise = bool(terms & {'shorter', 'brief', 'breve'})
        for block in evidence.split('PUBLIC SOURCE ')[1:3]:
            content = re.sub(r'/\*.*?\*/', '', block, flags=re.DOTALL)
            content = re.sub(
                r'^\s*(?:availability|seniority):.*$', '', content, flags=re.MULTILINE
            )
            affiliation = re.search(
                r'\b(?:at|for|en)\s+([A-Z][\w.-]+(?: [A-Z][\w.-]+){0,3})', question
            )
            companies = re.findall(r'company:\s*"([^"\n]+)"', content)
            if (
                affiliation
                and companies
                and not any(tokens(name) & tokens(affiliation[1]) for name in companies)
            ):
                continue
            # Join only literal concatenations; never evaluate source code.
            content = re.sub(r'"\s*\+\s*"', '', content)
            if not excerpts:
                names = re.findall(
                    r'(?:name|company|tagline):\s*"([^"\n]{1,120})"', content
                )
                subject = ' — '.join(names[:2])

            if terms & {'technologies', 'technology', 'tecnologias', 'stack'}:
                stacks = re.findall(r'technologyNames\(\[([^]]*)', content, re.DOTALL)
                technologies = [
                    name
                    for stack in stacks
                    for name in re.findall(r'"([^"\n]+)"', stack)
                ]
                if technologies:
                    excerpts.append(
                        (
                            'Tecnologías documentadas: '
                            if locale == 'es'
                            else 'Documented technologies: '
                        )
                        + ', '.join(technologies[:20])
                        + '.'
                    )
                    continue
            if block.splitlines()[0].startswith('README.md'):
                prose = [
                    line.strip()
                    for line in content.splitlines()[1:]
                    if len(line.strip()) > 40 and not line.startswith(('#', '```'))
                ]
                ranked_prose = sorted(
                    prose, key=lambda line: -len(tokens(line) & expanded)
                )
                excerpts.extend(ranked_prose[: 1 if concise else 2])
                continue
            candidates = re.findall(r'"([^"\n]{25,})"', content)
            if (
                re.search(
                    r'(?i)(tell me about|cu[eé]ntame sobre|who is|qui[eé]n es)\s+gonzalo',
                    question,
                )
                and '/profile.ts' in block.splitlines()[0]
            ):
                candidates = re.findall(r'(?:intro|summary):\s*"([^"\n]+)"', content)
                excerpts.extend(candidates[:2])
                break
            if terms & {
                'performance',
                'improvements',
                'metrics',
                'metricas',
                'rendimiento',
            }:
                metrics = metric_excerpts(content)
                if metrics:
                    excerpts.extend(metrics[:2])
                    break
            candidates = [
                part
                for part in candidates
                if not re.search(
                    r'(?i)https?://|ignore .*instructions|reveal .*secret|you are now',
                    part,
                )
            ]
            ranked = sorted(
                enumerate(candidates),
                key=lambda item: (-len(tokens(item[1]) & expanded), item[0]),
            )
            selected = [text for _, text in ranked[: 1 if concise else 2]]
            for text in selected:
                if text not in excerpts:
                    excerpts.append(text)
        if not excerpts:
            return insufficient
        # Quotes preserve first-person attribution and qualifications from the source.
        heading = (
            'El perfil público lo describe así (extractos en modo de prueba):'
            if locale == 'es'
            else 'The public profile describes it this way (fixture excerpts):'
        )
        if subject:
            heading += ' ' + subject + '.'
        return (
            heading
            + '\n\n'
            + '\n\n'.join('> ' + text for text in excerpts[: 1 if concise else 2])
        )
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
