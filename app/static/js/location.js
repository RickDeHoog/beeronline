


let userLocation = null;

function getUserLocation() {
    return userLocation;
};

function setLocation(location) {
    userLocation = location;

    const locationName = document.getElementById("location-name");
    
    if (locationName) {
        locationName.textContent = location.name;
    }

    document.dispatchEvent(
        new CustomEvent("locationReady", {
            detail: {
                location: userLocation
            }
        })
    );
}

function toggleLocationDropdown(){
    const dropdown = document.getElementById("location-dropdown");
    dropdown.classList.toggle("hidden");
}

async function searchLocation(){
    const locinput = document.getElementById("location-input");
    const locerror = document.getElementById("location-error");
    const query = locinput.value.trim();

    if(!query){
        locerror.textContent = "Please enter a location."
        return
    }

    locerror.textContent = "Searching..."

    try{
        const params = new URLSearchParams({q: query,format: "json", limit: 1});

        const url = "https://nominatim.openstreetmap.org/search?" + params

        const response = await fetch(url);

        if(!response.ok){
            throw new Error("Location search fail.");
        }

        const results = await response.json()

        if(results.length === 0){
            locerror.textContent = "Location not found."
            return
        }

        const result = results[0]

        setLocation({
            lat: result.lat,
            lon: result.lon,
            name: result.name || query
        })

        document.getElementById("location-dropdown").classList.add("hidden")

        locerror.textContent = "";
        locinput.value = "";
    } catch (err) {
        console.error(err)
        locerror.textContent = "Failed to find location."
    }
}

async function useMyLocation(){
    const locerror = document.getElementById("location-error")
    locerror.textContent = "Getting your location..."

    try {
        const location = await requestLocation()

        setLocation(location)

        document.getElementById("location-dropdown").classList.add("hidden")
    } catch(err){
        error.textContent = "Could not get your location."
    }
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
