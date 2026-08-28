from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status

from app import store
from app.auth import STAFF_ROLES, get_current_user, require_staff
from app.schemas import AppointmentCreate, AppointmentResponse, AppointmentUpdate

router = APIRouter(tags=["appointments"])

ACTIVE = "booked"
CANCELLED = "cancelled"
SERVED = "served"


def next_queue_number(day: date) -> int:
    same_day = [
        a for a in store.appointments.values()
        if a["date"] == day and a["status"] != CANCELLED
    ]
    return len(same_day) + 1


def has_active_booking(email: str, day: date) -> bool:
    return any(
        a["patient_email"] == email
        and a["date"] == day
        and a["status"] != CANCELLED
        for a in store.appointments.values()
    )


def get_appointment_or_404(appointment_id: int) -> dict:
    appointment = store.appointments.get(appointment_id)
    if appointment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found",
        )
    return appointment


def ensure_can_access(appointment: dict, user: dict) -> None:
    if user["role"] in STAFF_ROLES:
        return
    if appointment["patient_email"] != user["email"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own appointments",
        )


@router.post(
    "/appointments",
    response_model=AppointmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_appointment(
    payload: AppointmentCreate,
    user: dict = Depends(get_current_user),
):
    if has_active_booking(user["email"], payload.date):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already have an appointment booked on this date",
        )

    appointment = {
        "id": store.next_appointment_id(),
        "patient_email": user["email"],
        "doctor": payload.doctor,
        "reason": payload.reason,
        "date": payload.date,
        "status": ACTIVE,
        "queue_number": next_queue_number(payload.date),
    }
    store.appointments[appointment["id"]] = appointment
    return appointment


@router.get("/appointments", response_model=list[AppointmentResponse])
def list_appointments(user: dict = Depends(get_current_user)):
    if user["role"] in STAFF_ROLES:
        return list(store.appointments.values())
    return [
        a for a in store.appointments.values()
        if a["patient_email"] == user["email"]
    ]


@router.get("/appointments/{appointment_id}", response_model=AppointmentResponse)
def get_appointment(appointment_id: int, user: dict = Depends(get_current_user)):
    appointment = get_appointment_or_404(appointment_id)
    ensure_can_access(appointment, user)
    return appointment


@router.put("/appointments/{appointment_id}", response_model=AppointmentResponse)
def update_appointment(
    appointment_id: int,
    payload: AppointmentUpdate,
    user: dict = Depends(get_current_user),
):
    appointment = get_appointment_or_404(appointment_id)
    ensure_can_access(appointment, user)

    if appointment["status"] != ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot update an appointment that is {appointment['status']}",
        )

    updates = payload.model_dump(exclude_none=True)

    new_date = updates.get("date")
    if new_date and new_date != appointment["date"]:
        if has_active_booking(appointment["patient_email"], new_date):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You already have an appointment booked on this date",
            )
        appointment["queue_number"] = next_queue_number(new_date)

    appointment.update(updates)
    return appointment


@router.delete("/appointments/{appointment_id}", response_model=AppointmentResponse)
def cancel_appointment(appointment_id: int, user: dict = Depends(get_current_user)):
    appointment = get_appointment_or_404(appointment_id)
    ensure_can_access(appointment, user)

    if appointment["status"] == CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Appointment is already cancelled",
        )

    appointment["status"] = CANCELLED
    return appointment


@router.get("/queue/today", response_model=list[AppointmentResponse])
def todays_queue(user: dict = Depends(get_current_user)):
    today = date.today()
    queue = [
        a for a in store.appointments.values()
        if a["date"] == today and a["status"] != CANCELLED
    ]

    if user["role"] not in STAFF_ROLES:
        queue = [a for a in queue if a["patient_email"] == user["email"]]

    return sorted(queue, key=lambda a: a["queue_number"])


@router.post("/queue/{appointment_id}/serve", response_model=AppointmentResponse)
def mark_served(appointment_id: int, user: dict = Depends(require_staff)):
    appointment = get_appointment_or_404(appointment_id)

    if appointment["status"] == SERVED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Patient has already been served",
        )
    if appointment["status"] == CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot serve a cancelled appointment",
        )

    appointment["status"] = SERVED
    return appointment
