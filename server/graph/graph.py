from langgraph.graph import StateGraph, END
from graph.state import ClinicState
from graph.agents.booking.agent import (
    scheduling_agent_node,
    tool_node 
)
from graph.agents.booking.update_state import update_state_from_tools
from graph.agents.rag.rag import rag_chain_node
from graph.agents.router import router_node
import os
from psycopg_pool import ConnectionPool
from langgraph.checkpoint.postgres import PostgresSaver

RAW_DB_URI = os.getenv("DATABASE_URL", "postgresql+psycopg://postgres:password@localhost:5432/AI_scheduling")

# 2. Strip out the "+psycopg" part specifically for LangGraph
LANGGRAPH_DB_URI = RAW_DB_URI.replace("+psycopg", "")

# 3. Pass the clean URL to the ConnectionPool
connection_pool = ConnectionPool(
    conninfo=LANGGRAPH_DB_URI,
    max_size=20,
    kwargs={"autocommit": True} 
)
memory = PostgresSaver(connection_pool)
memory.setup()

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


# Compile with checkpointer to enable "threads" (conversations)
graph = builder.compile(checkpointer=memory)

