import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.database import reset_engine


@pytest.fixture
def fresh(tmp_path):
    settings.data_dir = tmp_path
    settings.api_key = "test-key"
    settings.seed_demo = False
    settings.app_password = ""
    settings.session_secret = "test-session-secret"
    reset_engine()
    from app.main import app

    with TestClient(app) as test_client:
        yield test_client


def test_fresh_start_opens_setup_guide(fresh):
    response = fresh.get("/", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/opsaetning"
    page = fresh.get("/opsaetning")
    assert page.status_code == 200
    assert "Første opsætning" in page.text
    assert "administrator" in page.text.lower()


def test_first_person_is_admin_with_password(fresh):
    created = fresh.post(
        "/opsaetning",
        data={
            "household_name": "Huset",
            "municipal_tax_pct": "25.05",
            "church_tax_pct": "0",
            "is_couple": "1",
            "admin_name": "Mie",
            "admin_password": "hemmelig1",
            "admin_password2": "hemmelig1",
            "other_name_1": "Bo",
            "other_name_2": "",
            "other_name_3": "",
        },
        follow_redirects=False,
    )
    assert created.status_code == 303
    home = fresh.get("/")
    assert home.status_code == 200
    assert "Huset" in home.text
    assert "Mie" in home.text
    assert "admin" in home.text
    assert "Bo" in home.text
    assert "Husstanden er tom" in home.text

    fresh.get("/logout")
    denied = fresh.get("/", follow_redirects=False)
    assert denied.status_code == 303
    assert denied.headers["location"] == "/login"

    as_bo = fresh.post("/login", data={"name": "Bo", "password": "hemmelig1"}, follow_redirects=False)
    assert as_bo.status_code == 303
    assert as_bo.headers["location"] == "/login"

    as_mie = fresh.post("/login", data={"name": "Mie", "password": "hemmelig1"}, follow_redirects=False)
    assert as_mie.status_code == 303
    assert as_mie.headers["location"] == "/"


def test_login_person_needs_password(fresh):
    fail = fresh.post(
        "/opsaetning",
        data={
            "household_name": "Huset",
            "admin_name": "Mie",
            "admin_password": "hemmelig1",
            "admin_password2": "hemmelig1",
            "other_name_1": "Kai",
            "other_login_1": "1",
            "other_password_1": "kort",
        },
        follow_redirects=False,
    )
    assert fail.status_code == 303
    assert fail.headers["location"] == "/opsaetning"
    page = fresh.get("/opsaetning")
    assert "mindst 8 tegn" in page.text
