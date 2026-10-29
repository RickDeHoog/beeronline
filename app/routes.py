from flask import Blueprint, render_template, request, jsonify

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

@main_bp.route("/components/map")
def map():
    return render_template("/components/map.html")
