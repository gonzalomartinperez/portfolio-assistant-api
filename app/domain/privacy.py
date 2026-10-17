"""Best-effort minimization of common visitor identifiers, never public evidence."""

import re

EMAIL = re.compile(r'(?i)\b[A-Z0-9._%+-]{1,64}@[A-Z0-9.-]{1,253}\.[A-Z]{2,63}\b')
PHONE = re.compile(r'(?<!\w)\+[0-9][0-9 ()-]{8,62}[0-9](?!\w)')
SECRET = re.compile(
    r'\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}|\bBearer [A-Za-z0-9._~+/=-]{16,}', re.IGNORECASE
)


def minimize_visitor_text(text: str) -> str:
    """Keep context useful without forwarding common contact/key patterns.

    This is not complete PII detection or an erasure policy. Replacements never
    increase character bounds; authoritative public evidence must not use it.
    """
    result = SECRET.sub('(secret)', text)
    if '@' in result:
        result = EMAIL.sub(
            lambda match: '(email)' if len(match[0]) >= 7 else '(…)', result
        )
    if '+' in result:
        result = PHONE.sub(
            lambda match: (
                '(phone)'
                if sum(char.isdigit() for char in match[0]) >= 10
                else match[0]
            ),
            result,
        )
    return result
