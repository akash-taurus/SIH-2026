from fastapi import APIRouter
from typing import Dict, Any
from app.services.radar_service import fetch_live_radar_frames, get_insar_deformation_features

router = APIRouter(prefix="/radar", tags=["Doppler Radar & InSAR Remote Sensing"])

@router.get("/live-frames")
async def get_live_radar_frames() -> Dict[str, Any]:
    """
    Returns live Doppler Weather Radar frames (timestamps, tile URLs)
    for nowcasting precipitation loops across North-East India.
    """
    return await fetch_live_radar_frames()

@router.get("/insar-deformation")
def get_insar_ground_motion() -> Dict[str, Any]:
    """
    Returns Sentinel-1 InSAR millimeter surface displacement points (LOS velocity mm/yr)
    and cumulative slope deformation across Meghalaya landslide sectors.
    """
    return get_insar_deformation_features()
