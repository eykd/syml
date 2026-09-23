"""Bindings for specs/acceptance-specs/US03-line-lexing.feature."""

import pytest
from pytest_bdd import scenarios

pytestmark = pytest.mark.acceptance

scenarios('US03-line-lexing.feature')
