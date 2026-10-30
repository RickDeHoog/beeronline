
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
        document.getElementById("weather-feels-like").textContent = data.feels_like
        document.getElementById("weather-advice").textContent = data.advice

    } catch (error) {
        console.error("Failed to fetch weather:", error);
    }
});
