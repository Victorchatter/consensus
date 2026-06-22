import pytest
from fastapi.testclient import TestClient
import sys
import os

# Ensure backend root is on path for 'main' import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from main import app

client = TestClient(app)


def test_healthcheck():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_backtest_list():
    response = client.get("/backtest/")
    assert response.status_code in (200, 401)
