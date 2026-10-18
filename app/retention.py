"""Compatibility CLI; new code imports app.bootstrap.maintenance."""

from app.bootstrap.maintenance import prune

if __name__ == '__main__':
    print(prune())
