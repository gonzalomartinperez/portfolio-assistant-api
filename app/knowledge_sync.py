"""Compatibility CLI; new code imports app.infrastructure.indexing."""

from app.infrastructure.indexing import main, sync

__all__ = ['main', 'sync']

if __name__ == '__main__':
    main()
