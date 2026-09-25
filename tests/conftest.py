"""Hypothesis settings profiles (plan.md § Performance Considerations).

`gate` (the default, loaded whenever `HYPOTHESIS_PROFILE` is unset) is what
the commit gate and CI run: deterministic (`derandomize=True`) and a few
hundred examples per property, fast enough not to slow the loop down. `fuzz`
(selected by `HYPOTHESIS_PROFILE=fuzz`, wired to `just fuzz`) trades
determinism for volume: several thousand examples per property, run by hand
to hunt for rare counterexamples.
"""

from __future__ import annotations

import os

from hypothesis import HealthCheck, settings

settings.register_profile(
    'gate',
    deadline=None,
    derandomize=True,
    max_examples=300,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much, HealthCheck.data_too_large],
)
settings.register_profile(
    'fuzz',
    deadline=None,
    derandomize=False,
    max_examples=5000,
    print_blob=True,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much, HealthCheck.data_too_large],
)
settings.load_profile(os.environ.get('HYPOTHESIS_PROFILE', 'gate'))
