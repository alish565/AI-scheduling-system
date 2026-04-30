import uuid
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from server.graph.graph import graph


app = FastAPI(title="Clinic AI Scheduler API")

class ChatRequest(BaseModel):
    message: str
    thread_id: Optional[str] = None  

class ChatResponse(BaseModel):
    response: str
    thread_id: str
    patient_name: Optional[str] = None
    patient_email: Optional[str] = None
    doctor_id: Optional[str] = None
    date: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    status: Optional[str] = None



@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    # 1. Handle thread_id (Use provided one or start fresh)
    thread_id = request.thread_id or str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    try:
        # 2. Invoke the Graph
        # We use ainvoke (async) because FastAPI is an async framework
        input_data = {"messages": [("user", request.message)]}
        
        # This will automatically pull history from MemorySaver 
        # based on the thread_id
        result = await graph.ainvoke(input_data, config)

        # 3. Extract data from the updated state
        messages = result.get("messages", [])
        if not messages:
            raise HTTPException(status_code=500, detail="No response generated")

        final_answer = messages[-1].content
        
        return ChatResponse(
            response=final_answer,
            thread_id=thread_id,
            patient_name=result.get("patient_name"),
            patient_email=result.get("patient_email"),
            doctor_id=result.get("doctor_id"),
            date=result.get("date"),
            start_time=result.get("start_time"),
            end_time=result.get("end_time"),
            status=result.get("status"),
        )

    except Exception as e:
        print(f"Error in graph execution: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health_check():
    return {"status": "healthy"}
