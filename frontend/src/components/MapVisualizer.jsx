import React, { useEffect, useRef, useState } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { reverseGeocode, searchLocation } from "../services/api";

const MAP_TILES = {
  google_streets: {
    url: "https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}",
    attribution: "&copy; Google Maps",
    label: "Google Streets"
  },
  google_hybrid: {
    url: "https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}",
    attribution: "&copy; Google Maps",
    label: "Google Satellite/Hybrid"
  },
  google_terrain: {
    url: "https://mt1.google.com/vt/lyrs=p&x={x}&y={y}&z={z}",
    attribution: "&copy; Google Maps",
    label: "Google Terrain"
  },
  osm: {
    url: "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    label: "OpenStreetMap"
  }
};

export default function MapVisualizer({
  networkData,
  activeRoute,
  origin,
  destination,
  pickingMode,
  onSelectPoint,
  onCancelPickingMode
}) {
  const mapRef = useRef(null);
  const leafletMap = useRef(null);
  const tileLayerRef = useRef(null);
  const networkLayerRef = useRef(null);
  const routeLayerRef = useRef(null);
  const markersLayerRef = useRef(null);

  const [mapType, setMapType] = useState("google_streets");
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState([]);
  const [isSearching, setIsSearching] = useState(false);

  // Initialize Leaflet Map
  useEffect(() => {
    if (!leafletMap.current && mapRef.current) {
      const map = L.map(mapRef.current, { zoomControl: false }).setView([10.015, 76.32], 12);
      L.control.zoom({ position: "topright" }).addTo(map);

      tileLayerRef.current = L.tileLayer(MAP_TILES.google_streets.url, {
        attribution: MAP_TILES.google_streets.attribution,
        maxZoom: 20
      }).addTo(map);

      networkLayerRef.current = L.layerGroup().addTo(map);
      routeLayerRef.current = L.layerGroup().addTo(map);
      markersLayerRef.current = L.layerGroup().addTo(map);

      leafletMap.current = map;
    }
  }, []);

  // Handle Map Tile Type Switch
  useEffect(() => {
    if (!leafletMap.current || !tileLayerRef.current) return;
    const tileConfig = MAP_TILES[mapType] || MAP_TILES.google_streets;
    leafletMap.current.removeLayer(tileLayerRef.current);
    tileLayerRef.current = L.tileLayer(tileConfig.url, {
      attribution: tileConfig.attribution,
      maxZoom: 20
    }).addTo(leafletMap.current);
  }, [mapType]);

  // Handle ESC key to cancel picking mode
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === "Escape" && pickingMode) {
        onCancelPickingMode?.();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [pickingMode, onCancelPickingMode]);

  // Map Click Listener (Arbitrary Point Selection or Picking Mode)
  useEffect(() => {
    const map = leafletMap.current;
    if (!map) return;

    const handleMapClick = async (e) => {
      const { lat, lng } = e.latlng;

      if (pickingMode === "origin" || pickingMode === "destination") {
        const placeName = await reverseGeocode(lat, lng);
        onSelectPoint(pickingMode, {
          id: `POINT_${lat.toFixed(4)}_${lng.toFixed(4)}`,
          name: placeName,
          lat,
          lon: lng
        });
      } else {
        // General map click popup allowing set start / set end
        const tempPopup = L.popup()
          .setLatLng([lat, lng])
          .setContent(`
            <div style="font-family:sans-serif;padding:4px;text-align:center;min-width:180px;">
              <div style="font-weight:700;font-size:13px;color:#0f172a;margin-bottom:2px;">📍 Picked Map Point</div>
              <div style="font-size:11px;color:#64748b;margin-bottom:8px;font-family:monospace;">${lat.toFixed(4)}, ${lng.toFixed(4)}</div>
              <div style="display:flex;gap:6px;justify-content:center;">
                <button id="pop-click-start" style="background:#059669;color:white;border:none;padding:5px 10px;border-radius:6px;font-size:11px;font-weight:600;cursor:pointer;">
                  🚀 Set Start
                </button>
                <button id="pop-click-dest" style="background:#dc2626;color:white;border:none;padding:5px 10px;border-radius:6px;font-size:11px;font-weight:600;cursor:pointer;">
                  🏁 Set End
                </button>
              </div>
            </div>
          `)
          .openOn(map);

        setTimeout(() => {
          document.getElementById("pop-click-start")?.addEventListener("click", async () => {
            map.closePopup();
            const placeName = await reverseGeocode(lat, lng);
            onSelectPoint("origin", { id: `POINT_${lat.toFixed(4)}_${lng.toFixed(4)}`, name: placeName, lat, lon: lng });
          });
          document.getElementById("pop-click-dest")?.addEventListener("click", async () => {
            map.closePopup();
            const placeName = await reverseGeocode(lat, lng);
            onSelectPoint("destination", { id: `POINT_${lat.toFixed(4)}_${lng.toFixed(4)}`, name: placeName, lat, lon: lng });
          });
        }, 100);
      }
    };

    map.on("click", handleMapClick);
    return () => {
      map.off("click", handleMapClick);
    };
  }, [pickingMode, onSelectPoint]);

  // Update Network Stops Layer
  useEffect(() => {
    if (!leafletMap.current || !networkData?.stops || !networkLayerRef.current) return;
    networkLayerRef.current.clearLayers();

    networkData.stops.forEach((stop) => {
      let color = "#3b82f6"; // metro blue
      let iconSymbol = "🚆";
      if (stop.mode === "water_metro") {
        color = "#0d9488"; // teal
        iconSymbol = "🚤";
      } else if (stop.mode === "bus") {
        color = "#f97316"; // orange
        iconSymbol = "🚌";
      }

      const iconHtml = `
        <div style="background:${color};color:white;border-radius:50%;border:2px solid white;width:24px;height:24px;display:flex;align-items:center;justify-content:center;box-shadow:0 2px 6px rgba(0,0,0,0.3);font-size:11px;cursor:pointer;" title="${stop.name}">
          ${iconSymbol}
        </div>
      `;
      const stopIcon = L.divIcon({ className: "", html: iconHtml, iconSize: [24, 24], iconAnchor: [12, 12] });

      const marker = L.marker([stop.lat, stop.lon], { icon: stopIcon }).addTo(networkLayerRef.current);

      marker.bindPopup(`
        <div style="font-family:sans-serif;padding:4px;text-align:center;min-width:180px;">
          <div style="font-weight:700;font-size:13px;color:#0f172a;margin-bottom:2px;">${stop.name}</div>
          <div style="font-size:10px;font-weight:700;color:${color};text-transform:uppercase;margin-bottom:8px;">
            ${stop.agency} • ${stop.mode.replace("_", " ")}
          </div>
          <div style="display:flex;gap:6px;justify-content:center;">
            <button id="btn-stop-start-${stop.id}" style="background:#059669;color:white;border:none;padding:5px 10px;border-radius:6px;font-size:11px;font-weight:600;cursor:pointer;">
              🚀 Set Start
            </button>
            <button id="btn-stop-dest-${stop.id}" style="background:#dc2626;color:white;border:none;padding:5px 10px;border-radius:6px;font-size:11px;font-weight:600;cursor:pointer;">
              🏁 Set End
            </button>
          </div>
        </div>
      `);

      marker.on("popupopen", () => {
        document.getElementById(`btn-stop-start-${stop.id}`)?.addEventListener("click", () => {
          leafletMap.current.closePopup();
          onSelectPoint("origin", stop);
        });
        document.getElementById(`btn-stop-dest-${stop.id}`)?.addEventListener("click", () => {
          leafletMap.current.closePopup();
          onSelectPoint("destination", stop);
        });
      });
    });
  }, [networkData, onSelectPoint]);

  // Update Origin & Destination Custom Pin Markers
  useEffect(() => {
    if (!leafletMap.current || !markersLayerRef.current) return;
    markersLayerRef.current.clearLayers();

    // Origin Marker
    if (origin?.lat && origin?.lon) {
      const startHtml = `
        <div style="position:relative;display:flex;align-items:center;justify-content:center;">
          <div style="position:absolute;width:44px;height:44px;border-radius:50%;background:rgba(5,150,105,0.3);animation:ping 1.5s cubic-bezier(0,0,0.2,1) infinite;"></div>
          <div style="background:#059669;color:white;border-radius:50%;border:2px solid white;width:36px;height:36px;display:flex;align-items:center;justify-content:center;box-shadow:0 10px 15px -3px rgba(0,0,0,0.4);font-weight:bold;font-size:16px;z-index:2;cursor:grab;">
            🚀
          </div>
        </div>
      `;
      const startIcon = L.divIcon({ className: "", html: startHtml, iconSize: [36, 36], iconAnchor: [18, 18] });
      const origMarker = L.marker([origin.lat, origin.lon], { icon: startIcon, draggable: true }).addTo(
        markersLayerRef.current
      );
      origMarker.bindPopup(`<b>Start Point</b><br/>${origin.name}`);

      origMarker.on("dragend", async (ev) => {
        const newLat = ev.target.getLatLng().lat;
        const newLng = ev.target.getLatLng().lng;
        const newName = await reverseGeocode(newLat, newLng);
        onSelectPoint("origin", { id: `POINT_${newLat.toFixed(4)}_${newLng.toFixed(4)}`, name: newName, lat: newLat, lon: newLng });
      });
    }

    // Destination Marker
    if (destination?.lat && destination?.lon) {
      const destHtml = `
        <div style="position:relative;display:flex;align-items:center;justify-content:center;">
          <div style="position:absolute;width:44px;height:44px;border-radius:50%;background:rgba(220,38,38,0.3);animation:ping 1.5s cubic-bezier(0,0,0.2,1) infinite;"></div>
          <div style="background:#dc2626;color:white;border-radius:50%;border:2px solid white;width:36px;height:36px;display:flex;align-items:center;justify-content:center;box-shadow:0 10px 15px -3px rgba(0,0,0,0.4);font-weight:bold;font-size:16px;z-index:2;cursor:grab;">
            🏁
          </div>
        </div>
      `;
      const destIcon = L.divIcon({ className: "", html: destHtml, iconSize: [36, 36], iconAnchor: [18, 18] });
      const destMarker = L.marker([destination.lat, destination.lon], { icon: destIcon, draggable: true }).addTo(
        markersLayerRef.current
      );
      destMarker.bindPopup(`<b>Destination Point</b><br/>${destination.name}`);

      destMarker.on("dragend", async (ev) => {
        const newLat = ev.target.getLatLng().lat;
        const newLng = ev.target.getLatLng().lng;
        const newName = await reverseGeocode(newLat, newLng);
        onSelectPoint("destination", { id: `POINT_${newLat.toFixed(4)}_${newLng.toFixed(4)}`, name: newName, lat: newLat, lon: newLng });
      });
    }
  }, [origin, destination, onSelectPoint]);

  // Update Route Polyline
  useEffect(() => {
    if (!leafletMap.current || !routeLayerRef.current) return;
    routeLayerRef.current.clearLayers();

    if (activeRoute?.route_polyline && activeRoute.route_polyline.length > 0) {
      const poly = L.polyline(activeRoute.route_polyline, {
        color: "#2563eb",
        weight: 6,
        opacity: 0.9,
        lineCap: "round",
        lineJoin: "round"
      }).addTo(routeLayerRef.current);

      leafletMap.current.fitBounds(poly.getBounds(), { padding: [60, 60] });
    }
  }, [activeRoute]);

  // Handle Location Search Submission
  const handleSearchSubmit = async (e) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    setIsSearching(true);
    const results = await searchLocation(searchQuery.trim());
    setIsSearching(false);
    setSearchResults(results);
    if (results.length > 0 && leafletMap.current) {
      const first = results[0];
      leafletMap.current.flyTo([first.lat, first.lon], 15);
    }
  };

  const handlePickSearchResult = (item, type) => {
    if (leafletMap.current) {
      leafletMap.current.flyTo([item.lat, item.lon], 15);
    }
    onSelectPoint(type, {
      id: `POINT_${item.lat.toFixed(4)}_${item.lon.toFixed(4)}`,
      name: item.name,
      lat: item.lat,
      lon: item.lon
    });
    setSearchResults([]);
    setSearchQuery("");
  };

  return (
    <div className={`w-full h-full relative ${pickingMode ? "cursor-crosshair" : ""}`}>
      {/* Map Container */}
      <div ref={mapRef} className="w-full h-full z-0" />

      {/* Map Type Switcher Floating Control */}
      <div className="absolute top-4 right-14 z-10 bg-white/90 backdrop-blur-md border border-slate-200 shadow-md rounded-xl p-1 flex gap-1 text-xs">
        {Object.entries(MAP_TILES).map(([key, cfg]) => (
          <button
            key={key}
            onClick={() => setMapType(key)}
            className={`px-2.5 py-1 rounded-lg font-medium transition ${
              mapType === key ? "bg-slate-900 text-white shadow" : "text-slate-600 hover:bg-slate-100"
            }`}
          >
            {cfg.label}
          </button>
        ))}
      </div>

      {/* Map Search Bar Floating Widget */}
      <div className="absolute top-4 left-4 z-10 w-80">
        <form onSubmit={handleSearchSubmit} className="relative shadow-md rounded-xl overflow-hidden bg-white/90 backdrop-blur-md border border-slate-200">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="🔍 Search any landmark or location..."
            className="w-full text-xs py-2.5 pl-3 pr-16 focus:outline-none bg-transparent"
          />
          <button
            type="submit"
            disabled={isSearching}
            className="absolute right-1 top-1 bottom-1 px-3 bg-blue-600 hover:bg-blue-700 text-white text-xs font-medium rounded-lg transition"
          >
            {isSearching ? "..." : "Search"}
          </button>
        </form>

        {/* Search Results Dropdown */}
        {searchResults.length > 0 && (
          <div className="mt-1 bg-white/95 backdrop-blur-md border border-slate-200 shadow-lg rounded-xl overflow-hidden text-xs max-h-56 overflow-y-auto divide-y divide-slate-100">
            {searchResults.map((r, i) => (
              <div key={i} className="p-2 hover:bg-slate-50 flex items-center justify-between">
                <span className="font-medium text-slate-800 truncate pr-2" title={r.name}>{r.name}</span>
                <div className="flex gap-1 flex-shrink-0">
                  <button
                    onClick={() => handlePickSearchResult(r, "origin")}
                    className="px-2 py-0.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded text-[10px] font-semibold"
                  >
                    Start
                  </button>
                  <button
                    onClick={() => handlePickSearchResult(r, "destination")}
                    className="px-2 py-0.5 bg-red-600 hover:bg-red-700 text-white rounded text-[10px] font-semibold"
                  >
                    End
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Picking Mode Banner Prompt */}
      {pickingMode && (
        <div className="absolute top-16 left-1/2 -translate-x-1/2 z-20 bg-slate-900/90 backdrop-blur-md text-white px-5 py-2.5 rounded-full shadow-2xl flex items-center gap-3 border border-slate-700 animate-bounce">
          <span className="w-3 h-3 rounded-full bg-blue-400 animate-ping" />
          <span className="text-xs font-semibold tracking-wide">
            {pickingMode === "origin"
              ? "📍 Click anywhere on Google Map to set STARTING POINT"
              : "🏁 Click anywhere on Google Map to set DESTINATION POINT"}
          </span>
          <button
            onClick={onCancelPickingMode}
            className="px-2 py-0.5 bg-slate-700 hover:bg-slate-600 rounded text-[11px] font-medium"
          >
            Cancel (Esc)
          </button>
        </div>
      )}
    </div>
  );
}
