import random
import pandas as pd
from fastapi import APIRouter, HTTPException
from models.call_model import TriageReport
from services.excel_service import load_and_prepare_data
from services.dispatch_service import dispatch_ambulance

router = APIRouter(prefix="/api", tags=["Calls"])

# --- Global Ambulance Data ---
AMBULANCE_DF = load_and_prepare_data(
    filepath="data/AMBULANCE - Copy.csv",
    required_columns=['Lat', 'Long', 'Emergency_Level', 'availibility']
)

@router.get("/caller-info")
def get_caller_info():
    if random.random() < 0.2:
        return {"caller_id": "9876543210", "location": {"lat": 22.3072, "lng": 73.1812}}
    else:
        raise HTTPException(status_code=500, detail="Failed to retrieve caller info.")

@router.post("/triage-report")
def receive_triage_report(report: TriageReport):
    global AMBULANCE_DF
    dispatched_info, report_content = dispatch_ambulance(report, AMBULANCE_DF)

    return {
        "status": "success",
        "receivedData": report.model_dump(),
        "dispatchedAmbulance": dispatched_info,
        "report": report_content
    }
