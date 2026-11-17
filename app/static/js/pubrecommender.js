function displayPubs(pubs){
    const publist = document.getElementById("pub-list");

    publist.innerHTML = "";

    if(pubs.length === 0){
        publist.innerHTML = "<p>No pubs found.</p>"
        return;
    }

    pubs.forEach((pub) => {
        const card = document.createElement("div");

        card.className="pub-card"

        const terrace = pub.has_terrace == null
            ? "Unknown"
            : pub.has_terrace ? "Yes" : "No";
        const heating = pub.has_heating == null
            ? "Unknown"
            : pub.has_heating ? "Yes" : "No";

        card.innerHTML =  `
            <h3>${pub.name}</h3>
            ${pub.match_badge ? `<p class="pub-match ${pub.match_color || ""}">${pub.match_badge}</p>` : ""}
            <p>${pub.address || "Address unknown"}</p>
            <p>Distance: ${pub.distance_m}m</p>
            <p>Specialty: ${pub.specialty || "Not specified"}</p>
            <p>Menu: ${(pub.beer_menu || []).join(", ") || "Unknown"}</p>
            ${pub.recommended_beer ? `<p><strong>Weather pick:</strong> ${pub.recommended_beer}</p>` : ""}
            <p>Terrace: ${terrace}</p>
            <p>Terrace heating: ${heating}</p>
        `;

        card.addEventListener("click", () =>{
            const coords = [pub.lat, pub.lon];

            map.setView(coords, 20);

        });

        publist.appendChild(card)
    })

}