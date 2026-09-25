"""Bindings for specs/acceptance-specs/US13-release-documents.feature."""

import pytest
from pytest_bdd import scenarios

pytestmark = pytest.mark.acceptance

scenarios('US13-release-documents.feature')
