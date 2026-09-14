"""Shared fixtures for pytest-bdd acceptance tests."""

from typing import Any

import pytest


@pytest.fixture
def context() -> dict[str, Any]:
    """Mutable scratch space carried between Given/When/Then steps of one scenario."""
    return {}
