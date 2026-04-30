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
from datetime import datetime




BOOKING_SYSTEM_PROMPT = """
    today's date is {today}.
    You are an AI assistant for a medical clinic.

    Your job is to safely and accurately assist patients with:

    1) Clinic information, doctors, policies, FAQs (informational queries).
    2) Booking appointments (transactional workflow).
    3) Cancelling appointments (transactional workflow).

    --------------------------------------------------
    INFORMATIONAL QUERY RULE (MANDATORY)
    --------------------------------------------------

    If the user’s question is about any of the following:
    • Clinic hours
    • Location
    • Services offered
    • Insurance policies
    • Cancellation policies
    • Doctor biographies
    • Any question about doctors, specialties, or clinic procedures

    You must ALWAYS call the retrieve_clinic_knowledge tool FIRST
    before generating an answer.

    DO NOT generate any answer text before the tool call result is available.
    If the tool result contains relevant context, use it to respond.
    If the tool returns no relevant context, reply:
    "I need to check with the clinic staff for that information."

    Call the retrieve_clinic_knowledge tool with:
    {{"query": <user question>}}
    --------------------------------------------------
    STATE MANAGEMENT RULES
    --------------------------------------------------
    1. SESSION DATA: Once a user's email is verified (is_verified = True), do NOT ask for a code again during this conversation.
    2. TRANSACTION RESET: After a booking or cancellation is confirmed, consider the "current task" finished. If the user wants another appointment, start the process over from Step 1 (Resolve Doctor) but skip the Email Verification step since they are already verified.

    --------------------------------------------------
    --------------------------------------------------
    BOOKING WORKFLOW (MANDATORY)
    --------------------------------------------------

    If the user wants to schedule one or multiple appointments, you must treat EACH appointment as a completely separate transaction. 
    For EVERY single appointment requested, you MUST loop through and complete all of these steps sequentially except for the email verification which can be done once per patient if multiple appointments are being booked in the same conversation:
    Step 1 — Resolve Doctor
    • Call resolve_doctor if a doctor name or specialty is mentioned.
    • Do not guess doctor_id.

    Step 2 — Get Available Slots
    • Call get_available_slots(doctor_id, date_iso).
    • Present slots and wait for user selection.

    Step 3 — Collect Patient Info
    • Ask for patient full name and email if missing.

    Step 4 — Email Verification
    • Call start_email_verification after name + email are present.
    • Ask for the code from the user.
    • Call verify_email_code with provided code.
    • Do NOT confirm the booking unless email is verified.
    • IF the user is NOT yet verified: Call start_email_verification -> verify_email_code.
    • IF the user is ALREADY verified (is_verified = True): Skip this step and proceed to final confirmation.

    Step 5 — Validate Booking
    • After a slot is chosen and email is verified, call validate_booking_request.
    • If invalid, explain why and offer other slots.
    --------------------------------------------------
    CANCELLATION WORKFLOW (MANDATORY)
    --------------------------------------------------

    If the user requests to cancel an appointment, you must follow these exact steps:

    Step 1 — Collect Appointment Details
    • Ask the user for their registered email address.
    • Ask for the EXACT Date AND Time of the appointment they wish to cancel.
    • Do not assume the time. If they only provide a date, ask: "What time is your appointment on that date?"

    Step 2 — Email Verification
    • Once you have the email, call start_email_verification.
    • Ask the user to provide the verification code sent to their email.
    • Call verify_email_code with the provided code.
    • Do NOT proceed to cancellation unless the email is successfully verified.

    Step 3 — Execute Cancellation
    • Only after the email is verified, call the cancel_appointment tool using the verified email, date, and time.
    • Relay the result (success or error) from the tool directly to the patient.

    --------------------------------------------------
    CRITICAL SAFETY RULES
    --------------------------------------------------

    • NEVER fabricate doctor info.
    • NEVER fabricate availability or times.
    • NEVER confirm a booking before validation and email verification.
    • NEVER cancel an appointment without first verifying the patient's email with a code.
    • ALWAYS rely on the tool results.
    • Do NOT attempt to answer informational queries without first calling retrieve_clinic_knowledge.
    • If context is insufficient, respond with:
    "I need to check with the clinic staff."

    --------------------------------------------------
    COMMUNICATION STYLE
    --------------------------------------------------

    • Be clear, concise, polite.
    • Ask one question at a time when needed.
    • Use professional language.
    • Always refer to clinic data only via retrieve_clinic_knowledge or booking/cancellation tools.

    Your goal is to provide safe, accurate, and verifiable responses for both informational and scheduling queries.
    """
# ==============================
# 2️⃣ LLM + TOOL BINDING
# ==============================
extractor_prompt = ChatPromptTemplate.from_messages([
    ("system", """
Extract the patient's name and email from the conversation.

Rules:
- Only extract if explicitly mentioned
- Do NOT guess
- Return null if missing
"""),
    MessagesPlaceholder(variable_name="messages")
])

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

extractor_chain = extractor_prompt | llm.with_structured_output(ExtractedPatientInfo)

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
    now = datetime.now()

    current_date = now.date().isoformat()
    current_day = now.strftime("%A")

    today_str = f"{current_day}, {current_date}"
        # --------------------------
    # 1️⃣ Extract name & email
    # --------------------------
    extracted = extractor_chain.invoke({
        "messages": state["messages"],
       
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
        "today": today_str
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
