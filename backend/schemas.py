from pydantic import BaseModel
from typing import Optional


class DepartureOut(BaseModel):
    line: Optional[str] = None
    lineName: Optional[str] = None
    destination: Optional[str] = None
    operator: Optional[str] = None
    platform: Optional[str] = None
    scheduled_dt: Optional[str] = None
    estimated_dt: Optional[str] = None
    delay_min: Optional[float] = None
    realtime: Optional[bool] = None


class ErrorOut(BaseModel):
    detail: str
