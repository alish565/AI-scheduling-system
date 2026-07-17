import requests
from langchain_core.tools import tool
import requests
from langchain_core.tools import tool
import os

# You will get this URL in Step 2 from your new n8n workflow

CANCEL_WEBHOOK_URL = os.getenv("N8N_CANCEL_URL")

N8N_API_KEY = os.getenv("N8N_API_KEY")

def get_n8n_headers():
    return {
        "Content-Type": "application/json",
        "X-API-KEY": N8N_API_KEY
    }

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
        "time": time_str 
    }
    
    try:
        # 2. Added headers=get_n8n_headers() here!
        response = requests.post(CANCEL_WEBHOOK_URL, json=payload, headers=get_n8n_headers(), timeout=15)
        
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