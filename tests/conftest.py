from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from fortigate_8_0_0_copilot.api import app


@pytest.fixture
def client() -> Iterator[TestClient]:
    """Provide a fresh API client for each test that needs one.

    Pytest supplies this fixture to tests that request it, letting them call
    the FortiGate Copilot API without starting a separate server. Application
    startup runs before the test; shutdown and client cleanup run afterward.
    """
    with TestClient(app) as test_client:
        yield test_client
