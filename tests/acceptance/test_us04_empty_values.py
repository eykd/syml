"""Bindings for specs/acceptance-specs/US04-empty-values.feature."""

import pytest
from pytest_bdd import scenarios

pytestmark = pytest.mark.acceptance

scenarios('US04-empty-values.feature')
