from langchain_core.messages import ToolMessage
from graph.state import ClinicState
import json
import ast
from langchain_core.messages import ToolMessage
from langchain_core.messages import AIMessage

def update_state_from_tools(state: ClinicState) -> dict:
    """
    Globally intercepts, patches tracking IDs, and correctly 
    returns both message history fixes and state variables.
    """
    messages = state.get("messages", [])
    if not messages:
        return {}

    last_message = messages[-1]
    
    # We will accumulate all state updates here
    updates = {}

    if isinstance(last_message, ToolMessage):
        # 🚀 FIX: If tracking ID is missing or blank, let's fix it
        if not last_message.tool_call_id or last_message.tool_call_id == "":
            print(f"\n--- 🛠️ GLOBAL SANITIZER: Patching missing ID for tool '{last_message.name}' ---")
            
            target_id = None
            for msg in reversed(messages):
                if isinstance(msg, AIMessage) and msg.tool_calls:
                    for tool_call in msg.tool_calls:
                        if tool_call.get("name") == last_message.name:
                            target_id = tool_call["id"]
                            break
                    if not target_id:
                        target_id = msg.tool_calls[-1]["id"]
                    break
            
            if target_id:
                print(f"--- 🛠️ GLOBAL SANITIZER: Successfully mapped to ID: {target_id} ---")
                last_message.tool_call_id = target_id
                
                # 🚀 THE CRITICAL ADDITION: Force LangGraph to update this specific message object
                updates["messages"] = [last_message]

        # -------------------------------------------------------------
        # Data Parsing Engine
        # -------------------------------------------------------------
        content = last_message.content
        if isinstance(content, str) and "VERIFICATION_SUCCESSFUL" in content:
            updates["email_verified"] = True
        elif isinstance(content, str) and "VERIFICATION_FAILED" in content:
            updates["email_verified"] = False
        else:
            try:
                data = json.loads(content)
            except (json.JSONDecodeError, TypeError):
                try:
                    data = ast.literal_eval(content)
                except Exception:
                    data = None

            if isinstance(data, dict):
                for key, value in data.items():
                    if key not in ["instruction_for_llm", "message"]:
                        updates[key] = value

    # Returns the updates. LangGraph will now see 'messages' and merge/overwrite the fixed message!
    return updates