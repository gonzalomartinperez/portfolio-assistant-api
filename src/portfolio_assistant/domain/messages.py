"""Locale text shared across layers."""


def insufficient_message(locale: str) -> str:
    return (
        "No tengo información pública suficiente para confirmar ese dato."
        if locale == "es"
        else "I don't have enough public information to confirm that."
    )
