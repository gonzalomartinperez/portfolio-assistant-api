"""Compatibility CLI; new code imports app.bootstrap.knowledge_watch."""

import asyncio

from app.bootstrap.knowledge_watch import run

__all__ = ['run']

if __name__ == '__main__':
    asyncio.run(run())
