// BeerOnline / Group 20 — Leiden pub and bar discovery
// Source: OpenStreetMap via Overpass Turbo (https://overpass-turbo.eu/)
// Export snapshot: 2026-10-29T13:43:11Z
// Centre: 52.1601, 4.4970 (Leiden); radius: 3000 metres
// Includes OSM amenity=pub and amenity=bar, not amenity=cafe.
// Query results provide possible venues, NOT verified beer menus or heating.
// Attribution: © OpenStreetMap contributors (ODbL)
// https://www.openstreetmap.org/copyright

[out:json][timeout:20];

nwr["amenity"~"^(pub|bar)$"]
   (around:3000,52.1601,4.4970);

out center;
