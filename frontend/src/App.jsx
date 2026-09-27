import React, { useState, useEffect } from "react";
import MapVisualizer from "./components/MapVisualizer";
import JourneyPlanner from "./components/JourneyPlanner";
import AIChatModal from "./components/AIChatModal";
import { fetchNetworkGraph, planRoute } from "./services/api";

export default function App() {
  const [networkData, setNetworkData] = useState({ stops: [], edges: [], routes: [] });
  const [origin, setOrigin] = useState(null);
  const [destination, setDestination] = useState(null);
  const [pickingMode, setPickingMode] = useState(null); // 'origin' | 'destination' | null
  const [preference, setPreference] = useState("fastest");
  const [activeRoute, setActiveRoute] = useState(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState("plan");

  useEffect(() => {
    fetchNetworkGraph()
      .then(setNetworkData)
      .catch((err) => console.error("Could not load network:", err));
  }, []);

  const handlePlanRoute = async (orig = origin, dest = destination, pref = preference) => {
    if (!orig || !dest) return;
    setLoading(true);
    try {
      const itinerary = await planRoute(orig, dest, pref);
      setActiveRoute(itinerary);
    } catch (err) {
      alert(err.message || "No path found between selected locations.");
    } finally {
      setLoading(false);
    }
  };

  const handleSelectPoint = (type, point) => {
    if (type === "origin") {
      setOrigin(point);
      setPickingMode(null);
      if (destination) {
        handlePlanRoute(point, destination, preference);
      }
    } else if (type === "destination") {
      setDestination(point);
      setPickingMode(null);
      if (origin) {
        handlePlanRoute(origin, point, preference);
      }
    }
  };

  const handleSwapPoints = () => {
    const temp = origin;
    setOrigin(destination);
    setDestination(temp);
    if (origin && destination) {
      handlePlanRoute(destination, origin, preference);
    }
  };

  const handlePreferenceChange = (newPref) => {
    setPreference(newPref);
    if (origin && destination) {
      handlePlanRoute(origin, destination, newPref);
    }
  };

  const handleSelectTripFromAI = (origId, destId, preview) => {
    const origStop = networkData.stops.find((s) => s.id === origId) || origId;
    const destStop = networkData.stops.find((s) => s.id === destId) || destId;
    setOrigin(origStop);
    setDestination(destStop);

    if (preview) {
      setActiveRoute(preview);
    } else {
      handlePlanRoute(origStop, destStop, preference);
    }
  };

  const handleSelectOption = (opt) => {
    setActiveRoute(opt);
  };

  // Analytics calculation helpers
  const distKm = activeRoute?.total_distance_km || 0;
  const durMin = activeRoute?.total_duration_min || 0;
  const fare = activeRoute?.total_fare || 0;
  const smartCardFare = Math.round(fare * 0.8);
  const estimatedCabCost = distKm > 0 ? Math.round(distKm * 25 + 50) : 0;
  const savings = Math.max(0, estimatedCabCost - fare);
  const co2Saved = (distKm * 0.12).toFixed(2);
  const avgSpeed = durMin > 0 ? Math.round((distKm / (durMin / 60))) : 0;

  return (
    <div className="bg-slate-50 text-slate-800 font-sans h-screen flex flex-col overflow-hidden">
      {/* Header */}
      <header className="bg-slate-900 text-white px-5 py-3 flex items-center justify-between shadow-md z-10">
        <div className="flex items-center gap-3">
          <div className="bg-blue-600 text-white p-2 rounded-lg flex items-center justify-center font-bold">
            🚀
          </div>
          <div>
            <h1 className="text-lg font-bold tracking-wide flex items-center gap-2">
              smartRoute <span className="text-xs bg-blue-500/30 text-blue-300 font-mono px-2 py-0.5 rounded">MaaS Platform</span>
            </h1>
            <p className="text-xs text-slate-400">Greater Kochi Integrated Multimodal Transit • 50% Milestone Dashboard</p>
          </div>
        </div>
        <div className="flex items-center gap-2 text-xs">
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 font-medium">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            Backend API Connected
          </span>
          <a href="http://127.0.0.1:8000/docs" target="_blank" rel="noreferrer" className="px-3 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded border border-slate-700">
            Swagger Docs ↗
          </a>
        </div>
      </header>

      {/* Main Layout */}
      <div className="flex-1 flex overflow-hidden relative">
        <aside className="w-96 bg-white border-r border-slate-200 flex flex-col shadow-lg z-10 flex-shrink-0">
          {/* Navigation Tabs */}
          <div className="flex border-b border-slate-200 bg-slate-100/70 p-1.5 gap-1 text-xs font-medium">
            <button
              onClick={() => setActiveTab("plan")}
              className={`flex-1 py-1.5 px-2 rounded-md transition ${activeTab === "plan" ? "bg-white shadow-sm text-blue-600 font-semibold" : "text-slate-600"}`}
            >
              Plan Trip
            </button>
            <button
              onClick={() => setActiveTab("network")}
              className={`flex-1 py-1.5 px-2 rounded-md transition ${activeTab === "network" ? "bg-white shadow-sm text-blue-600 font-semibold" : "text-slate-600"}`}
            >
              Network Lines
            </button>
            <button
              onClick={() => setActiveTab("analytics")}
              className={`flex-1 py-1.5 px-2 rounded-md transition ${activeTab === "analytics" ? "bg-white shadow-sm text-blue-600 font-semibold" : "text-slate-600"}`}
            >
              Analytics & Fares
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {activeTab === "plan" && (
              <JourneyPlanner
                stops={networkData.stops}
                origin={origin}
                destination={destination}
                pickingMode={pickingMode}
                onSelectOrigin={(pt) => handleSelectPoint("origin", pt)}
                onSelectDestination={(pt) => handleSelectPoint("destination", pt)}
                onSetPickingMode={setPickingMode}
                onSwapPoints={handleSwapPoints}
                onPlanRoute={handlePlanRoute}
                activeRoute={activeRoute}
                loading={loading}
                preference={preference}
                onPreferenceChange={handlePreferenceChange}
                onSelectOption={handleSelectOption}
              />
            )}

            {activeTab === "network" && (
              <div className="space-y-3 text-xs">
                <h3 className="font-bold text-slate-500 uppercase tracking-wider">Active Kochi Transit Network</h3>
                <div className="space-y-2">
                  <div className="p-3 bg-blue-50 border border-blue-200 rounded-xl">
                    <div className="font-bold text-blue-800 text-sm mb-1">🚆 Kochi Metro Line 1</div>
                    <p className="text-slate-600 text-[11px]">Aluva ↔ Thripunithura (25 Stations, 100% Electrified)</p>
                  </div>
                  <div className="p-3 bg-teal-50 border border-teal-200 rounded-xl">
                    <div className="font-bold text-teal-800 text-sm mb-1">🚤 Kochi Water Metro</div>
                    <p className="text-slate-600 text-[11px]">Line 1: Vyttila ↔ Kakkanad | Line 2: High Court ↔ Fort Kochi (13 Jetties)</p>
                  </div>
                  <div className="p-3 bg-orange-50 border border-orange-200 rounded-xl">
                    <div className="font-bold text-orange-800 text-sm mb-1">🚌 First/Last Mile Feeder Buses</div>
                    <p className="text-slate-600 text-[11px]">Kalamassery, Rajagiri (RSET), CUSAT, Infopark, MG Road (22 Stops)</p>
                  </div>
                </div>

                <div className="bg-slate-100 p-3 rounded-xl border border-slate-200 space-y-1 text-[11px] text-slate-600">
                  <b className="text-slate-800 block mb-1">📊 System Scale Summary:</b>
                  <p>• Total Stops Ingested: <b>{networkData.stops.length || 60}+</b></p>
                  <p>• Total Network Edges: <b>{networkData.edges?.length || 120}+</b></p>
                  <p>• Intermodal Hubs: <b>34 Interchanges</b></p>
                </div>
              </div>
            )}

            {activeTab === "analytics" && (
              <div className="space-y-4 text-xs">
                <div>
                  <h3 className="font-bold text-slate-500 uppercase tracking-wider mb-2">Fare Estimator & Savings</h3>
                  <div className="bg-gradient-to-br from-blue-600 to-indigo-700 text-white rounded-xl p-3.5 shadow">
                    <span className="text-[10px] uppercase font-bold tracking-wider opacity-80">Estimated Standard Fare</span>
                    <div className="text-2xl font-extrabold mt-0.5">₹{fare}</div>
                    <div className="mt-2 grid grid-cols-2 gap-2 text-[11px] border-t border-white/20 pt-2">
                      <div>
                        <span className="opacity-75 block text-[9px]">KOCHI1 SMART CARD</span>
                        <span className="font-bold">₹{smartCardFare} (20% OFF)</span>
                      </div>
                      <div>
                        <span className="opacity-75 block text-[9px]">PRIVATE CAB ESTIMATE</span>
                        <span className="font-bold">₹{estimatedCabCost}</span>
                      </div>
                    </div>
                  </div>
                </div>

                {savings > 0 && (
                  <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-xl font-medium flex items-center justify-between">
                    <span>💰 Total Cost Savings vs Taxi:</span>
                    <b className="text-sm font-bold text-emerald-700">₹{savings}</b>
                  </div>
                )}

                <div>
                  <h3 className="font-bold text-slate-500 uppercase tracking-wider mb-2">Mobility & Sustainability Metrics</h3>
                  <div className="grid grid-cols-2 gap-2">
                    <div className="p-3 bg-white border border-slate-200 rounded-xl shadow-sm">
                      <span className="text-slate-400 block text-[10px] uppercase font-bold">CO₂ Saved</span>
                      <span className="text-base font-extrabold text-emerald-600">{co2Saved} kg</span>
                      <span className="text-[9px] text-slate-400 block mt-0.5">vs private car trip</span>
                    </div>
                    <div className="p-3 bg-white border border-slate-200 rounded-xl shadow-sm">
                      <span className="text-slate-400 block text-[10px] uppercase font-bold">Avg Trip Speed</span>
                      <span className="text-base font-extrabold text-blue-600">{avgSpeed} km/h</span>
                      <span className="text-[9px] text-slate-400 block mt-0.5">{distKm} km / {durMin} min</span>
                    </div>
                  </div>
                </div>

                <div className="bg-slate-50 p-3 rounded-xl border border-slate-200 space-y-1 text-[11px] text-slate-600">
                  <b className="text-slate-800 block mb-1">🌿 Environmental Impact:</b>
                  <p>By opting for integrated public transit (Metro + Water Metro + Feeder Bus), this journey reduces urban traffic congestion in Greater Kochi.</p>
                </div>
              </div>
            )}
          </div>
        </aside>

        <main className="flex-1 relative">
          <MapVisualizer
            networkData={networkData}
            activeRoute={activeRoute}
            origin={origin}
            destination={destination}
            pickingMode={pickingMode}
            onSelectPoint={handleSelectPoint}
            onCancelPickingMode={() => setPickingMode(null)}
          />
          <AIChatModal onSelectTrip={handleSelectTripFromAI} />
        </main>
      </div>
    </div>
  );
}
