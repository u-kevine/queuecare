from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app import store
from app.main import app

TODAY = date.today()
TOMORROW = TODAY + timedelta(days=1)
YESTERDAY = TODAY - timedelta(days=1)


@pytest.fixture(autouse=True)
def clean_state():
    """Guarantee test isolation: every test starts from an empty store."""
    store.reset()
    yield
    store.reset()


@pytest.fixture
def client():
    return TestClient(app)


def register_and_login(client, email, role="patient", password="Passw0rd!"):
    client.post("/auth/register", json={
        "name": email.split("@")[0],
        "email": email,
        "password": password,
        "role": role,
    })
    response = client.post("/auth/login", json={"email": email, "password": password})
    return response.json()["access_token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def patient_token(client):
    return register_and_login(client, "patient@queuecare.io", "patient")


@pytest.fixture
def other_patient_token(client):
    return register_and_login(client, "other@queuecare.io", "patient")


@pytest.fixture
def staff_token(client):
    return register_and_login(client, "staff@queuecare.io", "staff")


@pytest.fixture
def booking(client, patient_token):
    """An active appointment for today, owned by the patient fixture."""
    response = client.post(
        "/appointments",
        json={"doctor": "Dr Uwase", "reason": "Consultation", "date": str(TODAY)},
        headers=auth(patient_token),
    )
    return response.json()
