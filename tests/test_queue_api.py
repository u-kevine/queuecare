from tests.conftest import TODAY, TOMORROW, auth


class TestTodaysQueue:
    def test_queue_is_ordered_by_queue_number(
        self, client, staff_token, patient_token, other_patient_token
    ):
        client.post(
            "/appointments",
            json={"doctor": "Dr Uwase", "reason": "Checkup", "date": str(TODAY)},
            headers=auth(patient_token),
        )
        client.post(
            "/appointments",
            json={"doctor": "Dr Keza", "reason": "Follow-up", "date": str(TODAY)},
            headers=auth(other_patient_token),
        )

        response = client.get("/queue/today", headers=auth(staff_token))

        assert response.status_code == 200
        assert [a["queue_number"] for a in response.json()] == [1, 2]

    def test_queue_excludes_other_days(self, client, staff_token, patient_token):
        client.post(
            "/appointments",
            json={"doctor": "Dr Uwase", "reason": "Checkup", "date": str(TOMORROW)},
            headers=auth(patient_token),
        )

        response = client.get("/queue/today", headers=auth(staff_token))

        assert response.json() == []

    def test_queue_excludes_cancelled_appointments(
        self, client, staff_token, patient_token, booking
    ):
        client.delete(f"/appointments/{booking['id']}", headers=auth(patient_token))

        response = client.get("/queue/today", headers=auth(staff_token))

        assert response.json() == []

    def test_queue_requires_authentication(self, client):
        assert client.get("/queue/today").status_code == 401


class TestMarkServed:
    def test_staff_can_mark_a_patient_as_served(self, client, staff_token, booking):
        response = client.post(
            f"/queue/{booking['id']}/serve", headers=auth(staff_token)
        )

        assert response.status_code == 200
        assert response.json()["status"] == "served"

    def test_patient_cannot_mark_anyone_as_served(self, client, patient_token, booking):
        response = client.post(
            f"/queue/{booking['id']}/serve", headers=auth(patient_token)
        )

        assert response.status_code == 403

    def test_serving_twice_is_handled_gracefully(self, client, staff_token, booking):
        client.post(f"/queue/{booking['id']}/serve", headers=auth(staff_token))

        response = client.post(
            f"/queue/{booking['id']}/serve", headers=auth(staff_token)
        )

        assert response.status_code == 409
        assert "already been served" in response.json()["detail"].lower()

    def test_cancelled_appointment_cannot_be_served(
        self, client, staff_token, patient_token, booking
    ):
        client.delete(f"/appointments/{booking['id']}", headers=auth(patient_token))

        response = client.post(
            f"/queue/{booking['id']}/serve", headers=auth(staff_token)
        )

        assert response.status_code == 409

    def test_serving_an_unknown_appointment_returns_404(self, client, staff_token):
        response = client.post("/queue/9999/serve", headers=auth(staff_token))

        assert response.status_code == 404

    def test_serving_requires_authentication(self, client, booking):
        assert client.post(f"/queue/{booking['id']}/serve").status_code == 401
