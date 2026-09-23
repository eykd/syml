"""Bindings for specs/acceptance-specs/US06-quoted-strings.feature."""

import pytest
from pytest_bdd import scenarios

pytestmark = pytest.mark.acceptance

scenarios('US06-quoted-strings.feature')
