import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import crud
from app.database import get_db
from app.osrm import get_route
from app.schemas import CreateJourneyRequest, JourneyResponse

router = APIRouter(prefix="/journeys", tags=["journeys"])


@router.post("", response_model=JourneyResponse, status_code=201)
async def create_journey(request: CreateJourneyRequest, db: Session = Depends(get_db)):
    """
    Geocode origin/destination, fetch a real road route from OSRM,
    enrich way IDs with country data via Nominatim, and persist the result.
    """
    try:
        route = await get_route(request.origin, request.destination)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Upstream routing error: {e}")

    journey = crud.create_journey(db, {
        "id": str(uuid.uuid4()),
        "origin": request.origin,
        "destination": request.destination,
        "distance_m": route["distance_m"],
        "duration_s": route["duration_s"],
        "way_ids": route["way_ids"],
    })

    return journey


@router.get("/{journey_id}", response_model=JourneyResponse)
def get_journey(journey_id: str, db: Session = Depends(get_db)):
    """Fetch a stored journey by ID, including its enriched way IDs."""
    journey = crud.get_journey(db, journey_id)
    if not journey:
        raise HTTPException(status_code=404, detail="Journey not found")
    return journey


@router.delete("/{journey_id}", status_code=204)
def delete_journey(journey_id: str, db: Session = Depends(get_db)):
    """Delete a journey."""
    if not crud.delete_journey(db, journey_id):
        raise HTTPException(status_code=404, detail="Journey not found")
