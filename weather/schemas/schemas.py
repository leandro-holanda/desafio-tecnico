from pydantic import BaseModel


class CityResponse(BaseModel):
    name: str
    slug: str
    latitude: float
    longitude: float
