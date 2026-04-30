import requests
from langchain.tools import tool
from pydantic import BaseModel, Field

import requests
from pydantic import BaseModel, Field
from langchain_core.tools import tool

N8N_START_URL = "https://leeann-bioptic-bertram.ngrok-free.dev/webhook/verify/start"
N8N_VERIFY_URL = "https://leeann-bioptic-bertram.ngrok-free.dev/webhook/verify/code"

class StartVerificationInput(BaseModel):
    email: str = Field(description="User email address")
    name: str = Field(description="User full name")

class VerifyCodeInput(BaseModel):
    email: str = Field(description="User email address")
    code: str = Field(description="6-digit verification code provided by the user")
    request_id: str = Field(description="Verification request ID returned from start_email_verification")

@tool(args_schema=StartVerificationInput)
def start_email_verification(email: str, name: str) -> dict:
    """
    Sends a verification code to the user's email. Call this before verifying the code.
    """
    payload = {
        "email": email,
        "name": name
    }

    try:
        response = requests.post(N8N_START_URL, json=payload, timeout=10)
        response.raise_for_status() # Catches 4xx and 5xx errors
        data = response.json()
        
        req_id = data.get("request_id")
        
        # DEBUG: Watch your terminal to make sure n8n is actually returning the ID!
        print(f"--- DEBUG N8N START WEBHOOK RESPONSE ---: {data}")

        if not req_id:
             return {
                 "status": "error",
                 "message": "ERROR: The webhook succeeded, but n8n did not return a 'request_id'. Do not proceed."
             }

        # The Best of Both Worlds: Update state AND command the LLM
        return {
            "request_id": req_id,             # LangGraph saves this to your state
            "status": "verification_sent",    # LangGraph saves this to your state
            "message": f"SUCCESS! The email was sent to {email}. CRITICAL INSTRUCTION FOR AI: The request_id is {req_id}. You MUST remember this exact request_id and pass it into the verify_email_code tool when the user provides the code. Ask the user for the code now."
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"ERROR: Failed to send email. Apologize to the user. Error: {str(e)}"
        }
            
@tool(args_schema=VerifyCodeInput)
def verify_email_code(email: str, code: str, request_id: str) -> dict:
    """
    Verifies the OTP code provided by the user. 
    """
    # Force clean strings just in case the LLM or n8n added invisible spaces
    payload = {
        "email": email.strip(),
        "code": str(code).strip(),
        "request_id": str(request_id).strip()
    }

    print(f"\n--- DEBUG VERIFY: SENDING TO N8N ---")
    print(f"Payload: {payload}")

    try:
        response = requests.post(N8N_VERIFY_URL, json=payload, timeout=10)
        
        # This will print exactly what n8n is saying back!
        print(f"--- DEBUG VERIFY: N8N RESPONSE ---")
        print(f"Status Code: {response.status_code}")
        print(f"Raw Response: {response.text}\n")
        
        response.raise_for_status()
        data = response.json()

        # More flexible success checking (handles both booleans and strings)
        is_success = (
            data.get("verified") is True or 
            data.get("success") is True or 
            str(data.get("verified")).lower() == "true" or
            str(data.get("success")).lower() == "true" or
            data.get("message") == "success"
        )

        # We now know EXACTLY what n8n sends!
        is_success = (
            data.get("status") == "verified" or 
            data.get("message") == "Email confirmed successfully."
        )

        if is_success:
             return {
                 "email_verified": True,
                 "instruction_for_llm": "SUCCESS: The code is correct. You MUST now call the finalize_booking tool to save the appointment."
             }
        else:
             return {
                 "email_verified": False,
                 "instruction_for_llm": f"FAILED: The code is incorrect. n8n responded with: {data}. Ask the user to try again."
             }
             
    except Exception as e:
        print(f"--- DEBUG VERIFY: EXCEPTION ---: {str(e)}")
        return {
            "email_verified": False,
            "instruction_for_llm": f"An error occurred while verifying the code: {str(e)}"
        }