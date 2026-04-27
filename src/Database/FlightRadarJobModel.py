from sqlalchemy import Column, String, Integer, JSON
from src.Database.FlightRadarBase import FlightRadarBase


class FlightRadarJob(FlightRadarBase):
    __tablename__ = "flightradar_jobs"

    status = Column(String, default="running")
    progress = Column(Integer, default=0)
    params = Column(JSON, nullable=True)
    error_message = Column(String, nullable=True)
