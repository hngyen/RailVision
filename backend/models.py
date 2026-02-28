from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, UniqueConstraint
from database import Base


class Departure(Base):
    __tablename__ = "departures"

    id = Column(Integer, primary_key=True, index=True)
    line = Column(String)
    line_name = Column(String)
    destination = Column(String)
    operator = Column(String)
    platform = Column(String)
    scheduled = Column(String)
    estimated = Column(String)
    delay_min = Column(Float)
    realtime = Column(Boolean)
    stop_id = Column(String)
    fetched_at = Column(String)  # when pulled from the API

    __table_args__ = (
        UniqueConstraint('line', 'scheduled', 'stop_id', name='unique_departure'),
    )