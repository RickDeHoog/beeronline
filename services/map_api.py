"""
services/map_api.py

Loads verified local Leiden pubs from a structured JSON database (`pubs_database.json`)
to ensure lightning-fast performance, zero network dependency during demos, and accurate
beer menu / terrace heating data.
"""

import json
import math
import os
import requests

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
    Load pubs from JSON and return the closest ones.
    Distances are straight-line distances, not walking routes.
    """

    # A search radius or result limit cannot be negative.
    if radius_m < 0 or limit < 0:
        raise ValueError("radius_m and limit cannot be negative")

    # Find the JSON database in the same folder as this Python file.
    current_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(current_dir, "pubs_database.json")

    try:
        # Load the pub records from the JSON database.
        with open(json_path, "r", encoding="utf-8") as f:
            raw_pubs = json.load(f)

        # The database must contain a list of pub records.
        if not isinstance(raw_pubs, list):
            raise ValueError("Pub database must be a JSON list")

    except (OSError, json.JSONDecodeError, ValueError) as error:
        # Keep a clearly labelled demo pub if the database cannot load.
        print(f"[WARNING] Pub database unavailable ({error}). Using demo pub.")
        pubs = _get_emergency_fallback_pubs(lat, lon)

    else:
        # This section runs only if the database loaded successfully.
        pubs = []

        for pub in raw_pubs:
            try:
                # Every record must be a dictionary with a pub name.
                if not isinstance(pub, dict) or not pub.get("name"):
                    raise ValueError("Missing pub name")

                # Coordinates must exist; do not invent replacements.
                pub_lat = float(pub["lat"])
                pub_lon = float(pub["lon"])

                # Reject invalid coordinates.
                if (
                    isinstance(pub["lat"], bool)
                    or isinstance(pub["lon"], bool)
                    or not math.isfinite(pub_lat)
                    or not math.isfinite(pub_lon)
                    or not -90 <= pub_lat <= 90
                    or not -180 <= pub_lon <= 180
                ):
                    raise ValueError("Invalid pub coordinates")

            except (KeyError, ValueError, TypeError, OverflowError) as error:
                # Skip only this pub, not the entire database.
                print(f"[WARNING] Skipping invalid pub entry: {error}")
                continue

            # Calculate the straight-line distance to this pub.
            distance_m = calculate_distance_meters(
                lat, lon, pub_lat, pub_lon
            )

            # Keep the pub only if it is close enough.
            if distance_m <= radius_m:
                pub_copy = dict(pub)
                pub_copy["distance_m"] = distance_m
                pub_copy["is_fallback"] = False
                pubs.append(pub_copy)

    # Apply the distance limit even when using the emergency demo pub.
    pubs = [pub for pub in pubs if pub["distance_m"] <= radius_m]

    # Closest pubs first.
    pubs.sort(key=lambda pub: pub["distance_m"])

    # Return at most the requested number of pubs.
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


def get_osm_pub_candidates(
    lat: float = DEFAULT_LAT,
    lon: float = DEFAULT_LON,
    radius_m: int = 1500,
) -> list[dict]:
    """
    Find pubs, bars and cafes near a location using OpenStreetMap.

    Uses the Overpass API to discover possible venues.
    Beer menus and terrace heating are stored separately in our JSON database.
    """

    # 1. Check that the location and search radius are valid.
    if not -90 <= lat <= 90 or not -180 <= lon <= 180:
        raise ValueError("Invalid coordinates")

    if isinstance(radius_m, bool) or not isinstance(radius_m, int) or radius_m <= 0:
        raise ValueError("radius_m must be a positive integer")

    # 2. Create an Overpass query for pubs, bars and cafes.
    # 'nwr' searches nodes, ways and relations in OpenStreetMap.
    query = f"""
    [out:json][timeout:15];
    nwr["amenity"~"^(pub|bar|cafe|biergarten)$"]
       (around:{radius_m},{lat},{lon});
    out center;
    """

    # The public Overpass API endpoint.
    url = "https://overpass.private.coffee/api/interpreter"

    # 3. Identify our application to the Overpass server.
    # The server may reject generic Python requests with HTTP 406.
    headers = {
        "User-Agent": (
            "BeerOnline/0.1 "
            "(Leiden University student project; "
            "https://git.liacs.nl/s4832647/beeronline)"
        )
    }

    try:
        # 4. Send the query to the Overpass API.
        response = requests.post(
            url,
            data={"data": query},
            headers=headers,
            timeout=20,
        )

        # Raise an error if the server returns an HTTP error.
        response.raise_for_status()

        # Convert the JSON response into a Python dictionary.
        data = response.json()

        # Check that the response contains the expected results list.
        if not isinstance(data, dict) or not isinstance(data.get("elements"), list):
            raise ValueError("Unexpected OpenStreetMap response format")

    except (requests.RequestException, ValueError) as error:
        # An API failure should not crash the BeerOnline application.
        print(f"[WARNING] OpenStreetMap request failed: {error}")
        return []

    # 5. Convert the OpenStreetMap objects into simple pub dictionaries.
    candidates = []

    for element in data["elements"]:

        # Ignore incorrectly formatted elements.
        if not isinstance(element, dict):
            continue

        tags = element.get("tags", {})

        if not isinstance(tags, dict):
            continue

        # Nodes have coordinates directly.
        # Ways and relations can have a calculated centre.
        position = element.get("center", element)

        name = tags.get("name")

        # Skip venues without a name or coordinates.
        if (
            not isinstance(position, dict)
            or not isinstance(name, str)
            or not name.strip()
            or "lat" not in position
            or "lon" not in position
            or "id" not in element
            or "type" not in element
        ):
            continue

        # Save the useful geographic information.
        candidates.append({
            "name": name,
            "lat": position["lat"],
            "lon": position["lon"],
            "osm_id": element["id"],
            "osm_type": element["type"],
            "source": "OpenStreetMap",
        })

    # 6. Return all valid candidate venues.
    return candidates





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