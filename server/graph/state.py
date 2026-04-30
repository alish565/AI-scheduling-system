from typing import Optional, List, Dict,Annotated
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class ClinicState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    route: Optional[str]  # rag or schedule
    # user info
    patient_name: Optional[str]
    patient_email: Optional[str]
    email_verified: bool

    # booking info
    doctor_id: Optional[str]
    date: Optional[str]
    start_time: Optional[str]
    end_time: Optional[str]

    # system flags
    status: Optional[str]  
    intent: Optional[str]  # inquiry | schedule
    available_slots: Optional[List[Dict]]
    validation_result: Optional[Dict]
    validation_fail_reason: Optional[str]
    request_id: Optional[str]
