"""Compatibility CLI; new code imports app.bootstrap.indexing."""

from app.bootstrap.indexing import main, sync

__all__ = ['main', 'sync']

if __name__ == '__main__':
    main()
