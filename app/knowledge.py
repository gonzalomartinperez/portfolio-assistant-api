import hashlib
import math
import re


def embed(text: str) -> str:
    values = [0.0] * 64
    for word in re.findall(r'[\w]+', text.lower()):
        digest = hashlib.sha256(word.encode()).digest()
        values[digest[0] % 64] += -1 if digest[1] & 1 else 1
    norm = math.sqrt(sum(value * value for value in values)) or 1
    return '[' + ','.join(str(value / norm) for value in values) + ']'
