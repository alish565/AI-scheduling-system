import requests
from langchain_core.tools import tool
import requests
from langchain_core.tools import tool

# You will get this URL in Step 2 from your new n8n workflow
CANCEL_WEBHOOK_URL = "https://leeann-bioptic-bertram.ngrok-free.dev/webhook/cancel-appointment" 

@tool
def cancel_appointment(patient_email: str, date_iso: str, time_str: str) -> dict:
    """
    Use this tool when a patient wants to cancel an existing appointment.
    CRITICAL RULE: You MUST successfully verify the user's email using start_email_verification 
    AND verify_email_code tools BEFORE calling this cancel_appointment tool.
    Do NOT execute this tool if the email has not been verified with a code.
    Time should be in HH:MM format (e.g., "11:00" or "14:30").
    """
    
    payload = {
        "patient_email": patient_email,
        "date": date_iso,
        "time": time_str  # 👈 This is the crucial addition!
    }
    
    try:
        response = requests.post(CANCEL_WEBHOOK_URL, json=payload)
        
        if response.status_code == 200:
            return {
                "status": "cancelled", 
                "message": f"The appointment on {date_iso} at {time_str} was successfully cancelled. Please inform the user."
            }
        else:
            return {
                "status": "error", 
                "message": f"Failed to cancel. n8n returned status code {response.status_code}. Tell the user to call the clinic."
            }
    except Exception as e:
        return {"status": "error", "message": str(e)}