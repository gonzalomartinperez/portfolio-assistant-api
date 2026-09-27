class RejectedError(Exception):
    """A safe, public application error code; never includes provider/DB details."""

    def __init__(self, code: str, status: int = 400):
        super().__init__(code)
        self.code = code
        self.status = status


class BudgetExhaustedError(Exception):
    pass


class DependencyUnavailableError(Exception):
    """An I/O dependency failed; details must stay outside application contracts."""
