from tests.conftest import TODAY, TOMORROW, YESTERDAY, auth


class TestCreateAppointment:
    def test_booking_assigns_a_queue_number(self, client, patient_token):
        response = client.post(
            "/appointments",
            json={"doctor": "Dr Uwase", "reason": "Checkup", "date": str(TODAY)},
            headers=auth(patient_token),
        )

        assert response.status_code == 201
        body = response.json()
        assert body["queue_number"] == 1
        assert body["status"] == "booked"
        assert body["patient_email"] == "patient@queuecare.io"

    def test_queue_numbers_increment_per_day(self, client, patient_token, other_patient_token):
        first = client.post(
            "/appointments",
            json={"doctor": "Dr Uwase", "reason": "Checkup", "date": str(TODAY)},
            headers=auth(patient_token),
        ).json()
        second = client.post(
            "/appointments",
            json={"doctor": "Dr Uwase", "reason": "Checkup", "date": str(TODAY)},
            headers=auth(other_patient_token),
        ).json()

        assert (first["queue_number"], second["queue_number"]) == (1, 2)

    def test_queue_numbering_is_independent_per_date(self, client, patient_token):
        client.post(
            "/appointments",
            json={"doctor": "Dr Uwase", "reason": "Checkup", "date": str(TODAY)},
            headers=auth(patient_token),
        )
        tomorrow = client.post(
            "/appointments",
            json={"doctor": "Dr Uwase", "reason": "Checkup", "date": str(TOMORROW)},
            headers=auth(patient_token),
        ).json()

        assert tomorrow["queue_number"] == 1

    def test_missing_fields_return_400(self, client, patient_token):
        response = client.post(
            "/appointments",
            json={"doctor": "Dr Uwase"},
            headers=auth(patient_token),
        )

        assert response.status_code == 400

    def test_past_date_is_rejected(self, client, patient_token):
        response = client.post(
            "/appointments",
            json={"doctor": "Dr Uwase", "reason": "Checkup", "date": str(YESTERDAY)},
            headers=auth(patient_token),
        )

        assert response.status_code == 400
        assert "past" in response.text.lower()

    def test_invalid_date_format_returns_a_clear_error(self, client, patient_token):
        response = client.post(
            "/appointments",
            json={"doctor": "Dr Uwase", "reason": "Checkup", "date": "12/08/2026"},
            headers=auth(patient_token),
        )

        assert response.status_code == 400
        assert "date" in response.text.lower()

    def test_duplicate_booking_same_day_is_rejected(self, client, patient_token, booking):
        response = client.post(
            "/appointments",
            json={"doctor": "Dr Keza", "reason": "Second opinion", "date": str(TODAY)},
            headers=auth(patient_token),
        )

        assert response.status_code == 409

    def test_rebooking_after_cancellation_is_allowed(self, client, patient_token, booking):
        client.delete(f"/appointments/{booking['id']}", headers=auth(patient_token))

        response = client.post(
            "/appointments",
            json={"doctor": "Dr Keza", "reason": "Rescheduled visit", "date": str(TODAY)},
            headers=auth(patient_token),
        )

        assert response.status_code == 201

    def test_booking_requires_authentication(self, client):
        response = client.post(
            "/appointments",
            json={"doctor": "Dr Uwase", "reason": "Checkup", "date": str(TODAY)},
        )

        assert response.status_code == 401


class TestReadAppointments:
    def test_patient_sees_only_their_own_appointments(
        self, client, patient_token, other_patient_token, booking
    ):
        client.post(
            "/appointments",
            json={"doctor": "Dr Keza", "reason": "Checkup", "date": str(TOMORROW)},
            headers=auth(other_patient_token),
        )

        response = client.get("/appointments", headers=auth(patient_token))

        assert response.status_code == 200
        emails = {a["patient_email"] for a in response.json()}
        assert emails == {"patient@queuecare.io"}

    def test_staff_sees_all_appointments(
        self, client, staff_token, other_patient_token, booking
    ):
        client.post(
            "/appointments",
            json={"doctor": "Dr Keza", "reason": "Checkup", "date": str(TOMORROW)},
            headers=auth(other_patient_token),
        )

        response = client.get("/appointments", headers=auth(staff_token))

        assert len(response.json()) == 2

    def test_fetch_single_appointment_by_id(self, client, patient_token, booking):
        response = client.get(f"/appointments/{booking['id']}", headers=auth(patient_token))

        assert response.status_code == 200
        assert response.json()["id"] == booking["id"]

    def test_unknown_id_returns_404(self, client, patient_token):
        response = client.get("/appointments/9999", headers=auth(patient_token))

        assert response.status_code == 404

    def test_patient_cannot_read_another_patients_appointment(
        self, client, other_patient_token, booking
    ):
        response = client.get(
            f"/appointments/{booking['id']}", headers=auth(other_patient_token)
        )

        assert response.status_code == 403


class TestUpdateAppointment:
    def test_patient_can_reschedule_their_appointment(self, client, patient_token, booking):
        response = client.put(
            f"/appointments/{booking['id']}",
            json={"date": str(TOMORROW), "doctor": "Dr Keza"},
            headers=auth(patient_token),
        )

        assert response.status_code == 200
        body = response.json()
        assert body["date"] == str(TOMORROW)
        assert body["doctor"] == "Dr Keza"

    def test_reschedule_to_past_date_is_rejected(self, client, patient_token, booking):
        response = client.put(
            f"/appointments/{booking['id']}",
            json={"date": str(YESTERDAY)},
            headers=auth(patient_token),
        )

        assert response.status_code == 400

    def test_patient_cannot_update_another_patients_appointment(
        self, client, other_patient_token, booking
    ):
        response = client.put(
            f"/appointments/{booking['id']}",
            json={"reason": "Hijacked"},
            headers=auth(other_patient_token),
        )

        assert response.status_code == 403

    def test_updating_a_cancelled_appointment_is_rejected(
        self, client, patient_token, booking
    ):
        client.delete(f"/appointments/{booking['id']}", headers=auth(patient_token))

        response = client.put(
            f"/appointments/{booking['id']}",
            json={"reason": "Changed my mind"},
            headers=auth(patient_token),
        )

        assert response.status_code == 409


class TestCancelAppointment:
    def test_patient_can_cancel_their_appointment(self, client, patient_token, booking):
        response = client.delete(
            f"/appointments/{booking['id']}", headers=auth(patient_token)
        )

        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"

    def test_cancelling_twice_is_handled_gracefully(self, client, patient_token, booking):
        client.delete(f"/appointments/{booking['id']}", headers=auth(patient_token))

        response = client.delete(
            f"/appointments/{booking['id']}", headers=auth(patient_token)
        )

        assert response.status_code == 409
        assert "already cancelled" in response.json()["detail"].lower()

    def test_patient_cannot_cancel_another_patients_appointment(
        self, client, other_patient_token, booking
    ):
        response = client.delete(
            f"/appointments/{booking['id']}", headers=auth(other_patient_token)
        )

        assert response.status_code == 403
