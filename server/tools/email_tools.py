import requests
from langchain.tools import tool
from pydantic import BaseModel, Field
import os
from dotenv import load_dotenv
import json
from langchain_core.messages import ToolMessage

load_dotenv()

N8N_START_URL = os.getenv("N8N_START_URL")
N8N_VERIFY_URL = os.getenv("N8N_VERIFY_URL")
N8N_API_KEY = os.getenv("N8N_API_KEY", "super_secret_clinic_565")

def get_n8n_headers():
    return {
        "Content-Type": "application/json",
        "secret": N8N_API_KEY
    }

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
        # 2. Added headers=get_n8n_headers() here!
        response = requests.post(N8N_START_URL, json=payload, headers=get_n8n_headers(), timeout=10)
        response.raise_for_status() 
        data = response.json()
        
        req_id = data.get("request_id")
        print(f"--- DEBUG N8N START WEBHOOK RESPONSE ---: {data}")

        if not req_id:
             return {
                 "status": "error",
                 "message": "ERROR: The webhook succeeded, but n8n did not return a 'request_id'. Do not proceed."
             }

        return {
            "request_id": req_id,             
            "status": "verification_sent",    
            "message": f"SUCCESS! The email was sent to {email}. CRITICAL INSTRUCTION FOR AI: The request_id is {req_id}. You MUST remember this exact request_id and pass it into the verify_email_code tool when the user provides the code. Ask the user for the code now."
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"ERROR: Failed to send email. Apologize to the user. Error: {str(e)}"
        }
@tool(description="Verifies the OTP code provided by the user.", args_schema=VerifyCodeInput)
def verify_email_code(email: str, code: str, request_id: str) -> ToolMessage:
    """Verifies the OTP code provided by the user."""
    payload = {
        "email": email.strip(),
        "code": str(code).strip(),
        "request_id": str(request_id).strip()
    }

    print(f"\n--- DEBUG VERIFY: SENDING TO N8N ---")
    print(f"Payload: {payload}")

    # Initialize data payloads
    result_data = {"email_verified": False, "status": "error", "message": ""}

    try:
        response = requests.get(N8N_VERIFY_URL, json=payload, headers=get_n8n_headers(), timeout=10)
        
        print(f"--- DEBUG VERIFY: N8N RESPONSE ---")
        print(f"Status Code: {response.status_code}")
        print(f"Raw Response: {response.text}\n")
        
        response.raise_for_status()
        data = response.json()

        if isinstance(data, list) and len(data) > 0:
            data = data[0]

        is_success = (
            data.get("is_verified") is True or
            str(data.get("is_verified")).lower() == "true" or
            data.get("verified") is True or 
            data.get("success") is True or 
            str(data.get("verified")).lower() == "true" or
            str(data.get("success")).lower() == "true" or
            data.get("message") == "success" or
            data.get("status") == "verified" or 
            data.get("message") == "Email confirmed successfully."
        )

        if is_success:
            print("\n--- DEBUG VERIFY: MATCH SUCCESS! Returning ToolMessage payload ---")
            result_data = {
                "email_verified": True,
                "status": "success",
                "message": "SUCCESS: The verification code is correct. Proceed immediately to validate the appointment time."
            }
        else:
            print("\n--- DEBUG VERIFY: MATCH FAILED! ---")
            result_data = {
                "email_verified": False,
                "status": "failed",
                "message": "FAILED: The verification code is incorrect. Ask the user to check their email and try again."
            }
             
    except Exception as e:
        print(f"--- DEBUG VERIFY: EXCEPTION ---: {str(e)}")
        result_data = {
            "email_verified": False,
            "status": "error",
            "message": f"ERROR: An error occurred while communicating with the verification server: {str(e)}"
        }

    # 🚀 THE MAGIC FIX: Return a clean string content inside a ToolMessage block.
    # When your LangGraph ToolNode passes this back, OpenAI sees a perfectly matched tool block.
    return ToolMessage(
        content=json.dumps(result_data),
        status=result_data["status"],
        name="verify_email_code",
        tool_call_id="" # LangGraph's ToolNode will automatically override this with the real active tool_call_id!
    )