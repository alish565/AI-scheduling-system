from langchain_core.messages import ToolMessage
from server.graph.state import ClinicState
import json
import ast
from langchain_core.messages import ToolMessage

def update_state_from_tools(state: ClinicState) -> dict:
    """
    Reads last ToolMessage and updates state from tool output.
    """
    last_message = state["messages"][-1]
    
    # We will store only the fields we want to update in this dictionary
    updates = {}

    if isinstance(last_message, ToolMessage):
        content = last_message.content
        print(f"\n--- DEBUG UPDATE STATE --- Raw Tool Output: {content}")
        
        try:
            # First, try standard JSON parsing
            data = json.loads(content)
        except json.JSONDecodeError:
            try:
                # If it fails, it's likely a Python string representation. Use ast to parse it safely.
                data = ast.literal_eval(content)
            except Exception as e:
                print(f"--- DEBUG UPDATE STATE --- Failed to parse tool output! Error: {e}")
                data = None

        if isinstance(data, dict):
            for key, value in data.items():
                # We only want to update keys if they actually belong in ClinicState
                # (Ignoring tool-specific instructions meant for the LLM)
                if key != "instruction_for_llm" and key != "message":
                    updates[key] = value
                    print(f"--- DEBUG UPDATE STATE --- Saving to state: {key} = {value}")

    # Return ONLY the changed values. LangGraph automatically merges this into ClinicState!
    return updates