document.addEventListener("weatherDataLoaded", function (event) {
    const data = event.detail;
    const weatherCard = document.querySelector(".left-top");
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
});
