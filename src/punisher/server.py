import asyncio
import logging
import uvicorn
import json
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from punisher.core.orchestrator import AgentOrchestrator
from punisher.config import settings
from punisher.bus.queue import MessageQueue
from punisher.db.mongo import mongo
from punisher.integrations.telegram import TelegramBot

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("punisher.server")

orchestrator = AgentOrchestrator()
telegram = TelegramBot()
queue = MessageQueue()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Run orchestrator and telegram in background
    t1 = asyncio.create_task(orchestrator.start())
    t2 = asyncio.create_task(telegram.start())
    yield
    # Shutdown
    orchestrator.stop()
    await telegram.stop()
    await t1
    if t2:
        await t2


app = FastAPI(title="Punisher", lifespan=lifespan)

# Serve Frontend
app.mount("/static", StaticFiles(directory="frontend"), name="static")


@app.get("/")
async def read_root():
    return FileResponse("frontend/index.html")


# --- Agent Management API ---


@app.get("/api/agents/config")
async def get_all_configs():
    db = await mongo.get_db()
    configs = await db.agent_configs.find({}, {"_id": 0}).to_list(length=100)
    return configs


@app.post("/api/agents/config")
async def save_config(request: Request):
    data = await request.json()
    agent_id = data.get("agent_id")
    if not agent_id:
        return {"error": "Missing agent_id"}

    db = await mongo.get_db()
    await db.agent_configs.update_one(
        {"agent_id": agent_id},
        {
            "$set": {
                "system_prompt": data.get("system_prompt"),
                "temperature": float(data.get("temperature", 0.7)),
            }
        },
        upsert=True,
    )
    return {"status": "saved"}


@app.get("/api/agents/tasks")
async def get_tasks(agent: str = None):
    db = await mongo.get_db()
    query = {"agent": agent} if agent else {}
    tasks = (
        await db.agent_tasks.find(query, {"_id": 0})
        .sort("timestamp", -1)
        .limit(50)
        .to_list(length=50)
    )
    return tasks


# --- Command & Event API ---


@app.post("/api/command")
async def send_command(request: Request):
    data = await request.json()
    command = data.get("command")
    session_id = data.get("session_id", "default")

    if not command:
        return {"error": "No command provided"}

    payload = {"source": "web", "content": command, "session_id": session_id}
    queue.push("punisher:inbox", json.dumps(payload))
    return {"status": "sent"}


@app.get("/api/events")
async def events(request: Request):
    async def event_generator():
        while True:
            msg = queue.pop("punisher:cli:out", timeout=0)
            if msg:
                yield f"data: {json.dumps({'type': 'broadcast', 'content': msg})}\n\n"

            resp = queue.pop("punisher:web:out", timeout=0)
            if resp:
                yield f"data: {json.dumps({'type': 'response', 'content': resp})}\n\n"

            await asyncio.sleep(0.1)
            if await request.is_disconnected():
                break

    return StreamingResponse(event_generator(), media_type="text/event-stream")


def main():
    uvicorn.run("punisher.server:app", host="0.0.0.0", port=8000, reload=settings.DEBUG)


if __name__ == "__main__":
    main()
