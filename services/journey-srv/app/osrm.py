"""
osrm.py — Route planning via OSRM and country enrichment via Nominatim.

Flow:
  1. Forward geocode origin/destination names → coordinates (Nominatim)
  2. Request a route between those coordinates (OSRM)
  3. Decode the route geometry (polyline6 encoding)
  4. Sample N points evenly along the geometry
  5. Reverse geocode each sample point → country (Nominatim)
  6. Assign the nearest sampled country to each way ID
  7. Return distance_m, duration_s, and enriched way_ids list
"""

import asyncio
import math
from typing import Optional

import httpx

NOMINATIM_BASE = "https://nominatim.openstreetmap.org"
OSRM_BASE = "https://router.project-osrm.org"

SAMPLE_COUNT = 5

HEADERS = {"User-Agent": "journey-service-poc/1.0"}

def _decode_polyline6(encoded: str) -> list[tuple[float, float]]:
    coords = []
    index = 0
    lat = 0
    lng = 0

    while index < len(encoded):
        for is_lng in (False, True):
            shift = 0
            result = 0
            while True:
                b = ord(encoded[index]) - 63
                index += 1
                result |= (b & 0x1F) << shift
                shift += 5
                if b < 0x20:
                    break
            value = ~(result >> 1) if result & 1 else result >> 1
            if is_lng:
                lng += value
                coords.append((lat / 1e6, lng / 1e6))
            else:
                lat += value

    return coords

def _haversine(p1: tuple[float, float], p2: tuple[float, float]) -> float:
    R = 6_371_000
    lat1, lon1 = math.radians(p1[0]), math.radians(p1[1])
    lat2, lon2 = math.radians(p2[0]), math.radians(p2[1])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


def _sample_geometry(
    coords: list[tuple[float, float]], n: int
) -> list[tuple[float, float]]:
    if len(coords) <= n:
        return coords
    step = (len(coords) - 1) / (n - 1)
    return [coords[round(i * step)] for i in range(n)]


def _nearest_country(
    way_index: int,
    total_ways: int,
    sample_countries: list[Optional[str]],
) -> Optional[str]:
    if not sample_countries:
        return None
    ratio = way_index / max(total_ways - 1, 1)
    sample_index = round(ratio * (len(sample_countries) - 1))
    return sample_countries[sample_index]


async def _forward_geocode(client: httpx.AsyncClient, place: str) -> tuple[float, float]:
    resp = await client.get(
        f"{NOMINATIM_BASE}/search",
        params={"q": place, "format": "json", "limit": 1},
        headers=HEADERS,
    )
    resp.raise_for_status()
    results = resp.json()
    if not results:
        raise ValueError(f"Could not geocode place: '{place}'")
    return float(results[0]["lat"]), float(results[0]["lon"])


async def _reverse_geocode_country(
    client: httpx.AsyncClient, lat: float, lon: float
) -> Optional[str]:
    try:
        resp = await client.get(
            f"{NOMINATIM_BASE}/reverse",
            params={"lat": lat, "lon": lon, "format": "json", "zoom": 3},
            headers=HEADERS,
        )
        resp.raise_for_status()
        data = resp.json()
        country = data.get("address", {}).get("country")
        if country:
            country = country.split("/")[-1].strip()
        return country
    except Exception:
        return None



async def get_route(origin: str, destination: str) -> dict:

    async with httpx.AsyncClient(timeout=15.0) as client:

        origin_coords = await _forward_geocode(client, origin)
        await asyncio.sleep(1.1)  # Nominatim: max 1 req/sec
        destination_coords = await _forward_geocode(client, destination)

        coord_str = (
            f"{origin_coords[1]},{origin_coords[0]};"
            f"{destination_coords[1]},{destination_coords[0]}"
        )
        osrm_resp = await client.get(
            f"{OSRM_BASE}/route/v1/driving/{coord_str}",
            params={
                "overview": "full",
                "geometries": "polyline6",
                "annotations": "true",
            },
        )
        osrm_resp.raise_for_status()
        osrm_data = osrm_resp.json()

        if osrm_data.get("code") != "Ok" or not osrm_data.get("routes"):
            raise ValueError(f"OSRM returned no route: {osrm_data.get('code')}")

        route = osrm_data["routes"][0]
        distance_m = route["distance"]
        duration_s = route["duration"]

        node_ids_raw: list[int] = []
        for leg in route.get("legs", []):
            annotation = leg.get("annotation", {})
            node_ids_raw.extend(annotation.get("nodes", []))

        seen: set[int] = set()
        way_ids_raw: list[int] = []
        for nid in node_ids_raw:
            if nid not in seen:
                seen.add(nid)
                way_ids_raw.append(nid)

        encoded_geometry = route["geometry"]
        coords = _decode_polyline6(encoded_geometry)
        sample_points = _sample_geometry(coords, SAMPLE_COUNT)

        sample_countries: list[Optional[str]] = []
        for point in sample_points:
            country = await _reverse_geocode_country(client, point[0], point[1])
            sample_countries.append(country)
            await asyncio.sleep(1.1)

        enriched = [
            {
                "way_id": wid,
                "country": _nearest_country(i, len(way_ids_raw), sample_countries),
            }
            for i, wid in enumerate(way_ids_raw)
        ]

    return {
        "distance_m": distance_m,
        "duration_s": duration_s,
        "way_ids": enriched,
    }
