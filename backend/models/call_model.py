from pydantic import BaseModel, Field
from typing import Optional

class Location(BaseModel):
    lat: Optional[float] = None
    lng: Optional[float] = None

class TriageReport(BaseModel):
    caller_id: str
    location: Location
    emergency_level: int = Field(ge=1, le=4)
