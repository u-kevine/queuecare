from tests.conftest import auth


class TestRegistration:
    def test_register_returns_created_user(self, client):
        response = client.post("/auth/register", json={
            "name": "Aline",
            "email": "aline@queuecare.io",
            "password": "Passw0rd!",
            "role": "patient",
        })

        assert response.status_code == 201
        body = response.json()
        assert body["email"] == "aline@queuecare.io"
        assert body["role"] == "patient"
        assert "password" not in body

    def test_duplicate_email_is_rejected(self, client):
        payload = {
            "name": "Aline",
            "email": "aline@queuecare.io",
            "password": "Passw0rd!",
        }
        client.post("/auth/register", json=payload)

        response = client.post("/auth/register", json=payload)

        assert response.status_code == 409

    def test_email_is_case_insensitive(self, client):
        client.post("/auth/register", json={
            "name": "Aline",
            "email": "aline@queuecare.io",
            "password": "Passw0rd!",
        })

        response = client.post("/auth/register", json={
            "name": "Impostor",
            "email": "ALINE@queuecare.io",
            "password": "Passw0rd!",
        })

        assert response.status_code == 409

    def test_invalid_email_format_is_rejected(self, client):
        response = client.post("/auth/register", json={
            "name": "Aline",
            "email": "not-an-email",
            "password": "Passw0rd!",
        })

        assert response.status_code == 400

    def test_missing_fields_are_rejected(self, client):
        response = client.post("/auth/register", json={"email": "a@queuecare.io"})

        assert response.status_code == 400


class TestLogin:
    def test_login_returns_token_and_role(self, client):
        client.post("/auth/register", json={
            "name": "Aline",
            "email": "aline@queuecare.io",
            "password": "Passw0rd!",
            "role": "staff",
        })

        response = client.post("/auth/login", json={
            "email": "aline@queuecare.io",
            "password": "Passw0rd!",
        })

        assert response.status_code == 200
        body = response.json()
        assert body["access_token"]
        assert body["token_type"] == "bearer"
        assert body["role"] == "staff"

    def test_wrong_password_returns_401(self, client):
        client.post("/auth/register", json={
            "name": "Aline",
            "email": "aline@queuecare.io",
            "password": "Passw0rd!",
        })

        response = client.post("/auth/login", json={
            "email": "aline@queuecare.io",
            "password": "WrongPassword",
        })

        assert response.status_code == 401

    def test_unknown_email_returns_401(self, client):
        response = client.post("/auth/login", json={
            "email": "ghost@queuecare.io",
            "password": "Passw0rd!",
        })

        assert response.status_code == 401


class TestProtectedEndpoints:
    def test_no_token_returns_401(self, client):
        assert client.get("/appointments").status_code == 401

    def test_invalid_token_returns_401(self, client):
        response = client.get("/appointments", headers=auth("clearly-not-valid"))

        assert response.status_code == 401

    def test_valid_token_identifies_the_user(self, client, patient_token):
        response = client.get("/auth/me", headers=auth(patient_token))

        assert response.status_code == 200
        assert response.json()["email"] == "patient@queuecare.io"
