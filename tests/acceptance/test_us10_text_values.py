"""Bindings for specs/acceptance-specs/US10-text-values.feature."""

import pytest
from pytest_bdd import scenarios

pytestmark = pytest.mark.acceptance

scenarios('US10-text-values.feature')
