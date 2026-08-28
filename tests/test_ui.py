import subprocess
import time
import uuid
from datetime import date, timedelta

import httpx
import pytest
from playwright.sync_api import expect

BASE_URL = "http://127.0.0.1:8001"
TOMORROW = str(date.today() + timedelta(days=1))
PASSWORD = "Passw0rd!"


@pytest.fixture(scope="session")
def server():
    """Start the application on a dedicated port for the duration of the UI run."""
    process = subprocess.Popen(
        ["uvicorn", "app.main:app", "--port", "8001", "--log-level", "warning"]
    )
    for _ in range(40):
        try:
            if httpx.get(f"{BASE_URL}/health", timeout=1).status_code == 200:
                break
        except httpx.HTTPError:
            time.sleep(0.25)
    else:
        process.terminate()
        pytest.fail("Application did not start")

    yield BASE_URL
    process.terminate()
    process.wait()


@pytest.fixture
def patient(server):
    """A fresh account per test, so UI tests never share data."""
    account = {
        "name": "Aline",
        "email": f"patient-{uuid.uuid4().hex[:8]}@queuecare.io",
        "password": PASSWORD,
        "role": "patient",
    }
    httpx.post(f"{server}/auth/register", json=account)
    return account


def sign_in(page, server, email, password):
    page.goto(server)
    page.get_by_test_id("login-email").fill(email)
    page.get_by_test_id("login-password").fill(password)
    page.get_by_test_id("login-submit").click()


class TestLoginFlow:
    def test_valid_credentials_reach_the_dashboard(self, page, server, patient):
        sign_in(page, server, patient["email"], patient["password"])

        expect(page).to_have_url(f"{server}/static/dashboard.html")
        expect(page.get_by_test_id("current-user")).to_contain_text("patient")

    def test_invalid_credentials_show_an_error(self, page, server, patient):
        sign_in(page, server, patient["email"], "WrongPassword")

        expect(page.get_by_test_id("message")).to_contain_text("Invalid email or password")
        expect(page).not_to_have_url(f"{server}/static/dashboard.html")

    def test_empty_form_is_blocked_before_submitting(self, page, server):
        page.goto(server)
        page.get_by_test_id("login-submit").click()

        expect(page.get_by_test_id("message")).to_contain_text("Enter your email and password")

    def test_dashboard_is_not_reachable_without_signing_in(self, page, server):
        page.goto(f"{server}/static/dashboard.html")

        expect(page).to_have_url(f"{server}/")


class TestBookingFlow:
    def test_booking_appears_in_the_list(self, page, server, patient):
        sign_in(page, server, patient["email"], patient["password"])

        page.get_by_test_id("doctor").fill("Dr Uwase")
        page.get_by_test_id("reason").fill("Annual checkup")
        page.get_by_test_id("date").fill(TOMORROW)
        page.get_by_test_id("book-submit").click()

        row = page.get_by_test_id("appointment-row").last
        expect(row.get_by_test_id("appointment-doctor")).to_have_text("Dr Uwase")
        expect(row.get_by_test_id("appointment-status")).to_have_text("booked")
        expect(row.get_by_test_id("queue-number")).not_to_be_empty()

    def test_empty_booking_form_shows_validation_message(self, page, server, patient):
        sign_in(page, server, patient["email"], patient["password"])

        page.get_by_test_id("book-submit").click()

        expect(page.get_by_test_id("message")).to_contain_text("required")
        expect(page.get_by_test_id("appointment-row")).to_have_count(0)

    def test_cancelling_updates_the_status_in_the_list(self, page, server, patient):
        sign_in(page, server, patient["email"], patient["password"])

        page.get_by_test_id("doctor").fill("Dr Keza")
        page.get_by_test_id("reason").fill("Follow-up")
        page.get_by_test_id("date").fill(TOMORROW)
        page.get_by_test_id("book-submit").click()

        row = page.get_by_test_id("appointment-row").last
        row.get_by_test_id("cancel").click()

        expect(page.get_by_test_id("message")).to_contain_text("cancelled")
        expect(
            page.get_by_test_id("appointment-row").last.get_by_test_id("appointment-status")
        ).to_have_text("cancelled")
