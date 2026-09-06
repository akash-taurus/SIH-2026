from fastapi import APIRouter, Form, UploadFile, File, Request
from typing import List, Optional
from app.database import get_reports, add_report
from app.schemas import ReportResponse

router = APIRouter(tags=["Reports"])

@router.get("/reports", response_model=List[ReportResponse])
async def get_recent_reports():
    """
    Returns verified citizen and field responder hazard observations.
    """
    return get_reports()

@router.post("/reports", response_model=ReportResponse)
async def submit_report(
    note: str = Form(...),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    severity: Optional[str] = Form("high"),
    photo: Optional[UploadFile] = File(None)
):
    """
    Submits a new ground observation report with coordinates and optional photo attachment.
    """
    location_desc = f"{latitude:.4f}° N, {longitude:.4f}° E" if latitude and longitude else "Field Location Pending"
    
    report_data = {
        "reporter": "Citizen Field Responder",
        "location_name": location_desc,
        "latitude": latitude,
        "longitude": longitude,
        "note": note,
        "severity": severity,
        "photo_url": f"/uploads/{photo.filename}" if photo else None
    }
    
    created = add_report(report_data)
    return created
