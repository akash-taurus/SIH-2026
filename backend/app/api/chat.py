from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, Dict, Any
from app.services.ai_chat_service import process_disaster_chat, get_welcome_payload

router = APIRouter(prefix="/chat", tags=["AI Disaster Assistant Chatbot"])

class ChatRequest(BaseModel):
    query: str
    location: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    language: Optional[str] = "en"

@router.get("/welcome")
def get_chat_welcome(language: Optional[str] = "en") -> Dict[str, Any]:
    """
    Returns initial greeting and prompts user for their location in their chosen native language.
    """
    return get_welcome_payload(language or "en")

@router.post("/ask")
async def ask_disaster_assistant(req: ChatRequest) -> Dict[str, Any]:
    """
    Processes citizen/responder query in native language (English, Khasi, Garo, Hindi, Assamese)
    and returns context-grounded disaster safety guidance with Factor of Safety and road status.
    """
    return await process_disaster_chat(
        query=req.query,
        location=req.location,
        lat=req.lat,
        lon=req.lon,
        language=req.language or "en"
    )
