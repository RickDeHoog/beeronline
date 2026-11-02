
"use strict";

document.addEventListener("locationReady", async function (event) {
    const location = event.detail.location;

    try {
        const params = new URLSearchParams({
            lat: location.lat,
            lon: location.lon,
            visit_hours: 3
        });

        const response = await fetch(`/api/weather?${params.toString()}`);

        const data = await response.json();

        if (!response.ok) {
            console.error("Weather API error:", data);
            return;
        }

        document.getElementById("weather-headline").textContent = data.headline
        document.getElementById("weather-condition").textContent = data.condition
        document.getElementById("weather-feels-like").textContent = `${data.feels_like}°C`
        document.getElementById("weather-advice").textContent = data.advice
        document.getElementById("weather-temp").textContent = `${data.temp}°C`
        document.getElementById("weather-wind").textContent = `${data.wind_kmh} km/h`
        document.getElementById("weather-rain-chance").textContent = `${data.max_rain_prob_visit}%`

        document.dispatchEvent(new CustomEvent("weatherDataLoaded", { detail: data }));

    } catch (error) {
        console.error("Failed to fetch weather:", error);
    }
});
