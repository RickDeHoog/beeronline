
"""
services/weather_api.py

Fetches current weather and the hourly forecast from Open-Meteo.
Checks the weather during a pub visit and recommends terrace or indoor seating.
"""

from datetime import datetime, timedelta
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


def get_weather_analysis(
    lat: float = DEFAULT_LAT,
    lon: float = DEFAULT_LON,
    visit_hours: int = 3,
) -> dict:
    """Get current weather and forecast for a visit lasting visit_hours hours."""

    # Keep visit length simple: whole hours only, between 1 and 24.
    # Invalid input is a programming/user-input error, not a weather API failure.
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
        "forecast_days": 2,  # Include tomorrow for visits crossing midnight.
    }

    try:
        # timeout=5 avoids waiting forever if the internet connection fails.
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()

        # 1. Read current weather.
        current = data["current"]
        current_temp = round(current["temperature_2m"], 1)
        feels_like = round(current["apparent_temperature"], 1)
        current_rain = current["precipitation"]
        wind_speed = round(current["wind_speed_10m"], 1)
        weather_code = current["weather_code"]
        condition_text = decode_wmo_code(weather_code)

        # 2. Find the correct forecast hours for the whole visit.
        hourly = data["hourly"]
        hourly_times = hourly["time"]
        current_time = datetime.fromisoformat(current["time"])
        start_hour = current_time.replace(minute=0, second=0, microsecond=0)
        visit_end = current_time + timedelta(hours=visit_hours)

        # Find the hourly forecast entry for the current hour.
        # If it is missing, do NOT silently use the first forecast entry.
        start_idx = next(
            (i for i, time_str in enumerate(hourly_times)
             if datetime.fromisoformat(time_str) == start_hour),
            None,
        )
        if start_idx is None:
            raise ValueError("Current hour is missing from the forecast")

        # Include every hour touched by the visit. For example, 13:30 to
        # 16:30 needs forecasts for 13:00, 14:00, 15:00 AND 16:00.
        # Also check that none of those hours are missing or out of order.
        end_idx = start_idx
        expected_hour = start_hour
        while expected_hour < visit_end:
            if (end_idx >= len(hourly_times)
                    or datetime.fromisoformat(hourly_times[end_idx]) != expected_hour):
                raise ValueError("A required forecast hour is missing")
            end_idx += 1
            expected_hour += timedelta(hours=1)

        # Each weather array must contain values for all selected hours.
        for key in ("precipitation_probability", "precipitation", "apparent_temperature"):
            if len(hourly[key]) < end_idx:
                raise ValueError(f"Missing hourly values for {key}")

        upcoming_rain_probs = hourly["precipitation_probability"][start_idx:end_idx]
        upcoming_precip = hourly["precipitation"][start_idx:end_idx]
        upcoming_feels_like = hourly["apparent_temperature"][start_idx:end_idx]

        # Use the wettest/coldest forecast hour to make a cautious recommendation.
        max_rain_prob_during_visit = max(upcoming_rain_probs)
        total_rain_during_visit = sum(upcoming_precip)
        min_temp_during_visit = round(min(upcoming_feels_like), 1)

        rain_now = current_rain > 0.1 or weather_code >= 51
        rain_coming_later = max_rain_prob_during_visit >= 50 or total_rain_during_visit > 0.3

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
        )

    except (requests.RequestException, KeyError, TypeError, ValueError, IndexError) as error:
        # Demo values if the request fails OR the response contains bad data.
        # The frontend should show is_fallback=True as 'demo/sample weather'.
        print(f"[WARNING] Weather data unavailable ({error}). Using sample weather.")
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
            visit_hours=visit_hours,
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
    visit_hours: int = 3,
) -> dict:
    """Convert weather measurements into a simple seating recommendation."""
    duration_text = f"{visit_hours} hour{'s' if visit_hours != 1 else ''}"

    # Case 1: Already raining.
    if rain_now:
        verdict = "STAY_INSIDE"
        headline = "GO INSIDE! IT'S RAINING"
        advice = "Skip the terrace. Find a cozy indoor pub table."
        needs_heating = False

    # Case 2: Rain is expected during the visit.
    elif rain_coming_later:
        verdict = "STAY_INSIDE"
        headline = "TRAP ALERT: RAIN COMING SOON!"
        advice = (
            f"It looks dry now, but there is a {max_rain_prob}% chance of rain "
            "during your visit. Pick a pub with indoor seating or a covered roof!"
        )
        needs_heating = True

    # Case 3: Too cold or windy for a terrace.
    elif min_temp_during_visit < 7.0 or wind_speed > 35.0:
        verdict = "STAY_INSIDE"
        headline = "TOO COLD & WINDY FOR THE TERRACE"
        advice = f"Feels like {feels_like}°C with {wind_speed} km/h wind. Drink inside!"
        needs_heating = False

    # Case 4: Dry, but cold enough to need terrace heating.
    elif min_temp_during_visit < 16.0:
        verdict = "HEATED_TERRACE_ONLY"
        headline = "TERRACE OKAY — ONLY WITH HEATERS!"
        advice = (
            f"Dry for the next {duration_text}, but feels like {feels_like}°C "
            f"(dropping to {min_temp_during_visit}°C). Filter for heated terraces!"
        )
        needs_heating = True

    # Case 5: Warm and dry enough for an ordinary terrace.
    else:
        verdict = "GREAT_TERRACE"
        headline = "100% TERRACE WEATHER!"
        advice = f"Dry for the next {duration_text} and feels like {feels_like}°C. Grab an outside table!"
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
