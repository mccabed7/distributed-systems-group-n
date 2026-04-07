import json
from typing import Optional
from sqlalchemy.orm import Session
from app.models import Journey


def create_journey(db: Session, data: dict) -> Journey:
    # Serialise way_ids list to JSON string for storage
    data = {**data, "way_ids": json.dumps(data["way_ids"])}
    journey = Journey(**data)
    db.add(journey)
    db.commit()
    db.refresh(journey)
    return journey


def get_journey(db: Session, journey_id: str) -> Optional[Journey]:
    journey = db.query(Journey).filter(Journey.id == journey_id).first()
    if journey:
        journey.way_ids = json.loads(journey.way_ids)
    return journey


def delete_journey(db: Session, journey_id: str) -> bool:
    journey = db.query(Journey).filter(Journey.id == journey_id).first()
    if not journey:
        return False
    db.delete(journey)
    db.commit()
    return True
