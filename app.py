from aiohttp import web
from fastapi import FastAPI,Request,Response,BackgroundTasks
import requests
from dotenv import load_dotenv
from fastapi.responses import JSONResponse
from pydantic import BaseModel
load_dotenv()
from services.message import process_slack_message,process_teams_message,google_process_message
from services.koru_mcp_server import mcp


class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"


# Create MCP ASGI app first
mcp_app = mcp.http_app(path="/")

# Create FastAPI app with MCP lifespan
app = FastAPI(
    title="AI Bot",
    description="you can ask any questions to solve",
    lifespan=mcp_app.lifespan
)

# Mount the MCP server
app.mount("/mcp", mcp_app)


@app.post("/app/teams/messages")
async def getTeamsMessages(req:Request):
    activity=await req.json()
    await process_teams_message(activity)
    return Response(status_code=200)


@app.post("/app/slack/messages")
async def getSlackMessage(req:Request,background_task:BackgroundTasks):
    data = await req.json()
    print(data)
    if(data.get("type")=="url_verification"):
        return {"challenge":data.get("challenge")}
    events = data.get("event")
    if(events.get("type")=="message" and not events.get("bot_id") and not events.get("subtype")):
        user_message = events.get("text")
        channel = events.get("channel")
        background_task.add_task(process_slack_message,user_message,channel)
    return "",200



@app.post("/google/messages")
async def getSlackMessage(req:Request,background_task:BackgroundTasks):
    data = await req.json()
    background_task.add_task(google_process_message,data)
    JSONResponse(status_code=200, content={"text": "⏳ Processing..."})


@app.post("/chat")
async def chat(chat_request: ChatRequest):
    from model import chat_llm, llm_messages
    
    try:
        agent = await chat_llm()
        reply = await llm_messages(agent, chat_request.message, chat_request.session_id)
        return {"reply": reply, "session_id": chat_request.session_id}
    except Exception as e:
        print(f"Error in /chat endpoint: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to process message", "detail": str(e)}
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app",host="localhost",port=8003,reload=True)