from langgraph.graph import StateGraph, END
from server.graph.state import ClinicState
from server.graph.agents.booking.agent import (
    scheduling_agent_node,
    tool_node 
)
from langgraph.checkpoint.memory import MemorySaver
from server.graph.agents.booking.update_state import update_state_from_tools
from server.graph.agents.rag.rag import rag_chain_node
from server.graph.agents.router import router_node

def should_continue(state: ClinicState):
    last_message = state["messages"][-1]

    # If the LLM called a tool
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"

    return END


builder = StateGraph(ClinicState)

builder.add_node("router", router_node)
builder.add_node("rag", rag_chain_node)
builder.add_node("schedule", scheduling_agent_node)
builder.add_node("tools", tool_node)
builder.add_node("update_state", update_state_from_tools)

builder.set_entry_point("router")


# -----------------------------
# ROUTER
# -----------------------------
builder.add_conditional_edges(
    "router",
    lambda state: state["route"],
    {
        "rag": "rag",
        "schedule": "schedule"
    }
)

# -----------------------------
# SCHEDULING LOOP
# -----------------------------
builder.add_conditional_edges(
    "schedule",
    should_continue,
    {
        "tools": "tools",
        END: END,
    },
)

# Tools → Update State → Back to Schedule
builder.add_edge("tools", "update_state")
builder.add_edge("update_state", "schedule")


# -----------------------------
# RAG FLOW
# -----------------------------
builder.add_edge("rag", END)



memory = MemorySaver()
# Compile with checkpointer to enable "threads" (conversations)
graph = builder.compile(checkpointer=memory)

