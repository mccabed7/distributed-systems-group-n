from fastapi import FastAPI
from app.database import engine, Base
from app.routers import journeys

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Journey Service",
    description="Generates and stores road routes using OSRM, enriched with OSM way IDs and country data.",
    version="0.1.0",
)

app.include_router(journeys.router)


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok", "service": "journey-service"}
