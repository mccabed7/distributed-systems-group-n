import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, DateTime, Text
from app.database import Base


class Journey(Base):
    __tablename__ = "journeys"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    origin = Column(String, nullable=False)
    destination = Column(String, nullable=False)
    distance_m = Column(Float, nullable=False)
    duration_s = Column(Float, nullable=False)
    # JSON-encoded list of {way_id, country} objects
    way_ids = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
