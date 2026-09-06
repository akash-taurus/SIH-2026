from fastapi import APIRouter
from typing import List
from app.database import get_settlements
from app.schemas import SettlementItem

router = APIRouter(tags=["Emergency Prioritization"])

@router.get("/emergency-prioritization", response_model=List[SettlementItem])
async def get_emergency_prioritization():
    """
    Returns prioritized village evacuation list sorted by vulnerability score.
    """
    return get_settlements()
