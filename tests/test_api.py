from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.database import reset_engine


@pytest.fixture
def client(tmp_path):
    settings.data_dir = tmp_path
    settings.api_key = "test-key"
    settings.seed_demo = True
    settings.session_secret = "test-session-secret"
    reset_engine()
    from app.main import app

    with TestClient(app) as test_client:
        yield test_client


def auth():
    return {"X-API-Key": "test-key"}


def test_health_is_public(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_api_rejects_missing_key(client):
    assert client.get("/api/v1/overview").status_code == 401


def test_demo_seed_and_overview(client):
    overview = client.get("/api/v1/overview", headers=auth()).json()
    assert overview["household"] == "Familien"
    assert len(overview["months"]) == 12
    assert overview["months"][0]["income_dkk"] == 70000
    assert overview["this_month_net_ore"] != 0
    sensors = client.get("/api/v1/ha/sensors", headers=auth()).json()
    assert "naeste_maaned_netto" in sensors
    assert len(sensors["sensors"]) >= 6
    ics = client.get("/api/v1/ha/calendar.ics", headers=auth())
    assert ics.status_code == 200
    assert "BEGIN:VEVENT" in ics.text


def test_n8n_can_create_subscription_with_external_id(client):
    payload = {
        "name": "HBO Max",
        "amount_dkk": 89,
        "cadence": "monthly",
        "charge_rule": "day_of_month",
        "charge_day": 21,
        "starts_on": date.today().isoformat(),
        "category": "abonnement",
        "external_id": "n8n-hbo-max",
    }
    created = client.post("/api/v1/subscriptions", headers=auth(), json=payload)
    assert created.status_code == 201
    again = client.post("/api/v1/subscriptions", headers=auth(), json=payload)
    assert again.status_code == 201
    assert again.json()["created"] is False
    items = client.get("/api/v1/items?kind=expense", headers=auth()).json()
    matches = [i for i in items if i["external_id"] == "n8n-hbo-max"]
    assert len(matches) == 1
    assert matches[0]["continues_until_removed"] is True


def test_settings_returns_env_api_key(client):
    data = client.get("/api/v1/settings", headers=auth()).json()
    assert data["api_key"] == "test-key"


def test_ui_pages_render(client):
    for path in ("/", "/poster", "/personer", "/konti", "/skat", "/indstillinger"):
        response = client.get(path)
        assert response.status_code == 200, path
        assert "Fælleskassen" in response.text
