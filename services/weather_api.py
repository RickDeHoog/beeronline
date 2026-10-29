
"""
services/weather_api.py

Fetches current weather and the hourly forecast from Open-Meteo.
Checks the weather during a pub visit and recommends terrace or indoor seating.
"""

from datetime import datetime, timedelta
import math
import requests  # Lets Python request weather data from the internet.

# Leiden city centre is used when the user does not provide a location.
DEFAULT_LAT = 52.1601
DEFAULT_LON = 4.4970


def decode_wmo_code(code: int) -> str:
    """Translate Open-Meteo weather codes into short descriptions."""
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


def _valid_number(value, field_name: str) -> float:
    """Reject missing, non-numeric or non-finite API measurements."""
    if isinstance(value, bool):
        raise ValueError(f"Invalid weather value for {field_name}")
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError(f"Invalid weather value for {field_name}") from error
    if not math.isfinite(number):
        raise ValueError(f"Invalid weather value for {field_name}")
    return number


def get_weather_analysis(
    lat: float = DEFAULT_LAT,
    lon: float = DEFAULT_LON,
    visit_hours: int = 3,
) -> dict:
    """Get current weather and forecast for a visit lasting visit_hours hours."""

    # Keep visit length simple: whole hours only, between 1 and 24.
    if isinstance(visit_hours, bool) or not isinstance(visit_hours, int) or not 1 <= visit_hours <= 24:
        raise ValueError("visit_hours must be a whole number between 1 and 24")

    url = "https://api.open-meteo.com/v1/forecast"

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
        "timezone": "auto",  # Use local time for the requested coordinates.
        "wind_speed_unit": "kmh",  # Keep the wind threshold in km/h.
        "forecast_days": 2,  # Include tomorrow for visits crossing midnight.
    }

    try:
        # timeout=5 avoids waiting forever if the internet connection fails.
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()

        # 1. Read and validate current weather.
        current = data["current"]
        current_temp = round(_valid_number(current["temperature_2m"], "current temperature"), 1)
        feels_like = round(_valid_number(current["apparent_temperature"], "current feels-like temperature"), 1)
        current_rain = _valid_number(current["precipitation"], "current precipitation")
        wind_speed = round(_valid_number(current["wind_speed_10m"], "current wind speed"), 1)
        weather_code = int(_valid_number(current["weather_code"], "current weather code"))
        condition_text = decode_wmo_code(weather_code)

        # 2. Find the correct forecast hours for the whole visit.
        hourly = data["hourly"]
        hourly_times = hourly["time"]
        if not isinstance(hourly_times, list):
            raise ValueError("Hourly timestamps must be a list")
        current_time = datetime.fromisoformat(current["time"])
        start_hour = current_time.replace(minute=0, second=0, microsecond=0)
        visit_end = current_time + timedelta(hours=visit_hours)

        # Never silently use forecast index zero when the current hour is absent.
        start_idx = next(
            (i for i, time_str in enumerate(hourly_times)
             if datetime.fromisoformat(time_str) == start_hour),
            None,
        )
        if start_idx is None:
            raise ValueError("Current hour is missing from the forecast")

        # Include every hour touched by the visit, including the final partial hour.
        # Check the hours are consecutive (no gaps or out-of-order entries).
        end_idx = start_idx
        expected_hour = start_hour
        while expected_hour < visit_end:
            if (end_idx >= len(hourly_times)
                    or datetime.fromisoformat(hourly_times[end_idx]) != expected_hour):
                raise ValueError("A required forecast hour is missing")
            end_idx += 1
            expected_hour += timedelta(hours=1)

        # Check that every required array contains all forecast hours.
        required_keys = (
            "precipitation_probability", "precipitation", "apparent_temperature",
            "wind_speed_10m", "weather_code",
        )
        for key in required_keys:
            if not isinstance(hourly[key], list) or len(hourly[key]) < end_idx:
                raise ValueError(f"Missing hourly values for {key}")

        # Convert all selected measurements to numbers; reject null/NaN values.
        upcoming_rain_probs = [
            _valid_number(x, "precipitation_probability")
            for x in hourly["precipitation_probability"][start_idx:end_idx]
        ]
        upcoming_precip = [
            _valid_number(x, "precipitation")
            for x in hourly["precipitation"][start_idx:end_idx]
        ]
        upcoming_feels_like = [
            _valid_number(x, "apparent_temperature")
            for x in hourly["apparent_temperature"][start_idx:end_idx]
        ]
        upcoming_winds = [
            _valid_number(x, "wind_speed_10m")
            for x in hourly["wind_speed_10m"][start_idx:end_idx]
        ]
        upcoming_codes = [
            int(_valid_number(x, "weather_code"))
            for x in hourly["weather_code"][start_idx:end_idx]
        ]

        # Reject measurements outside their meaningful ranges.
        if (current_rain < 0 or wind_speed < 0
                or any(not 0 <= p <= 100 for p in upcoming_rain_probs)
                or any(p < 0 for p in upcoming_precip)
                or any(w < 0 for w in upcoming_winds)):
            raise ValueError("Weather measurements outside valid ranges")

        # Use the wettest, coldest and windiest period of the visit.
        max_rain_prob_during_visit = max(upcoming_rain_probs)
        total_rain_during_visit = sum(upcoming_precip)
        min_temp_during_visit = round(min(upcoming_feels_like), 1)
        max_wind_during_visit = round(max(wind_speed, *upcoming_winds), 1)

        # The original 'rain_now' name is retained for compatibility.
        # Treat snow and thunderstorms as bad outdoor weather too.
        bad_weather_codes = {
            51, 53, 55, 56, 57, 61, 63, 65, 66, 67,
            71, 73, 75, 77, 80, 81, 82, 85, 86, 95, 96, 99,
        }
        rain_now = current_rain > 0.1 or weather_code in bad_weather_codes
        rain_coming_later = (
            max_rain_prob_during_visit >= 50
            or total_rain_during_visit > 0.3
            or any(code in bad_weather_codes for code in upcoming_codes)
        )

        # 3. Turn the measurements into a simple terrace verdict.
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
            visit_hours=visit_hours,
            max_wind_during_visit=max_wind_during_visit,
        )

    except (requests.RequestException, KeyError, TypeError, ValueError, IndexError, OverflowError) as error:
        # These are sample values, NOT real weather. Display the fallback flag in the UI.
        print(f"[WARNING] Weather data unavailable ({error}). Using sample weather.")
        fallback = _build_terrace_verdict(
            current_temp=14.0,
            feels_like=12.0,
            min_temp_during_visit=11.0,
            wind_speed=19.0,
            condition_text="Cloudy",
            rain_now=False,
            rain_coming_later=False,
            max_rain_prob=10,
            is_fallback=True,
            visit_hours=visit_hours,
            max_wind_during_visit=19.0,
        )
        # Make it obvious this is example data, even before the UI is built.
        fallback["headline"] = "SAMPLE WEATHER — NOT LIVE"
        fallback["advice"] = "Live weather is unavailable. These are demo values, not a real forecast."
        return fallback


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
    visit_hours: int = 3,
    max_wind_during_visit: float | None = None,
) -> dict:
    """Convert weather measurements into a simple seating recommendation."""
    duration_text = f"{visit_hours} hour{'s' if visit_hours != 1 else ''}"
    if max_wind_during_visit is None:
        max_wind_during_visit = wind_speed

    # Case 1: Bad weather happening now (rain, snow or thunderstorms).
    if rain_now:
        verdict = "STAY_INSIDE"
        headline = "BAD WEATHER — GO INSIDE!"
        advice = "Rain, snow or storms make outdoor seating unsuitable. Find an indoor pub table."
        needs_heating = False

    # Case 2: Bad weather is forecast during the visit.
    elif rain_coming_later:
        verdict = "STAY_INSIDE"
        headline = "BAD WEATHER POSSIBLE DURING YOUR VISIT!"
        advice = (
            f"Precipitation may occur during the next {duration_text} "
            f"(highest hourly probability: {max_rain_prob}%). Choose indoor seating!"
        )
        needs_heating = False

    # Case 3: Too cold or too windy, considering the whole visit.
    elif min_temp_during_visit < 7.0 or max_wind_during_visit > 35.0:
        verdict = "STAY_INSIDE"
        headline = "TOO COLD OR WINDY FOR THE TERRACE"
        advice = (
            f"Feels like {feels_like}°C, dropping to {min_temp_during_visit}°C, "
            f"with winds up to {max_wind_during_visit} km/h. Drink inside!"
        )
        needs_heating = False

    # Case 4: Dry but chilly enough to need terrace heaters.
    elif min_temp_during_visit < 16.0:
        verdict = "HEATED_TERRACE_ONLY"
        headline = "TERRACE OKAY — ONLY WITH HEATERS!"
        advice = (
            f"Dry for the next {duration_text}, but feels like {feels_like}°C "
            f"(dropping to {min_temp_during_visit}°C). Filter for heated terraces!"
        )
        needs_heating = True

    # Case 5: Warm, dry and not too windy for an ordinary terrace.
    else:
        verdict = "GREAT_TERRACE"
        headline = "GREAT TERRACE WEATHER!"
        advice = (
            f"Dry for the next {duration_text} and feels like {feels_like}°C. "
            "Grab an outside table!"
        )
        needs_heating = False

    return {
        "temp": current_temp,
        "feels_like": feels_like,
        "min_temp_visit": min_temp_during_visit,
        "wind_kmh": wind_speed,  # Current wind speed.
        "max_wind_kmh_visit": max_wind_during_visit,  # New: maximum wind during visit.
        "condition": condition_text,
        "rain_now": rain_now,
        "rain_coming_later": rain_coming_later,
        "max_rain_prob_visit": max_rain_prob,
        "verdict": verdict,
        "headline": headline,
        "advice": advice,
        "needs_heating": needs_heating,
        "is_fallback": is_fallback,
    }


# Quick manual test: python services/weather_api.py
if __name__ == "__main__":
    print("Testing Weather Service for Leiden...")
    result = get_weather_analysis()
    for key, value in result.items():
        print(f"  {key}: {value}")
