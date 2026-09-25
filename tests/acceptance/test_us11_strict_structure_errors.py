"""Bindings for specs/acceptance-specs/US11-strict-structure-errors.feature."""

import pytest
from pytest_bdd import scenarios

pytestmark = pytest.mark.acceptance

scenarios('US11-strict-structure-errors.feature')
