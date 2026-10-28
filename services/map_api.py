"""
services/map_api.py

Loads verified local Leiden pubs from a structured JSON database (`pubs_database.json`)
to ensure lightning-fast performance, zero network dependency during demos, and accurate
beer menu / terrace heating data.
"""

import json
import math
import os

# Default coordinates for Leiden city center (Beestenmarkt / Nieuwe Rijn area)
DEFAULT_LAT = 52.1601
DEFAULT_LON = 4.4970


def calculate_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> int:
    """
    Uses the Haversine formula to calculate the walking distance in meters
    between the user's coordinates and a pub's coordinates.
    """
    earth_radius_m = 6371000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return int(round(earth_radius_m * c))


def get_nearby_pubs(
    lat: float = DEFAULT_LAT,
    lon: float = DEFAULT_LON,
    radius_m: int = 1500,
    limit: int = 12,
) -> list[dict]:
    """
    Loads pubs from the local JSON database, calculates walking distances from the user,
    and returns them sorted by proximity.
    """
    # Locate pubs_database.json in the same directory as this script
    current_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(current_dir, "pubs_database.json")

    pubs = []
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            raw_pubs = json.load(f)

            for pub in raw_pubs:
                pub_lat = pub.get("lat", DEFAULT_LAT)
                pub_lon = pub.get("lon", DEFAULT_LON)
                distance_m = calculate_distance_meters(lat, lon, pub_lat, pub_lon)

                # Include pub if it's within the search radius
                if distance_m <= radius_m:
                    pub_copy = dict(pub)
                    pub_copy["distance_m"] = distance_m
                    pub_copy["is_fallback"] = False
                    pubs.append(pub_copy)

    except (FileNotFoundError, json.JSONDecodeError) as error:
        print(f"[WARNING] Could not load pubs_database.json ({error}). Using hardcoded fallback.")
        pubs = _get_emergency_fallback_pubs(lat, lon)

    # Sort by closest walking distance
    pubs.sort(key=lambda x: x["distance_m"])
    return pubs[:limit]


def _get_emergency_fallback_pubs(user_lat: float, user_lon: float) -> list[dict]:
    """Emergency fallback if JSON file is missing."""
    emergency_pub = {
        "name": "Belgisch Biercafé Olivier",
        "lat": 52.1589,
        "lon": 4.4906,
        "address": "Hooigracht 23",
        "has_terrace": True,
        "has_heating": True,
        "specialty": "Belgian Beer Café",
        "beer_menu": ["Tripel Karmeliet", "La Chouffe"],
        "distance_m": calculate_distance_meters(user_lat, user_lon, 52.1589, 4.4906),
        "is_fallback": True,
    }
    return [emergency_pub]


# Self-test block: Run `python3 services/map_api.py` in terminal to verify!
if __name__ == "__main__":
    print("Testing Local JSON Pub Database for Leiden...")
    found_pubs = get_nearby_pubs()
    print(f"Successfully loaded {len(found_pubs)} pubs:\n")
    for p in found_pubs:
        print(
            f"  - {p['name']} ({p['distance_m']}m) | "
            f"Terrace: {p['has_terrace']} | Heated: {p['has_heating']} | "
            f"Menu Beers: {', '.join(p.get('beer_menu', []))}"
        )