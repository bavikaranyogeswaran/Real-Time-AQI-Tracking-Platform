from pydantic import BaseModel, field_validator


class LocationIn(BaseModel):
    city: str
    country: str
    latitude: float
    longitude: float

    @field_validator("city", "country", mode="before")
    @classmethod
    def normalize_name(cls, v: str) -> str:
        return v.strip().title()


class LocationOut(BaseModel):
    location_id: str
    city: str
    country: str
    latitude: float
    longitude: float
    source: str

    model_config = {"from_attributes": True}
