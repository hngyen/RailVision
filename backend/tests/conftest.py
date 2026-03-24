import importlib
import os
import sys
from typing import Generator

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def client() -> Generator[TestClient, None, None]:
    os.environ["RAILVISION_ENABLE_SCHEDULER"] = "0"

    if "main" in sys.modules:
        del sys.modules["main"]

    main = importlib.import_module("main")
    with TestClient(main.app) as test_client:
        yield test_client
