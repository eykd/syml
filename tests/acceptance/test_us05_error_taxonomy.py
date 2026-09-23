"""Bindings for specs/acceptance-specs/US05-error-taxonomy.feature."""

import pytest
from pytest_bdd import scenarios

pytestmark = pytest.mark.acceptance

scenarios('US05-error-taxonomy.feature')
