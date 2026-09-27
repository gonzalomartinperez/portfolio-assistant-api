"""Compatibility entry point; implementation lives in app.infrastructure.retention."""

from app.infrastructure.retention import *

if __name__ == '__main__':
    print(prune())
