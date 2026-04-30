from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from server.graph.state import ClinicState

llm = ChatOpenAI(model="gpt-4o-mini")


def router_node(state: ClinicState) -> dict:
    user_message = state["messages"][-1].content
    
    # --- THE STICKY STATE BYPASS ---
    # Check if they are already in the middle of scheduling
    current_route = state.get("route")
    current_status = state.get("status")
    
    # If they started scheduling, but haven't finished (status is not 'booked'), keep them there!
    if current_route == "schedule" and current_status != "booked":
        # We can safely bypass the LLM and lock them into the schedule node
        return {"route": "schedule"}
    # ---------------------------------

    # If they are not currently scheduling, use the LLM to decide
    prompt = f"""
You are a router for a medical center AI assistant.

If the user is:
- Asking about doctors, services, opening hours → respond with: rag
- Trying to book, check availability → respond with: schedule

Only respond with one word:
rag
or
schedule

User message:
{user_message}
"""

    response = llm.invoke([HumanMessage(content=prompt)])

    return {
        "route": response.content.strip().lower()
    }