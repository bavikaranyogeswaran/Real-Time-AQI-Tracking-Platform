from pydantic import BaseModel


class LocationOut(BaseModel):
    location_id: str
    city: str
    country: str
    latitude: float
    longitude: float
    source: str

    model_config = {"from_attributes": True}
