import uuid
from server.graph.graph import graph

# Define the config OUTSIDE or INSIDE the function depending on if 
# you want a new session every time you run the script.
config = {"configurable": {"thread_id": str(uuid.uuid4())}}

def chat():
    print("Clinic Assistant is ready! (type 'quit' to exit)")
    
    while True:
        user_input = input("User: ")
        
        if user_input.lower() in ["quit", "exit"]:
            print("Goodbye!")
            break

        for event in graph.stream(
            {"messages": [("user", user_input)]}, 
            config, 
            stream_mode="updates"
        ):
            # Only print if the node actually produced messages
            for node_name, output in event.items():
                if "messages" in output:
                    last_msg = output["messages"][-1]
                    # We check for .content to avoid printing empty tool-call messages
                    if hasattr(last_msg, "content") and last_msg.content:
                        print(f"[{node_name}]: {last_msg.content}")

chat()