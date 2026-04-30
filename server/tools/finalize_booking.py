from langchain_core.tools import tool

@tool
def finalize_booking(date: str, start_time: str, doctor_id: str, patient_name: str, patient_email: str):
    """
    Call this tool ONLY after the email is verified to finalize the appointment.
    It saves the final booking details to the system.
    """
   
    return {
        "date": date,
        "start_time": start_time,
        "doctor_id": doctor_id,
        "patient_name": patient_name,
        "patient_email": patient_email,
        "status": "booked" # This is the magic flag that tells n8n to fire!
    }