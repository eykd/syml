"""Bindings for specs/acceptance-specs/US02-preprocessing.feature."""

import pytest
from pytest_bdd import scenarios

pytestmark = pytest.mark.acceptance

scenarios('US02-preprocessing.feature')
