"""Hypothesis profiles for the property lane: ``ci`` on every PR, ``nightly`` on schedule."""

import os

from hypothesis import HealthCheck, settings

settings.register_profile(
    'ci',
    max_examples=100,
    derandomize=True,
    deadline=None,
    print_blob=True,
    suppress_health_check=[HealthCheck.too_slow],
)
settings.register_profile(
    'nightly',
    max_examples=1000,
    derandomize=False,
    deadline=None,
    print_blob=True,
    suppress_health_check=[HealthCheck.too_slow],
)
settings.load_profile(os.environ.get('HYPOTHESIS_PROFILE', 'ci'))
