from fastapi import FastAPI,Request,Response,BackgroundTasks
import requests
from dotenv import load_dotenv
from fastapi.responses import JSONResponse
load_dotenv()
from services.message import process_slack_message,process_teams_message,google_process_message


app = FastAPI(title="AI Bot",description="you can ask any questions to solve")


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
    JSONResponse(status_code=200, content={"text": " Processing..."})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app",host="0.0.0.0",port=8003,reload=True)
