"""
services/weather_api.py

Handles fetching live current weather and short-term hourly forecasts from the
free Open-Meteo API (no API key required). It evaluates both the current weather
and the upcoming 3 hours ("during your visit") to produce a simple, drunk-friendly
terrace recommendation (Great Terrace, Heated Terrace Only, or Stay Inside).
"""

from datetime import datetime
import requests

# Default coordinates for Leiden city center (used if user location is not provided)
DEFAULT_LAT = 52.1601
DEFAULT_LON = 4.4970


def decode_wmo_code(code: int) -> str:
    """
    Translates standard WMO weather interpretation codes returned by Open-Meteo
    into simple, human-readable descriptions suitable for a drunk-friendly UI.
    """
    if code == 0:
        return "Clear sky"
    elif code in (1, 2, 3):
        return "Partly cloudy"
    elif code in (45, 48):
        return "Foggy"
    elif code in (51, 53, 55, 56, 57):
        return "Drizzle"
    elif code in (61, 63, 65, 66, 67, 80, 81, 82):
        return "Rainy"
    elif code in (71, 73, 75, 77, 85, 86):
        return "Snowy"
    elif code in (95, 96, 99):
        return "Thunderstorm"
    return "Cloudy"


def get_weather_analysis(lat: float = DEFAULT_LAT, lon: float = DEFAULT_LON, visit_hours: int = 3) -> dict:
    """
    Fetches live weather and hourly forecast for the next `visit_hours` hours.
    
    Parameters:
        lat (float): Latitude of the user/city.
        lon (float): Longitude of the user/city.
        visit_hours (int): How many hours the user plans to stay at the pub.
        
    Returns:
        dict: Processed weather summary including current stats, 3-hour outlook,
              whether heaters are needed, and a drunk-friendly terrace verdict.
    """
    url = "https://api.open-meteo.com/v1/forecast"
    
    # Request both current weather and hourly forecast variables from Open-Meteo
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": [
            "temperature_2m",
            "apparent_temperature",
            "precipitation",
            "wind_speed_10m",
            "weather_code",
        ],
        "hourly": [
            "temperature_2m",
            "apparent_temperature",
            "precipitation_probability",
            "precipitation",
            "wind_speed_10m",
            "weather_code",
        ],
        "timezone": "auto",
        "forecast_days": 2,  # Fetch 2 days so midnight visits still have next-hour data
    }

    try:
        # Make HTTP GET request with a 5-second timeout so the app never hangs
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()

        # 1. Extract Current Weather Data
        current = data["current"]
        current_temp = round(current["temperature_2m"], 1)
        feels_like = round(current["apparent_temperature"], 1)
        current_rain = current["precipitation"]
        wind_speed = round(current["wind_speed_10m"], 1)
        weather_code = current["weather_code"]
        condition_text = decode_wmo_code(weather_code)

        # 2. Extract Hourly Data for the Duration of the Pub Visit
        hourly = data["hourly"]
        hourly_times = hourly["time"]

        # Match the current hour ISO string (e.g. "2026-10-28T13:00") to find index
        current_hour_prefix = current["time"][:13]
        start_idx = 0
        for idx, time_str in enumerate(hourly_times):
            if time_str.startswith(current_hour_prefix):
                start_idx = idx
                break

        # Slice the next `visit_hours` hours (e.g. next 3 hours of the pub visit)
        end_idx = start_idx + visit_hours
        upcoming_rain_probs = hourly["precipitation_probability"][start_idx:end_idx]
        upcoming_precip = hourly["precipitation"][start_idx:end_idx]
        upcoming_feels_like = hourly["apparent_temperature"][start_idx:end_idx]

        # Calculate worst-case weather during the visit
        max_rain_prob_during_visit = max(upcoming_rain_probs) if upcoming_rain_probs else 0
        total_rain_during_visit = sum(upcoming_precip) if upcoming_precip else 0.0
        min_temp_during_visit = round(min(upcoming_feels_like), 1) if upcoming_feels_like else feels_like

        # Determine if weather will turn bad during the visit
        rain_now = current_rain > 0.1 or weather_code >= 51
        rain_coming_later = max_rain_prob_during_visit >= 50 or total_rain_during_visit > 0.3

        # 3. Evaluate Terrace Suitability (Drunk-Friendly Decision Logic)
        return _build_terrace_verdict(
            current_temp=current_temp,
            feels_like=feels_like,
            min_temp_during_visit=min_temp_during_visit,
            wind_speed=wind_speed,
            condition_text=condition_text,
            rain_now=rain_now,
            rain_coming_later=rain_coming_later,
            max_rain_prob=max_rain_prob_during_visit,
            is_fallback=False,
        )

    except requests.RequestException as error:
        # Fallback data if there is no internet or the API is unreachable during demo
        print(f"[WARNING] Weather API request failed ({error}). Using fallback data.")
        return _build_terrace_verdict(
            current_temp=14.0,
            feels_like=12.0,
            min_temp_during_visit=11.0,
            wind_speed=19.0,
            condition_text="Cloudy",
            rain_now=False,
            rain_coming_later=False,
            max_rain_prob=10,
            is_fallback=True,
        )


def _build_terrace_verdict(
    current_temp: float,
    feels_like: float,
    min_temp_during_visit: float,
    wind_speed: float,
    condition_text: str,
    rain_now: bool,
    rain_coming_later: bool,
    max_rain_prob: int,
    is_fallback: bool,
) -> dict:
    """
    Internal helper function that converts raw weather metrics into a clear,
    drunk-friendly decision on whether to sit outside, require terrace heating,
    or stay inside the pub.
    """
    # Case 1: Raining right now -> Go inside immediately
    if rain_now:
        verdict = "STAY_INSIDE"
        headline = "GO INSIDE! IT'S RAINING"
        advice = "Skip the terrace. Find a cozy indoor pub table."
        needs_heating = False

    # Case 2: Dry right now, but rain is coming during the 3-hour visit
    elif rain_coming_later:
        verdict = "STAY_INSIDE"
        headline = "TRAP ALERT: RAIN COMING SOON!"
        advice = (
            f"It looks dry now, but there is a {max_rain_prob}% chance of rain "
            "during your visit. Pick a pub with indoor seating or a covered roof!"
        )
        needs_heating = True

    # Case 3: Too freezing or too windy even for terrace heaters
    elif min_temp_during_visit < 7.0 or wind_speed > 35.0:
        verdict = "STAY_INSIDE"
        headline = "TOO COLD & WINDY FOR THE TERRACE"
        advice = f"Feels like {feels_like}°C with {wind_speed} km/h wind. Drink inside!"
        needs_heating = False

    # Case 4: Dry for the visit, but chilly (7°C to 16°C) -> Requires Terrace Heating!
    elif min_temp_during_visit < 16.0:
        verdict = "HEATED_TERRACE_ONLY"
        headline = "TERRACE OKAY — ONLY WITH HEATERS!"
        advice = (
            f"Dry for the next 3 hours, but feels like {feels_like}°C "
            f"(dropping to {min_temp_during_visit}°C). Filter for heated terraces!"
        )
        needs_heating = True

    # Case 5: Warm and dry for the next 3 hours -> Perfect terrace weather
    else:
        verdict = "GREAT_TERRACE"
        headline = "100% TERRACE WEATHER!"
        advice = f"Dry for the next 3 hours and feels like {feels_like}°C. Grab an outside table!"
        needs_heating = False

    return {
        "temp": current_temp,
        "feels_like": feels_like,
        "min_temp_visit": min_temp_during_visit,
        "wind_kmh": wind_speed,
        "condition": condition_text,
        "rain_now": rain_now,
        "rain_coming_later": rain_coming_later,
        "max_rain_prob_visit": max_rain_prob,
        "verdict": verdict,               # "GREAT_TERRACE", "HEATED_TERRACE_ONLY", or "STAY_INSIDE"
        "headline": headline,             # Big bold drunk-friendly banner text
        "advice": advice,                 # Short explanation for the user
        "needs_heating": needs_heating,   # Boolean used by map_api.py to highlight heated terraces
        "is_fallback": is_fallback,
    }


# Self-test block: Run `python3 services/weather_api.py` in terminal to verify!
if __name__ == "__main__":
    print("Testing Weather Service for Leiden...")
    result = get_weather_analysis()
    for key, value in result.items():
        print(f"  {key}: {value}")