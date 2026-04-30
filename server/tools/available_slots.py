from sqlalchemy import text
from datetime import date, timedelta, datetime
import pytz # type: ignore 
from ..db.session import get_db
from langchain.tools import tool


APPOINTMENT_DURATION_MINUTES = 30
CLINIC_TIMEZONE = pytz.timezone("Asia/Beirut")
def get_doctor_working_hours(db, doctor_id):
    query = text("""
        SELECT working_hours
        FROM doctors
        WHERE id = :doctor_id
    """)
    result = db.execute(query, {"doctor_id": doctor_id}).fetchone()
    return result[0] if result else None


def get_existing_appointments(db, doctor_id, target_date: date):
    query = text("""
        SELECT start_time, end_time
        FROM appointments
        WHERE doctor_id = :doctor_id
          AND start_time::date = :target_date
    """)
    return db.execute(
        query,
        {
            "doctor_id": doctor_id,
            "target_date": target_date
        }
    ).fetchall()

@tool
def get_available_slots(doctor_id: str, date_iso: str) -> dict:
    """
    Returns available appointment slots for a doctor on a given date.
    
    CRITICAL INSTRUCTION: You DO NOT know the doctor_id by default. 
    If you do not have the 36-character UUID for the doctor, you MUST call 
    the `resolve_doctor` tool FIRST to find their correct `doctor_id`. 
    DO NOT guess or make up an ID like "1".
    """
    if len(doctor_id) < 30:
        return {"slots": [], "reason": "Error: Invalid doctor_id. You MUST use the resolve_doctor tool to get the real UUID first."}
    
    try:
        target_date = datetime.fromisoformat(date_iso).date()
    except ValueError:
        return {"slots": [], "reason": "Invalid date format"}

    # 🛑 NEW: THE PAST DATE FAILSAFE
    today_date = datetime.now(CLINIC_TIMEZONE).date()
    if target_date < today_date:
        print(f"--- DEBUG: User requested past date {target_date}. Wiping state. ---")
        return {
            "date": None,         # Wipes the bad date from the LangGraph state
            "start_time": None,   # Clears any stray times
            "end_time": None,
            "slots": [], 
            "reason": "Error: The requested date has already passed. Ask the user for a future date."
        }

    weekday_key = target_date.strftime("%a").lower()[:3]

    db = get_db()

    try:
        # 1️⃣ Working hours
        working_hours = get_doctor_working_hours(db, doctor_id)
        if not working_hours:
            return {"slots": [], "reason": "Doctor not found"}

        if weekday_key not in working_hours:
            return {"slots": [], "reason": "Doctor not working this day"}

        # 2️⃣ Generate candidate slots
        candidate_slots = []

        for time_range in working_hours[weekday_key]:
            start_str, end_str = time_range.split("-")

            window_start = CLINIC_TIMEZONE.localize(
                datetime.combine(target_date, datetime.strptime(start_str, "%H:%M").time())
            )
            window_end = CLINIC_TIMEZONE.localize(
                datetime.combine(target_date, datetime.strptime(end_str, "%H:%M").time())
            )

            current = window_start
            while current + timedelta(minutes=APPOINTMENT_DURATION_MINUTES) <= window_end:
                candidate_slots.append((current, current + timedelta(minutes=APPOINTMENT_DURATION_MINUTES)))
                current += timedelta(minutes=APPOINTMENT_DURATION_MINUTES)

        # 3️⃣ Existing appointments
        existing = get_existing_appointments(db, doctor_id, target_date)

        # 4️⃣ Conflict removal
        available_slots = []

        for slot_start, slot_end in candidate_slots:
            conflict = False
            for appt_start, appt_end in existing:
                appt_start = appt_start.astimezone(CLINIC_TIMEZONE)
                appt_end = appt_end.astimezone(CLINIC_TIMEZONE)

                if slot_start < appt_end and slot_end > appt_start:
                    conflict = True
                    break

            if not conflict:
                # 👇 FIX: Tell the AI the actual times!
                available_slots.append({
                    "start": slot_start.strftime("%H:%M"),
                    "end": slot_end.strftime("%H:%M")
                })

        return {
            "doctor_id": doctor_id,
            "date": date_iso,
            "available_slots": available_slots
        }

    finally:
        db.close()