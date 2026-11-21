"""Run import-linter in-process without leaking its logging configuration."""

import logging

from click.testing import CliRunner, Result
from importlinter.cli import lint_imports_command


def invoke_lint_imports(args: list[str]) -> Result:
    """Invoke `lint-imports`, then re-enable loggers its `dictConfig` call disabled.

    The CLI configures logging with `disable_existing_loggers` left at its default (True), which
    would silence the application's loggers for the rest of the test session.
    """
    loggers = [
        logger
        for logger in logging.Logger.manager.loggerDict.values()
        if isinstance(logger, logging.Logger)
    ]
    disabled = {logger: logger.disabled for logger in loggers}
    try:
        return CliRunner().invoke(lint_imports_command, args)
    finally:
        for logger, state in disabled.items():
            logger.disabled = state
