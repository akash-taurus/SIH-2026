from fastapi import APIRouter
from typing import List
from app.database import get_roads
from app.schemas import RoadItem

router = APIRouter(tags=["Roads"])

@router.get("/roads", response_model=List[RoadItem])
async def get_all_roads():
    """
    Returns critical highway network corridors with real-time blockage status.
    """
    return get_roads()
