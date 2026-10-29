
"use strict";

let userLocation = null;

window.getUserLocation = function () {
    return userLocation;
};

function setLocation(location) {
    userLocation = location;

    document.dispatchEvent(
        new CustomEvent("locationReady", {
            detail: {
                location: userLocation
            }
        })
    );
}

function useFallback() {
    setLocation(window.DEFAULT_LOCATION);
}


function requestLocation() {
    if (!navigator.geolocation) {
        console.warn("Geolocation is not supported.");
        useFallback();
        return;
    }

    navigator.geolocation.getCurrentPosition(
        function (position) {
            setLocation(
                {
                    lat: position.coords.latitude,
                    lon: position.coords.longitude,
                    name: "My location"
                }
            );
        },

        function (error) {
            console.warn("Location error:", error.message);
            useFallback();
        },

        {
            timeout: 10000,
            maximumAge: 0
        }
    );
}

requestLocation();
