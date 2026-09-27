const API_BASE = process.env.REACT_APP_API_URL || "http://127.0.0.1:8000";

export async function fetchNetworkGraph() {
  const res = await fetch(`${API_BASE}/api/transit/network-graph`);
  if (!res.ok) throw new Error("Failed to fetch network graph");
  return res.json();
}

export async function planRoute(origin, destination, preference = "fastest") {
  const payload = { preference };

  if (typeof origin === "object" && origin !== null) {
    if (origin.id && !origin.id.startsWith("POINT_")) {
      payload.origin_id = origin.id;
    } else {
      payload.origin_lat = origin.lat;
      payload.origin_lon = origin.lon;
      payload.origin_name = origin.name;
    }
  } else if (typeof origin === "string") {
    payload.origin_id = origin;
  }

  if (typeof destination === "object" && destination !== null) {
    if (destination.id && !destination.id.startsWith("POINT_")) {
      payload.destination_id = destination.id;
    } else {
      payload.dest_lat = destination.lat;
      payload.dest_lon = destination.lon;
      payload.dest_name = destination.name;
    }
  } else if (typeof destination === "string") {
    payload.destination_id = destination;
  }

  const res = await fetch(`${API_BASE}/api/routing/plan`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || "No route found between selected points");
  }
  return res.json();
}

export async function sendAIChat(message) {
  const res = await fetch(`${API_BASE}/api/ai/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message })
  });
  if (!res.ok) throw new Error("AI service error");
  return res.json();
}

export async function reverseGeocode(lat, lon) {
  try {
    const res = await fetch(
      `https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lon}&zoom=18&addressdetails=1`
    );
    if (res.ok) {
      const data = await res.json();
      const addr = data.address;
      const display = data.display_name;
      if (display) {
        const parts = display.split(",").map((s) => s.trim());
        const cleaned = parts.slice(0, 3).join(", ");
        return cleaned;
      }
    }
  } catch (err) {
    console.warn("Reverse geocode failed:", err);
  }
  return `Point (${lat.toFixed(4)}, ${lon.toFixed(4)})`;
}

export async function searchLocation(query) {
  try {
    const res = await fetch(
      `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(
        query + " Greater Kochi Kerala India"
      )}&limit=5`
    );
    if (res.ok) {
      const data = await res.json();
      return data.map((item) => ({
        name: item.display_name.split(",").slice(0, 3).join(", "),
        lat: parseFloat(item.lat),
        lon: parseFloat(item.lon)
      }));
    }
  } catch (err) {
    console.warn("Location search failed:", err);
  }
  return [];
}

