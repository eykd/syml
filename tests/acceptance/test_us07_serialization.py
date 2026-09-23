"""Bindings for specs/acceptance-specs/US07-serialization.feature."""

import pytest
from pytest_bdd import scenarios

pytestmark = pytest.mark.acceptance

scenarios('US07-serialization.feature')
