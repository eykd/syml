"""Bindings for specs/acceptance-specs/US09-release-readiness.feature."""

import pytest
from pytest_bdd import scenarios

pytestmark = pytest.mark.acceptance

scenarios('US09-release-readiness.feature')
