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


const userMarker = L.marker([
    initialLocation.lat,
    initialLocation.lon
]).addTo(map);


const pubLayer = L.layerGroup().addTo(map);
const pubIcon = L.divIcon({
  html: '<span style="font-size: 28px;">🍺</span>',
  className: 'beer-marker',
  iconSize: [32, 32],
  iconAnchor: [16, 28]
});



async function loadNearbyPubs(location){
    const params = new URLSearchParams({
        lat: location.lat,
        lon: location.lon,
        radius_m: 1500,
        limit: 12
    });

    try {
        const response = await fetch(`/api/pubs?${params}`);

        if(!response.ok){
            throw new Error(`API: ${response.status}`);
        }

        const data = await response.json();

        data.pubs.forEach((pub) => {
            const pubMarker = L.marker([
                pub.lat,
                pub.lon
            ], {
                icon: pubIcon
            });

            pubMarker.addTo(pubLayer)
        })
    } catch (error){
        console.error("Could not load pubs:", error);
    }
}

function updateMap(location) {
    const coords = [
        location.lat,
        location.lon
    ];

    map.setView(coords, 13);

    userMarker
        .setLatLng(coords)
        .bindPopup(location.name);

    loadNearbyPubs(location);
}


document.addEventListener("locationReady", (event) => {
    const { location } = event.detail;

    updateMap(location);
});

const existingLocation = window.getUserLocation?.();

if (existingLocation) {
    updateMap(existingLocation);
}