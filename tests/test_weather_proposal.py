"""
tests/test_weather_proposal.py

Tests that check if get_weather_analysis() keeps the promises in our project proposal.

get_weather_analysis() normally fetches real weather from the internet. In these tests
we replace the internet with a FAKE one, so:
  - we choose the weather (and therefore know the correct answer)
  - tests work without wifi and always give the same result
  - we can see exactly what the app asked the weather API for
"""

import pytest
import requests

from services import weather_api
from services.weather_api import get_weather_analysis


class FakeResponse:
    """
    Pretends to be the answer from the weather website.
    The real code calls .raise_for_status() and .json() on the answer,
    so our fake needs those two as well.
    """

    def __init__(self, data):
        self.data = data          # The made-up weather we want to hand back

    def raise_for_status(self):
        pass                      # Real version: crashes on errors like 404. Fake: always fine.

    def json(self):
        return self.data          # Real version: turns website text into a dictionary.


def fake_weather_data(now="2026-10-28T14:45", feels_like=20.0, rain_chances=None):
    """
    Builds made-up weather in the exact same format Open-Meteo sends.
    Default: it's 14:45 and 20°C, with no rain all day.

    rain_chances: optional list of 24 numbers, the rain chance (%) for each hour 00:00 to 23:00.
    """
    hours = [f"2026-10-28T{h:02d}:00" for h in range(24)]   # "2026-10-28T00:00" ... "T23:00"
    if rain_chances is None:
        rain_chances = [0] * 24                              # 0% rain every hour
    return {
        "current": {
            "time": now,
            "temperature_2m": feels_like,
            "apparent_temperature": feels_like,
            "precipitation": 0.0,
            "wind_speed_10m": 10.0,
            "weather_code": 0,                               # 0 = clear sky
        },
        "hourly": {
            "time": hours,
            "temperature_2m": [feels_like] * 24,
            "apparent_temperature": [feels_like] * 24,
            "precipitation_probability": rain_chances,
            "precipitation": [0.0] * 24,
            "wind_speed_10m": [10.0] * 24,
            "weather_code": [0] * 24,
        },
    }


def use_fake_internet(monkeypatch, data):
    """
    Swaps the real requests.get for a fake one that always returns `data`.
    Also writes down every call, so tests can check what the app asked for.
    monkeypatch automatically undoes the swap after each test.
    """
    calls = []

    def fake_get(url, params=None, timeout=None):
        calls.append({"url": url, "params": params, "timeout": timeout})   # Write down the call
        return FakeResponse(data)                                           # Hand back fake weather

    monkeypatch.setattr(weather_api.requests, "get", fake_get)   # The actual swap
    return calls



# ---------------------------------------------------------------------------
# Proposal promises
# ---------------------------------------------------------------------------

# Proposal: "utilizes live weather data"
def test_uses_live_weather_data(monkeypatch):
    use_fake_internet(monkeypatch, fake_weather_data(feels_like=22.0))
    result = get_weather_analysis()
    assert result["is_fallback"] is False      # Real (fake-internet) data was used, not backup data
    assert result["feels_like"] == 22.0        # The number from the "website" made it into the result


# Proposal: "and user location"
def test_uses_the_users_location(monkeypatch):
    calls = use_fake_internet(monkeypatch, fake_weather_data())
    get_weather_analysis(lat=52.37, lon=4.89)  # Amsterdam instead of the Leiden default
    assert calls[0]["params"]["latitude"] == 52.37
    assert calls[0]["params"]["longitude"] == 4.89


# Proposal: "open source alternatives" (free, no paywall)
def test_uses_free_api_without_key(monkeypatch):
    calls = use_fake_internet(monkeypatch, fake_weather_data())
    get_weather_analysis()
    assert "open-meteo.com" in calls[0]["url"]
    assert "apikey" not in calls[0]["params"]  # No secret key needed


# Proposal: "if the weather will change during your visit"
def test_spots_rain_coming_during_visit(monkeypatch):
    rain = [0] * 24
    rain[15] = 80                              # 80% rain at 15:00, it's now 14:45
    use_fake_internet(monkeypatch, fake_weather_data(rain_chances=rain))
    result = get_weather_analysis(visit_hours=3)   # Visit = 14:00, 15:00, 16:00
    assert result["rain_coming_later"] is True
    assert result["verdict"] == "STAY_INSIDE"


# Same promise, other side: rain AFTER you leave should not matter
def test_ignores_rain_after_visit_ends(monkeypatch):
    rain = [0] * 24
    rain[20] = 80                              # 80% rain at 20:00, long after the visit
    use_fake_internet(monkeypatch, fake_weather_data(rain_chances=rain))
    result = get_weather_analysis(visit_hours=3)
    assert result["verdict"] == "GREAT_TERRACE"


# Proposal: "easy to read when drunk"
def test_answer_is_simple_enough_for_drunk_users(monkeypatch):
    use_fake_internet(monkeypatch, fake_weather_data())
    result = get_weather_analysis()
    assert result["verdict"] in ("GREAT_TERRACE", "HEATED_TERRACE_ONLY", "STAY_INSIDE")
    assert result["headline"] != ""            # There is always a big readable headline


# The app must not crash during the demo if wifi is down
def test_no_internet_uses_backup_data(monkeypatch):
    def broken_get(*args, **kwargs):
        raise requests.ConnectionError("no wifi")   # Pretend the internet is down
    monkeypatch.setattr(weather_api.requests, "get", broken_get)
    result = get_weather_analysis()
    assert result["is_fallback"] is True       # Backup data used instead of crashing


# ---------------------------------------------------------------------------
# Known bugs (from Salah's code review).
# xfail = "expected to fail". These show what the app SHOULD do but doesn't yet.
# When someone fixes the bug, pytest will report XPASS: then remove the xfail line.
# ---------------------------------------------------------------------------

# Bug: if the current hour is missing from the forecast, the code silently
# uses index 0 (midnight) and judges the visit on the wrong hours.
@pytest.mark.xfail(reason="Known bug: if the current hour is missing, the code uses midnight's forecast")
def test_does_not_use_midnight_when_hour_missing(monkeypatch):
    rain = [0] * 24
    rain[0] = 90                               # Heavy rain at midnight only
    # "now" is 2 days later, so 14:45 is NOT in the forecast hours
    use_fake_internet(monkeypatch, fake_weather_data(now="2026-10-30T14:45", rain_chances=rain))
    result = get_weather_analysis()
    assert result["verdict"] != "STAY_INSIDE"  # Midnight's rain should not decide the afternoon


# Bug: only network errors are caught. Incomplete data from the API crashes the app.
@pytest.mark.xfail(reason="Known bug: incomplete API data crashes instead of using backup data")
def test_broken_api_data_does_not_crash(monkeypatch):
    use_fake_internet(monkeypatch, {"current": {}})   # The website answers, but the data is empty
    result = get_weather_analysis()
    assert result["is_fallback"] is True              # Should fall back, not crash