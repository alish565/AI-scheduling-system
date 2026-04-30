from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.prebuilt import ToolNode
from langgraph.graph import END
from langchain_core.messages import AIMessage
from server.graph.state import ClinicState
from server.tools.resolve_doctor import resolve_doctor
from server.tools.available_slots import get_available_slots
from server.tools.validation import validate_booking_request
from server.tools.email_tools import start_email_verification, verify_email_code
from server.tools.finalize_booking import finalize_booking
from server.tools.cancel import cancel_appointment
from pydantic import BaseModel
from typing import Optional
from datetime import date
from langchain_core.messages import HumanMessage, AIMessage




BOOKING_SYSTEM_PROMPT = """
today's date is {today}.
You are a scheduling assistant for a medical center.

Your job is to safely guide patients through booking appointments.

STRICT RULES:

1) Always use tools when database or validation is required.
2) Never invent doctor IDs or time slots.
3) Never confirm booking without calling validate_booking_request.
4) Never confirm booking before email verification succeeds.
5) Follow the workflow strictly.

BOOKING WORKFLOW:

Step 1 — Resolve Doctor
- Use resolve_doctor when doctor name or specialty is mentioned.

Step 2 — Check Availability
- Use get_available_slots.
- Show available slots to the user.
- Wait for selection.

Step 3 — Validate Booking
- Use validate_booking_request after slot selection.
- If invalid, explain reason.

Step 4 — Collect Info
- Ask for full name and email.

Step 5 — Email Verification
- Call start_email_verification.
- CRITICAL: The start_email_verification tool will return a `request_id`. You MUST remember this ID.
- Ask the user for the verification code.
- Call verify_email_code. You MUST pass the user's email, the code they provided, AND the exact `request_id` you received in the previous step.
- Only after success, confirm the appointment.
DATA FORMATTING RULES:
- Whenever you pass a date to a tool, you MUST format it as YYYY-MM-DD (e.g., 2026-03-30).
- Whenever you pass a time to a tool, you MUST format it in 24-hour military time HH:MM (e.g., 14:30).
- Never use AM/PM or words for months when using tools.

FINAL BOOKING STEP (CRITICAL):
After the email is successfully verified in Step 5, you MUST save the final appointment details to the state.
Ensure you output the extracted:
- patient_name
- patient_email
- doctor_id
- date (YYYY-MM-DD)
- start_time (HH:MM)
- status: Set this exactly to "booked" (this triggers the external calendar system).
Be professional, clear, and step-by-step.
"""


# ==============================
# 2️⃣ LLM + TOOL BINDING
# ==============================

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0
)

tools = [
    resolve_doctor,
    get_available_slots,
    validate_booking_request,
    start_email_verification,
    verify_email_code,
    finalize_booking,
    cancel_appointment
]


class ExtractedPatientInfo(BaseModel):
    patient_name: Optional[str] = None
    patient_email: Optional[str] = None


prompt = ChatPromptTemplate.from_messages([
    ("system", BOOKING_SYSTEM_PROMPT),
    MessagesPlaceholder(variable_name="messages")
])


agent_chain = prompt | llm.bind_tools(tools)

tool_node = ToolNode(tools)

extractor_chain = prompt | llm.with_structured_output(ExtractedPatientInfo)

def scheduling_agent_node(state: ClinicState) -> ClinicState:
    """
    1️⃣ Extract patient info from conversation
    2️⃣ Run booking agent to decide tool usage
    """
    last_message = state["messages"][-1]

    # 🛑 THE STATE WIPE: If the user sends a new message AFTER a successful booking
    if isinstance(last_message, HumanMessage) and state.get("status") == "booked":
        print("\n--- DEBUG: Wiping old appointment data from state! ---")
        state["status"] = None
    current_date = date.today().isoformat()
    # --------------------------
    # 1️⃣ Extract name & email
    # --------------------------
    extracted = extractor_chain.invoke({
        "messages": state["messages"],
        "today": current_date
    })

    if extracted.patient_name:
        state["patient_name"] = extracted.patient_name

    if extracted.patient_email:
        state["patient_email"] = extracted.patient_email

    # --------------------------
    # 2️⃣ Run booking agent
    # --------------------------
    
    response = agent_chain.invoke({
        "messages": state["messages"],
        "today": current_date
    })

    state["messages"].append(response)

    return state

def scheduling_should_continue(state: ClinicState):
    """
    Decide whether to execute tools or finish.
    """

    last_message = state["messages"][-1]

    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "tools"

    return END