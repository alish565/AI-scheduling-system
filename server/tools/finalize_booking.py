from langchain_core.tools import tool

@tool
def finalize_booking(date: str, start_time: str, doctor_id: str, patient_name: str, patient_email: str):
    """
    CRITICAL RULE: You may ONLY call this tool AFTER you have successfully called the 'validate_booking_request' 
    tool for this EXACT doctor_id, date,  patient_email, and start_time. 
    
    Do NOT call this tool for a second appointment until you have validated that second specific time slot.
    The patient's email must also be successfully verified before calling this.
    """
   
    return {
        "date": date,
        "start_time": start_time,
        "doctor_id": doctor_id,
        "patient_name": patient_name,
        "patient_email": patient_email,
        "status": "booked" # This is the magic flag that tells n8n to fire!
    }