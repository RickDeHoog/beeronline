"""
services/recommender.py

Combines processed weather analysis (from weather_api.py) with nearby pub data
(from map_api.py) to:
1. Recommend an ideal beer style and drink based on current temperature and rain.
2. Filter, rank, and badge nearby pubs according to whether it is terrace weather,
   heated-terrace-only weather, or indoor pub weather.
3. Assign a tailored beer recommendation for each respective pub.
"""


def get_weather_beer_recommendation(weather_data: dict) -> dict:
    """
    Selects the best overall beer style and specific Dutch/Belgian beer based on
    how the weather actually feels (`feels_like`) and the terrace verdict.
    """
    feels_like = weather_data.get("feels_like", 14.0)
    verdict = weather_data.get("verdict", "HEATED_TERRACE_ONLY")
    rain_now = weather_data.get("rain_now", False)

    # Case 1: Raining or freezing -> Heavy, warming indoor beer
    if rain_now or verdict == "STAY_INSIDE":
        return {
            "beer_name": "La Trappe Quadrupel (or Dark Bokbier)",
            "style": "Belgian Quadrupel / Imperial Stout",
            "abv": "10.0%",
            "tagline": "Warm up inside while the weather does its worst.",
            "reason": (
                f"With a '{weather_data.get('condition', 'rough')}' forecast and a "
                f"feels-like temp of {feels_like}°C, skip the watery pilsner and "
                "order a rich, malty dark beer indoors."
            ),
        }

    # Case 2: Chilly but dry -> Heated terrace beer (Amber, Tripel, or Herfstbok)
    if verdict == "HEATED_TERRACE_ONLY" or feels_like < 16.0:
        return {
            "beer_name": "Texels Skuumkoppe / Tripel Karmeliet",
            "style": "Dark Wheat Beer / Belgian Tripel",
            "abv": "6.0% - 8.4%",
            "tagline": "Built for sitting under a glowing terrace heater.",
            "reason": (
                f"It feels like {feels_like}°C outside. A full-bodied wheat beer or "
                "spiced Belgian Tripel keeps you warm under the terrace lamps."
            ),
        }

    # Case 3: Warm & sunny (20°C+) -> Ultra-refreshing Witbier or Weizen
    if feels_like >= 20.0:
        return {
            "beer_name": "Brouwerij 't IJ IJwit",
            "style": "Crisp Amsterdam Witbier",
            "abv": "6.5%",
            "tagline": "Ice-cold citrus refreshment for peak terrace weather.",
            "reason": (
                f"At a warm {feels_like}°C, citrus and coriander notes in a chilled "
                "Witbier keep things refreshing in the sun."
            ),
        }

    # Case 4: Mild terrace weather (16°C - 20°C) -> Fresh Blond or Session IPA
    return {
        "beer_name": "Pronck Leidsch Blond",
        "style": "Local Fresh Blonde Ale",
        "abv": "6.4%",
        "tagline": "Crisp, local Leiden blonde for a dry terrace session.",
        "reason": (
            f"Feels like {feels_like}°C with dry skies for the next 3 hours—ideal "
            "for an easy-drinking local Leiden blonde."
        ),
    }


def _pick_pub_specific_beer(pub: dict, verdict: str) -> str:
    """
    Assigns a specific beer recommendation tailored to both the individual pub's
    specialty and the current weather verdict (fulfilling the proposal requirement
    to provide 'a beer recommendation for the respective pub').
    """
    specialty = pub.get("specialty", "").lower()

    if verdict == "STAY_INSIDE":
        if "belgian" in specialty or "abbey" in specialty:
            return "Rochefort 10 or St. Bernardus Abt 12"
        if "ipa" in specialty or "whisky" in specialty:
            return "Barrel-Aged Imperial Stout"
        if "brewery" in specialty or "craft" in specialty:
            return "House Smoked Porter / Winter Bock"
        return "Hertog Jan Grand Prestige"

    if verdict == "HEATED_TERRACE_ONLY":
        if "belgian" in specialty or "abbey" in specialty:
            return "Tripel Karmeliet or Westmalle Dubbel"
        if "ipa" in specialty or "whisky" in specialty:
            return "Hazy New England IPA (NEIPA)"
        if "brewery" in specialty or "craft" in specialty:
            return "Stael Amber Ale / Herfstbok"
        return "Texels Skuumkoppe on Draft"

    # GREAT_TERRACE weather
    if "belgian" in specialty or "abbey" in specialty:
        return "Chouffe Soleil or Vedett Extra White"
    if "ipa" in specialty or "whisky" in specialty:
        return "Tropical Session IPA"
    if "brewery" in specialty or "craft" in specialty:
        return "Fresh Unfiltered Leiden Weizen"
    return "Ice-Cold Draft Pilsner or IJwit"


def recommend_pubs_for_weather(pubs: list[dict], weather_data: dict) -> list[dict]:
    """
    Evaluates each pub against the current weather verdict, assigns a drunk-proof
    suitability badge, pairs a pub-specific beer, and sorts the best matches to the top.
    """
    verdict = weather_data.get("verdict", "HEATED_TERRACE_ONLY")
    ranked_pubs = []

    for pub in pubs:
        pub_copy = dict(pub)
        has_terrace = pub_copy.get("has_terrace", False)
        has_heating = pub_copy.get("has_heating", False)

        # Score and badge each pub based on the current weather verdict
        if verdict == "GREAT_TERRACE":
            if has_terrace:
                suitability_score = 3
                match_badge = "TOP PICK: OPEN TERRACE"
                match_color = "success"  # Green badge in UI
            else:
                suitability_score = 1
                match_badge = "INDOOR ONLY (NO TERRACE)"
                match_color = "secondary"

        elif verdict == "HEATED_TERRACE_ONLY":
            if has_terrace and has_heating:
                suitability_score = 3
                match_badge = "PERFECT: HEATED TERRACE 🔥"
                match_color = "warning"  # Amber/Orange badge in UI
            elif has_terrace and not has_heating:
                suitability_score = 2
                match_badge = "CHILLY: UNHEATED TERRACE ❄️"
                match_color = "info"
            else:
                suitability_score = 1
                match_badge = "INDOOR SEATING ONLY 🏠"
                match_color = "secondary"

        else:  # STAY_INSIDE
            suitability_score = 3
            match_badge = "SAFE & COZY INDOORS 🍺"
            match_color = "primary"

        pub_copy["suitability_score"] = suitability_score
        pub_copy["match_badge"] = match_badge
        pub_copy["match_color"] = match_color
        pub_copy["recommended_beer"] = _pick_pub_specific_beer(pub_copy, verdict)

        ranked_pubs.append(pub_copy)

    # Sort primarily by highest suitability score, and secondarily by shortest walking distance
    ranked_pubs.sort(key=lambda x: (-x["suitability_score"], x["distance_m"]))
    return ranked_pubs


# Self-test block: Run `python3 services/recommender.py` in terminal to verify!
if __name__ == "__main__":
    import os
    import sys

    # Ensure root project directory is on sys.path when running this file directly
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

    from services.map_api import get_nearby_pubs
    from services.weather_api import get_weather_analysis

    print("Running Full Service Pipeline Test (Weather -> Map -> Recommender)...\n")
    weather = get_weather_analysis()
    beer = get_weather_beer_recommendation(weather)
    raw_pubs = get_nearby_pubs()
    ranked = recommend_pubs_for_weather(raw_pubs, weather)

    print(f"WEATHER VERDICT : {weather['headline']} ({weather['feels_like']}°C feels like)")
    print(f"HERO BEER PICK  : {beer['beer_name']} ({beer['style']})")
    print(f"WHY             : {beer['reason']}\n")
    print("TOP 5 RECOMMENDED PUBS IN LEIDEN RIGHT NOW:")
    for idx, p in enumerate(ranked[:5], start=1):
        print(
            f"  {idx}. {p['name']} ({p['distance_m']}m) -> [{p['match_badge']}]\n"
            f"     Order here: {p['recommended_beer']}"
        )