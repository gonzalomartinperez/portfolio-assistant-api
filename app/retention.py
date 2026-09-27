"""Compatibility CLI; new code imports app.infrastructure.retention."""

from app.infrastructure.retention import prune

if __name__ == '__main__':
    print(prune())
