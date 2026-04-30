from datetime import datetime, date
import pytz
from sqlalchemy import text
from ..db.session import get_db
from langchain.tools import tool

CLINIC_TZ = pytz.timezone("Asia/Beirut")
APPOINTMENT_DURATION_MINUTES = 30

@tool
def validate_booking_request(
    doctor_id: str,
    date_iso: str,
    start_time: str,
    end_time: str,
    patient_email: str  # 👈 NEW: We need the patient's email to check their history!
) -> dict:
    """
    Final validation before booking.
    Does NOT write to DB.
    use it every time before booking any new appointment to ensure all rules are met.
    """

    db = get_db()

    # 1️⃣ Parse datetime
    try:
        target_date = datetime.fromisoformat(date_iso).date()
        start_dt = CLINIC_TZ.localize(
            datetime.fromisoformat(f"{date_iso}T{start_time}")
        )
        end_dt = CLINIC_TZ.localize(
            datetime.fromisoformat(f"{date_iso}T{end_time}")
        )
    except Exception:
        return {"validation_result": False, "validation_fail_reason": "Invalid date or time format"}

    # 2️⃣ Date not in the past
    if start_dt < datetime.now(CLINIC_TZ):
        return {"validation_result": False, "validation_fail_reason": "Appointment time is in the past"}

    # 3️⃣ Duration check
    duration = (end_dt - start_dt).total_seconds() / 60
    if duration != APPOINTMENT_DURATION_MINUTES:
        return {"validation_result": False, "validation_fail_reason": "Invalid appointment duration"}

    # 4️⃣ Check working hours
    weekday_key = target_date.strftime("%a").lower()[:3]

    working_hours_query = text("""
        SELECT working_hours
        FROM doctors
        WHERE id = :doctor_id
    """)
    row = db.execute(working_hours_query, {"doctor_id": doctor_id}).fetchone()

    if not row:
        return {"validation_result": False, "validation_fail_reason": "Doctor not found"}

    working_hours = row.working_hours
    if weekday_key not in working_hours:
        return {"validation_result": False, "validation_fail_reason": "Doctor does not work this day"}

    # Check slot inside allowed ranges
    slot_ok = False
    for time_range in working_hours[weekday_key]:
        ws, we = time_range.split("-")
        window_start = CLINIC_TZ.localize(
            datetime.fromisoformat(f"{date_iso}T{ws}")
        )
        window_end = CLINIC_TZ.localize(
            datetime.fromisoformat(f"{date_iso}T{we}")
        )

        if start_dt >= window_start and end_dt <= window_end:
            slot_ok = True
            break

    if not slot_ok:
        return {"validation_result": False, "validation_fail_reason": "Time outside working hours"}

    # 5️⃣ Check DOCTOR conflicts (Is the doctor busy?)
    # 👈 FIX: Added status != 'cancelled' so cancelled slots are freed up!
    conflict_query = text("""
        SELECT 1
        FROM appointments
        WHERE doctor_id = :doctor_id
          AND start_time < :end_time
          AND end_time > :start_time
          AND status != 'cancelled' 
        LIMIT 1
    """)

    conflict = db.execute(
        conflict_query,
        {
            "doctor_id": doctor_id,
            "start_time": start_dt,
            "end_time": end_dt
        }
    ).fetchone()

    if conflict:
        return {"validation_result": False, "validation_fail_reason": "Slot already booked by another patient"}

    # 6️⃣ NEW: Check PATIENT Limits
    
    # Rule A: Has the patient already booked THIS doctor on THIS day?
    patient_doc_rule = text("""
        SELECT 1 FROM appointments a
        JOIN patients p ON a.patient_id = p.id
        WHERE p.email = :patient_email
          AND a.doctor_id = :doctor_id
          AND a.start_time::date = :target_date
          AND a.status != 'cancelled'
        LIMIT 1
    """)
    if db.execute(patient_doc_rule, {"patient_email": patient_email, "doctor_id": doctor_id, "target_date": target_date}).fetchone():
        return {
            "validation_result": False, 
            "validation_fail_reason": "You already have an appointment with this doctor on this day. You can book a different doctor, or choose a different day."
        }

    # Rule B: Is the patient already booked at this EXACT TIME with a different doctor?
    patient_time_rule = text("""
        SELECT 1 FROM appointments a
        JOIN patients p ON a.patient_id = p.id
        WHERE p.email = :patient_email
          AND a.start_time < :end_time
          AND a.end_time > :start_time
          AND a.status != 'cancelled'
        LIMIT 1
    """)
    if db.execute(patient_time_rule, {"patient_email": patient_email, "start_time": start_dt, "end_time": end_dt}).fetchone():
        return {
            "validation_result": False, 
            "validation_fail_reason": "You already have an appointment scheduled at this exact time with another doctor. Please choose a different time."
        }

    # ✅ All good
    return {
        "validation_result": True,
        "status": "appointment_booked",
        "doctor_id": doctor_id,
        "date": date_iso,
        "start_time": start_time,
        "end_time": end_time
    }