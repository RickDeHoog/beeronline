"use strict";

const initialLocation = window.DEFAULT_LOCATION;

const map = L.map("map").setView(
    [
        initialLocation.lat,
        initialLocation.lon
    ],
    13
);

L.tileLayer(
    "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
).addTo(map);


const marker = L.marker([
    initialLocation.lat,
    initialLocation.lon
]).addTo(map);


function updateMap(location) {
    const coords = [
        location.lat,
        location.lon
    ];

    map.setView(coords, 13);

    marker
        .setLatLng(coords)
        .bindPopup(location.name);
}


document.addEventListener("locationReady", (event) => {
    const { location } = event.detail;

    updateMap(location);
});

const existingLocation = window.getUserLocation?.();

if (existingLocation) {
    updateMap(existingLocation);
}