"""Operator defaults; persistence adapters receive explicit configuration."""

from decimal import Decimal
from functools import partial

from app.adapters.postgres import checkpoints, db, ledger, retention
from app.bootstrap.config import settings


def connect():
    return db.connect(settings().database_url)


def reserve(
    run_id: str, amount: Decimal, *, connection=connect, cutoff: Decimal | None = None
) -> None:
    ledger.reserve(
        run_id,
        amount,
        connection=connection,
        cutoff=cutoff if cutoff is not None else Decimal(settings().reserve_cutoff_usd),
    )


def settle(
    run_id: str,
    input_tokens: int,
    output_tokens: int,
    *,
    connection=connect,
    input_price: Decimal | None = None,
    output_price: Decimal | None = None,
) -> None:
    ledger.settle(
        run_id,
        input_tokens,
        output_tokens,
        connection=connection,
        input_price=input_price
        if input_price is not None
        else Decimal(settings().input_usd_per_million),
        output_price=output_price
        if output_price is not None
        else Decimal(settings().output_usd_per_million),
    )


def delete_checkpoint(thread_id: str, database_url: str | None = None) -> None:
    checkpoints.delete_checkpoint(thread_id, database_url or settings().database_url)


def drain_cleanup(
    *, connection=connect, database_url: str | None = None, limit: int = 100
) -> int:
    return checkpoints.drain_cleanup(
        connection=connection,
        database_url=database_url or settings().database_url,
        limit=limit,
    )


def prune() -> dict[str, int]:
    config = settings()
    connection = partial(db.connect, config.database_url)
    return retention.prune(
        connection=connection,
        cleanup=lambda: checkpoints.drain_cleanup(
            connection=connection, database_url=config.database_url
        ),
    )
