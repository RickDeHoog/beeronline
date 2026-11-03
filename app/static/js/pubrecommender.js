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

        card.innerHTML =  `
            <h3>${pub.name}</h3>
            <p>${pub.address || "Address unknown"}</p>
            <p>Distance: ${pub.distance_m}m</p>
            <p>Specialty: ${pub.specialty || "Not specified"}</p>
            <p>Menu: ${(pub.beer_menu || []).join(", ") || "Unknown"}</p>
            <p>Terrace: ${ pub.has_terrace ? "Yes" : "No"}</p>
            <p>Terrace heating: ${pub.has_heating ? "Yes" : "No"}</p>
        `;

        card.addEventListener("click", () =>{
            const coords = [pub.lat, pub.lon];

            map.setView(coords, 20);

        });

        publist.appendChild(card)
    })

}