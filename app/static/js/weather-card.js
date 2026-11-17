document.addEventListener("weatherDataLoaded", function (event) {
    const data = event.detail;
    const weatherCard = document.getElementById("weather-card")
    const verdictColorClass = data.rain_now
        ? "weather-rain-now"
        : data.rain_coming_later
            ? "weather-rain-later"
            : data.verdict === "STAY_INSIDE"
                ? "weather-extreme"
                : data.verdict === "HEATED_TERRACE_ONLY"
                    ? "weather-cold"
                    : "weather-sunny";

    weatherCard.classList.remove(
        "weather-rain-now",
        "weather-rain-later",
        "weather-extreme",
        "weather-cold",
        "weather-sunny"
    );
    weatherCard.classList.add(verdictColorClass);

    const recommendation = data.beer_recommendation;
    if (!recommendation) {
        return;
    }

    document.getElementById("beer-name").textContent = recommendation.beer_name;
    document.getElementById("beer-style").textContent = recommendation.style;
    document.getElementById("beer-tagline").textContent = recommendation.tagline;
    document.getElementById("beer-reason").textContent = recommendation.reason;
    document.getElementById("beer-abv").textContent = `ABV ${recommendation.abv}`;
    document.getElementById("beer-recommendation").hidden = false;
});
