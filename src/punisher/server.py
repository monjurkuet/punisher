import asyncio
import logging
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from punisher.core.orchestrator import AgentOrchestrator
from punisher.config import settings

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("punisher.server")

orchestrator = AgentOrchestrator()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Run orchestrator in background
    task = asyncio.create_task(orchestrator.start())
    yield
    # Shutdown
    orchestrator.stop()
    await task


app = FastAPI(title="Punisher", lifespan=lifespan)

# Serve Frontend
app.mount("/static", StaticFiles(directory="frontend"), name="static")


@app.get("/")
async def read_root():
    return FileResponse("frontend/index.html")


@app.get("/styles.css")
async def styles():
    return FileResponse("frontend/styles.css")


def main():
    """Entry point for punisher-server"""
    uvicorn.run("punisher.server:app", host="0.0.0.0", port=8000, reload=settings.DEBUG)


if __name__ == "__main__":
    main()
