import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .auth import require_api_key
from .whatsapp_service import WhatsAppNotLoggedIn, WhatsAppSendError, WhatsAppService

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class SendMessageRequest(BaseModel):
    number: str = Field(..., min_length=5, examples=["8801XXXXXXXXX"])
    message: str = Field(..., min_length=1, examples=["Hello"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    session_dir = os.getenv("WHATSAPP_SESSION_DIR", "./session")
    app.state.whatsapp = WhatsAppService(
        session_dir=session_dir,
        headless=env_bool("WHATSAPP_HEADLESS", default=False),
    )

    try:
        await app.state.whatsapp.start()
        yield
    finally:
        await app.state.whatsapp.stop()


app = FastAPI(
    title="Local WhatsApp Automation API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def frontend():
    return FileResponse(BASE_DIR / "whatsapp_api" / "static" / "index.html")


@app.get("/status", dependencies=[Depends(require_api_key)])
async def status():
    try:
        logged_in = await app.state.whatsapp.is_logged_in()
    except Exception as exc:
        logger.exception("Could not read WhatsApp status")
        return {"logged_in": False, "success": False, "error": f"Could not read WhatsApp status: {exc}"}

    if logged_in:
        return {"logged_in": True}

    return {"logged_in": False, "message": "Please scan QR code"}


@app.post("/send-message", dependencies=[Depends(require_api_key)])
async def send_message(payload: SendMessageRequest):
    try:
        await app.state.whatsapp.send_message(
            number=payload.number,
            message=payload.message,
        )
        return {"success": True, "message": "Message sent"}
    except WhatsAppNotLoggedIn as exc:
        logger.warning("WhatsApp login required: %s", exc)
        return {"success": False, "error": str(exc)}
    except WhatsAppSendError as exc:
        logger.warning("WhatsApp send failed: %s", exc)
        return {"success": False, "error": str(exc)}
    except Exception as exc:
        logger.exception("Unexpected WhatsApp send error")
        return {"success": False, "error": f"Unexpected error: {exc}"}
