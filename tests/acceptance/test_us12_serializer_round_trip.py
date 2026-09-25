"""Bindings for specs/acceptance-specs/US12-serializer-round-trip.feature."""

import pytest
from pytest_bdd import scenarios

pytestmark = pytest.mark.acceptance

scenarios('US12-serializer-round-trip.feature')
