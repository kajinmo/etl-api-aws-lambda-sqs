// Geocoding Dictionary para lugares comuns no payload
// A fallback will generate slightly randomized coordinates for variations
const geoDictionary = {
    "India": [20.5937, 78.9629],
    "Egypt": [26.8206, 30.8025],
    "China": [35.8617, 104.1954],
    "Nanjing, China": [32.0603, 118.7969],
    "Edmonton, Alberta, Canada": [53.5461, -113.4938],
    "Santiago, Chile": [-33.4489, -70.6693],
    "Dublin, Ireland": [53.3498, -6.2603],
    "Slovakia": [48.6690, 19.6990],
    "Austria": [47.5162, 14.5501],
    "Brazil": [-14.2350, -51.9253]
};

function getCoordinates(locationStr) {
    if (!locationStr || locationStr === "Not Specified") return null;
    
    // Check direct match
    if (geoDictionary[locationStr]) {
        // Add tiny variance to prevent overlapping exact points
        const variance = () => (Math.random() - 0.5) * 0.1;
        return [
            geoDictionary[locationStr][0] + variance(),
            geoDictionary[locationStr][1] + variance()
        ];
    }
    
    // Simplistic random generation to simulate "world data" when missing from dict, for portfolio aesthetics
    // Only applied if location is NOT "Not Specified" but just isn't in our tiny dictionary
    return [
        (Math.random() * 120) - 60, // Lat
        (Math.random() * 360) - 180 // Lng
    ];
}

function timeAgo(dateStr) {
    const time = new Date(dateStr).getTime();
    const now = new Date().getTime();
    const diffInSeconds = Math.floor((now - time) / 1000);
    
    if (diffInSeconds < 60) return `${diffInSeconds}s ago`;
    const diffInMinutes = Math.floor(diffInSeconds / 60);
    if (diffInMinutes < 60) return `${diffInMinutes}m ago`;
    const diffInHours = Math.floor(diffInMinutes / 60);
    return `${diffInHours}h ago`;
}

// Map Initialization
const map = L.map('map', {
    center: [20, 0], // Center roughly around equator
    zoom: 2,
    zoomControl: false // keeping it clean
});

L.control.zoom({ position: 'bottomright' }).addTo(map);

// Using CartoDB Dark Matter for that sleek dark dashboard look
L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
    subdomains: 'abcd',
    maxZoom: 20
}).addTo(map);

// Custom Map Marker Icon
const greenIcon = new L.Icon({
    iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-green.png',
    shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
    iconSize: [25, 41],
    iconAnchor: [12, 41],
    popupAnchor: [1, -34],
    shadowSize: [41, 41]
});

async function loadData() {
    try {
        const response = await fetch('data.json');
        if (!response.ok) throw new Error('Data not found');
        const data = await response.json();
        
        const feedContainer = document.getElementById('activity-feed');
        feedContainer.innerHTML = '';
        
        let latestDate = new Date(0);

        data.forEach(event => {
            // Calculate latest update
            const eventDate = new Date(event.created_at);
            if (eventDate > latestDate) latestDate = eventDate;

            // 1. Build Feed Card
            const card = document.createElement('div');
            card.className = 'feed-card';
            card.innerHTML = `
                <div class="feed-header">
                    <span class="feed-type">${event.type.replace('Event', '')}</span>
                    <span>${timeAgo(event.created_at)}</span>
                </div>
                <div class="feed-repo">${event.repo.name}</div>
                <div class="feed-actor">
                    <img src="${event.actor.avatar_url || ''}" alt="avatar" onerror="this.style.display='none'">
                    ${event.actor.login}
                </div>
            `;
            feedContainer.appendChild(card);

            // 2. Add Map Marker
            const coords = getCoordinates(event.actor.location);
            if (coords) {
                const popupContent = `
                    <div style="font-family:'Inter',sans-serif;">
                        <strong style="color: #00ffcc;">${event.actor.login}</strong><br>
                        <em>${event.actor.location}</em><br>
                        ${event.repo.name}<br>
                        ${event.type}
                    </div>
                `;
                L.marker(coords, {icon: greenIcon})
                 .addTo(map)
                 .bindPopup(popupContent);
            }
        });

        // Update Latest Header
        document.getElementById('latest-update').innerText = `Latest Update: ${latestDate.toLocaleString()}`;

    } catch (error) {
        console.error("Error loading data:", error);
        document.getElementById('activity-feed').innerHTML = `<p style="color: red; padding: 1rem;">Failed to load data.json. Makes sure it exists in the same folder.</p>`;
        document.getElementById('latest-update').innerText = "Update Failed";
    }
}

// Initial Load
loadData();
