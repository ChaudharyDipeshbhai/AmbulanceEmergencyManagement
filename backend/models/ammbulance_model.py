from pydantic import BaseModel

class Ambulance(BaseModel):
    Ambulance_ID: str
    Category: str
    Emergency_Level: int
    Latitude: float
    Longitude: float
    Status: str
