"""
tests/test_weather_api.py

Tests for services/weather_api.py, based on the promises in our project proposal:
  - "recommend pubs suited to the current weather"
  - "whether or not a terrace has heating"
  - "if the weather will change during your visit"

These tests check the decision logic (_build_terrace_verdict) directly.
That function needs no internet, so the tests are fast and always give the same result.

How to run all tests (from the project root, the beeronline folder):
    python -m pytest
"""

from services.weather_api import _build_terrace_verdict


def get_weather_result(**changes):
    """
    Helper: gives the weather "judge" (_build_terrace_verdict) a form that is
    already filled in with perfect weather (20°C, dry, little wind), and only
    changes the values you pass in. Returns the judge's full result (a dictionary).

    Example: get_weather_result(rain_now=True) -> same perfect weather, but raining.
    This keeps every test short and shows exactly what that test is about.
    """
    # Built fresh on every call, so changes from one test never leak into another.
    weather = {
        "current_temp": 20.0,
        "feels_like": 20.0,
        "min_temp_during_visit": 20.0,
        "wind_speed": 10.0,
        "condition_text": "Clear sky",
        "rain_now": False,
        "rain_coming_later": False,
        "max_rain_prob": 0,
        "is_fallback": False,
    }
    weather.update(changes)  # Overwrite only the values this test cares about
    return _build_terrace_verdict(**weather)


# ---------------------------------------------------------------------------
# Proposal promises: does the app make the right decision for the weather?
# ---------------------------------------------------------------------------

# Proposal: "recommend pubs suited to the current weather"
def test_warm_and_dry_is_great_terrace():
    assert get_weather_result()["verdict"] == "GREAT_TERRACE"


# Proposal: "whether or not a terrace has heating"
def test_chilly_and_dry_needs_heated_terrace():
    result = get_weather_result(feels_like=12.0, min_temp_during_visit=12.0)
    assert result["verdict"] == "HEATED_TERRACE_ONLY"
    assert result["needs_heating"] is True


def test_raining_now_means_stay_inside():
    assert get_weather_result(rain_now=True)["verdict"] == "STAY_INSIDE"


# Proposal: "if the weather will change during your visit"
def test_rain_coming_during_visit_means_stay_inside():
    result = get_weather_result(rain_coming_later=True, max_rain_prob=80)
    assert result["verdict"] == "STAY_INSIDE"
    assert "80%" in result["advice"]  # The user is told how likely the rain is


def test_too_cold_means_stay_inside():
    assert get_weather_result(feels_like=4.0, min_temp_during_visit=4.0)["verdict"] == "STAY_INSIDE"


def test_too_windy_means_stay_inside():
    assert get_weather_result(wind_speed=40.0)["verdict"] == "STAY_INSIDE"


# ---------------------------------------------------------------------------
# Edge cases: the exact cut-off lines where the decision switches.
# ---------------------------------------------------------------------------

# Exactly 7°C is the lowest temperature that still allows a heated terrace.
def test_exactly_7_degrees_is_heated_terrace():
    assert get_weather_result(feels_like=7.0, min_temp_during_visit=7.0)["verdict"] == "HEATED_TERRACE_ONLY"


# Just under 7°C is too cold, even with heaters.
def test_just_below_7_degrees_is_stay_inside():
    assert get_weather_result(feels_like=6.9, min_temp_during_visit=6.9)["verdict"] == "STAY_INSIDE"


# Exactly 16°C is warm enough for any terrace.
def test_exactly_16_degrees_is_great_terrace():
    assert get_weather_result(feels_like=16.0, min_temp_during_visit=16.0)["verdict"] == "GREAT_TERRACE"


# Just under 16°C needs heaters.
def test_just_below_16_degrees_is_heated_terrace():
    assert get_weather_result(feels_like=15.9, min_temp_during_visit=15.9)["verdict"] == "HEATED_TERRACE_ONLY"


# The wind limit is "more than 35", so exactly 35 km/h is still fine.
def test_exactly_35_kmh_wind_is_still_ok():
    assert get_weather_result(wind_speed=35.0)["verdict"] == "GREAT_TERRACE"


# Rain beats everything: even on a hot day, rain means go inside.
def test_warm_but_raining_still_means_stay_inside():
    assert get_weather_result(feels_like=25.0, min_temp_during_visit=25.0, rain_now=True)["verdict"] == "STAY_INSIDE"