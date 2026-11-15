"""``assistant-retention``: prune expired data (scheduled by vps-ops)."""


def main() -> None:
    """Prune expired data like ``python -m app.retention`` and print the counts."""
    from app.bootstrap.maintenance import prune

    print(prune())
