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

def _pick_pub_specific_beer(pub: dict, verdict: str) -> str | None:
    """
    Recommend a beer from this pub's recorded menu.
    Return None if no usable menu is available.
    """

    # Get the actual beer menu for this pub.
    menu = pub.get("beer_menu", [])

    # Reject missing or incorrectly formatted menus.
    if not isinstance(menu, list):
        return None

    # Keep only non-empty beer names.
    available_beers = [
        beer for beer in menu
        if isinstance(beer, str) and beer.strip()
    ]

    if not available_beers:
        return None

    # Preferred beer styles for each weather situation.
    preferred_styles = {
        "STAY_INSIDE": (
            "stout", "porter", "quadrupel",
            "dubbel", "bock", "bok", "tripel"
        ),
        "HEATED_TERRACE_ONLY": (
            "tripel", "dubbel", "amber",
            "bock", "bok", "blond"
        ),
        "GREAT_TERRACE": (
            "witbier", "weizen", "radler",
            "pils", "ipa", "blond", "draft"
        ),
    }

    # Find the first beer matching a preferred style.
    for style in preferred_styles.get(verdict, ()):
        for beer in available_beers:
            if style in beer.lower():
                return beer

    # If no style matches, use the first actual menu entry.
    return available_beers[0]



def recommend_pubs_for_weather(pubs: list[dict], weather_data: dict) -> list[dict]:
    """
    Rank pubs based on how suitable their seating is for the weather.

    For each pub:
    1. Calculate a suitability score.
    2. Give it a readable badge.
    3. Recommend a beer from its recorded menu.
    4. Sort the results by suitability, then distance.
    """

    # Get the weather verdict. Use heated terrace as the default.
    verdict = weather_data.get("verdict", "HEATED_TERRACE_ONLY")

    ranked_pubs = []

    # Examine each pub individually.
    for pub in pubs:

        # Copy the pub so we don't change the original database record.
        pub_copy = dict(pub)

        has_terrace = pub_copy.get("has_terrace", False)
        has_heating = pub_copy.get("has_heating", False)

        # CASE 1: Warm and dry weather.
        # Pubs with terraces are preferred.
        if verdict == "GREAT_TERRACE":

            if has_terrace:
                suitability_score = 3
                match_badge = "TOP PICK: OPEN TERRACE"
                match_color = "success"

            else:
                suitability_score = 1
                match_badge = "INDOOR ONLY (NO TERRACE)"
                match_color = "secondary"

        # CASE 2: Chilly weather.
        # Heated terraces are preferred, followed by indoor-only pubs.
        elif verdict == "HEATED_TERRACE_ONLY":

            if has_terrace and has_heating:
                suitability_score = 3
                match_badge = "PERFECT: HEATED TERRACE 🔥"
                match_color = "warning"

            elif not has_terrace:
                suitability_score = 2
                match_badge = "GOOD ALTERNATIVE: INDOOR SEATING 🏠"
                match_color = "secondary"

            else:
                suitability_score = 1
                match_badge = "NOT RECOMMENDED: UNHEATED TERRACE ❄️"
                match_color = "secondary"

        # CASE 3: Rain, strong wind or very cold conditions.
        # Indoor seating is preferred.
        else:  # STAY_INSIDE

            suitability_score = 3
            match_badge = "STAY INSIDE: COZY PUB 🍺"
            match_color = "primary"

        # Save the results in the copied pub dictionary.
        pub_copy["suitability_score"] = suitability_score
        pub_copy["match_badge"] = match_badge
        pub_copy["match_color"] = match_color

        # Choose a beer from this pub's actual JSON beer menu.
        pub_copy["recommended_beer"] = _pick_pub_specific_beer(
            pub_copy, verdict
        )

        ranked_pubs.append(pub_copy)

    # Sort highest suitability first, then shortest distance.
    # The minus sign puts score 3 before score 2 and score 1.
    ranked_pubs.sort(
        key=lambda pub: (-pub["suitability_score"], pub["distance_m"])
    )

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