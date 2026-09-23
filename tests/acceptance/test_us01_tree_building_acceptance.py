"""Bindings for specs/acceptance-specs/US01-tree-building-acceptance.feature."""

import pytest
from pytest_bdd import scenarios

pytestmark = pytest.mark.acceptance

scenarios('US01-tree-building-acceptance.feature')
