"""Bindings for specs/acceptance-specs/US08-source-tracking.feature."""

import pytest
from pytest_bdd import scenarios

pytestmark = pytest.mark.acceptance

scenarios('US08-source-tracking.feature')
