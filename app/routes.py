from flask import Blueprint, render_template, request, jsonify
from services.map_api import get_nearby_pubs
from services.recommender import (
    get_weather_beer_recommendation,
    recommend_pubs_for_weather,
)
from services.weather_api import get_weather_analysis

main_bp = Blueprint("main", __name__)

DEFAULT_LOCATION = {
    "lat": 52.1601,
    "lon": 4.4970,
    "name": "Leiden"
}

@main_bp.context_processor
def inject_location():
    return {
        "default_location": DEFAULT_LOCATION
}


@main_bp.route("/")
def home():
    return render_template("index.html")


@main_bp.route("/api/pubs")
def api_nearby_pubs():
    try:
        lat = float(request.args.get("lat", DEFAULT_LOCATION["lat"]))
        lon = float(request.args.get("lon", DEFAULT_LOCATION["lon"]))
        radius_m = int(request.args.get("radius_m", 1500))
        limit = int(request.args.get("limit", 12))


        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            return jsonify({"error": "Invalid coordinates"}), 400


        if radius_m < 0 or limit < 0:
            return jsonify({
                "error": "radius_m and limit cannot be negative"
            }), 400

        pubs = get_nearby_pubs(
            lat=lat,
            lon=lon,
            radius_m=radius_m,
            limit=limit
        )

        if pubs:
            weather = get_weather_analysis(lat=lat, lon=lon, visit_hours=3)
            pubs = recommend_pubs_for_weather(pubs, weather)

        return jsonify({
            "pubs": pubs,
            "count": len(pubs),
        })

    except (TypeError, ValueError, OverflowError):
        return jsonify({"error": "Invalid query parameters"}), 400


@main_bp.route("/api/weather")
def api_weather():
    try:
        lat = float(request.args.get("lat", DEFAULT_LOCATION["lat"]))
        lon = float(request.args.get("lon", DEFAULT_LOCATION["lon"]))
        visit_hours = int(request.args.get("visit_hours", 3))

        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            return jsonify({"error": "Invalid coordinates"}), 400

        weather = get_weather_analysis(
            lat=lat,
            lon=lon,
            visit_hours=visit_hours
        )

        weather["beer_recommendation"] = get_weather_beer_recommendation(weather)
        return jsonify(weather)
    
    except (TypeError, ValueError, OverflowError):
        return jsonify({"error": "Invalid query parameters"}), 400
