import React from "react";

export default function JourneyPlanner({
  stops = [],
  origin,
  destination,
  pickingMode,
  onSelectOrigin,
  onSelectDestination,
  onSetPickingMode,
  onSwapPoints,
  onPlanRoute,
  activeRoute,
  loading,
  preference = "fastest",
  onPreferenceChange,
  onSelectOption
}) {
  const handleSubmit = (e) => {
    e.preventDefault();
    if (!origin || !destination) {
      alert("Please choose both an origin and a destination point.");
      return;
    }
    onPlanRoute(origin, destination, preference);
  };

  const handleQuickPick = (origId, destId) => {
    const origStop = stops.find((s) => s.id === origId) || origId;
    const destStop = stops.find((s) => s.id === destId) || destId;
    onSelectOrigin(origStop);
    onSelectDestination(destStop);
    onPlanRoute(origStop, destStop, preference);
  };

  const renderPointInput = (type, point, setPoint) => {
    const isOrigin = type === "origin";
    const isPickingThis = pickingMode === type;

    return (
      <div className="space-y-1.5">
        <div className="flex items-center justify-between">
          <label className="text-xs font-semibold text-slate-600 uppercase tracking-wider flex items-center gap-1">
            {isOrigin ? "🚀 Starting Point" : "🏁 Destination Point"}
          </label>
          <button
            type="button"
            onClick={() => onSetPickingMode(isPickingThis ? null : type)}
            className={`text-[11px] px-2 py-0.5 rounded-full font-medium border transition flex items-center gap-1 ${
              isPickingThis
                ? "bg-blue-600 text-white border-blue-600 animate-pulse"
                : "bg-white text-blue-600 border-blue-300 hover:bg-blue-50"
            }`}
          >
            🎯 {isPickingThis ? "Picking on Map..." : "Pick on Map"}
          </button>
        </div>

        {point && typeof point === "object" && point.name ? (
          <div className="flex items-center justify-between bg-blue-50 border border-blue-200 p-2 rounded-lg text-xs">
            <div className="flex items-center gap-2 overflow-hidden">
              <span className="text-base">{isOrigin ? "📍" : "🏁"}</span>
              <div className="truncate">
                <span className="font-semibold text-slate-800 block truncate">{point.name}</span>
                {point.lat && (
                  <span className="text-[10px] text-slate-400 font-mono">
                    ({point.lat.toFixed(4)}, {point.lon.toFixed(4)})
                  </span>
                )}
              </div>
            </div>
            <button
              type="button"
              onClick={() => setPoint(null)}
              className="text-slate-400 hover:text-red-500 font-bold px-1.5 py-0.5 text-xs rounded"
              title="Clear selection"
            >
              ✕
            </button>
          </div>
        ) : (
          <select
            value={typeof point === "string" ? point : point?.id || ""}
            onChange={(e) => {
              const val = e.target.value;
              const selectedStop = stops.find((s) => s.id === val);
              setPoint(selectedStop || val);
            }}
            className="w-full text-xs p-2 rounded-lg border border-slate-300 focus:ring-2 focus:ring-blue-500 focus:outline-none bg-white text-slate-800"
          >
            <option value="">Choose station or pick on map...</option>
            {stops.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name} ({s.agency})
              </option>
            ))}
          </select>
        )}
      </div>
    );
  };

  return (
    <div className="space-y-4">
      <form onSubmit={handleSubmit} className="bg-slate-50 p-3.5 rounded-xl border border-slate-200 space-y-3 shadow-sm">
        {/* Origin */}
        {renderPointInput("origin", origin, onSelectOrigin)}

        {/* Swap Button */}
        <div className="flex justify-center -my-1">
          <button
            type="button"
            onClick={onSwapPoints}
            className="p-1.5 bg-white border border-slate-200 hover:bg-slate-100 rounded-full shadow-sm text-slate-600 transition"
            title="Swap Origin and Destination"
          >
            🔃
          </button>
        </div>

        {/* Destination */}
        {renderPointInput("destination", destination, onSelectDestination)}

        {/* Quick-Filter Toggles (Fastest vs. Cheapest vs. Greenest) */}
        <div>
          <label className="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1">
            ⚡ Quick-Filter Toggle
          </label>
          <div className="grid grid-cols-3 gap-1 bg-slate-200/70 p-1 rounded-lg text-xs font-medium">
            <button
              type="button"
              onClick={() => onPreferenceChange?.("fastest")}
              className={`py-1.5 rounded-md transition flex items-center justify-center gap-1 ${
                preference === "fastest" ? "bg-white shadow text-blue-700 font-bold" : "text-slate-600 hover:text-slate-900"
              }`}
            >
              ⚡ Fastest
            </button>
            <button
              type="button"
              onClick={() => onPreferenceChange?.("cheapest")}
              className={`py-1.5 rounded-md transition flex items-center justify-center gap-1 ${
                preference === "cheapest" ? "bg-white shadow text-blue-700 font-bold" : "text-slate-600 hover:text-slate-900"
              }`}
            >
              💰 Cheapest
            </button>
            <button
              type="button"
              onClick={() => onPreferenceChange?.("greenest")}
              className={`py-1.5 rounded-md transition flex items-center justify-center gap-1 ${
                preference === "greenest" ? "bg-white shadow text-emerald-700 font-bold" : "text-slate-600 hover:text-slate-900"
              }`}
            >
              🌿 Greenest
            </button>
          </div>
        </div>

        {/* Quick Presets */}
        <div>
          <span className="text-[11px] text-slate-400 font-medium">Quick Presets:</span>
          <div className="flex flex-wrap gap-1 mt-1">
            <button
              type="button"
              onClick={() => handleQuickPick("BUS_RAJAGIRI", "WM_S8")}
              className="text-[10px] px-2 py-0.5 bg-slate-200 hover:bg-blue-100 hover:text-blue-700 rounded transition"
            >
              Rajagiri → Fort Kochi
            </button>
            <button
              type="button"
              onClick={() => handleQuickPick("KMRL_ALVA", "BUS_INFOPARK_P1")}
              className="text-[10px] px-2 py-0.5 bg-slate-200 hover:bg-blue-100 hover:text-blue-700 rounded transition"
            >
              Aluva → Infopark
            </button>
            <button
              type="button"
              onClick={() => handleQuickPick("WM_S1", "KMRL_MGRD")}
              className="text-[10px] px-2 py-0.5 bg-slate-200 hover:bg-blue-100 hover:text-blue-700 rounded transition"
            >
              Vyttila → MG Road
            </button>
          </div>
        </div>

        {/* Submit Plan Button */}
        <button
          type="submit"
          disabled={loading || !origin || !destination}
          className="w-full py-2.5 px-4 bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs rounded-lg shadow-sm flex items-center justify-center gap-2 transition disabled:opacity-50"
        >
          {loading ? "Calculating Multimodal Route..." : "Find Multimodal Route"}
        </button>
      </form>

      {/* Itinerary Result Display */}
      {activeRoute && (
        <div className="space-y-3">
          {/* Carbon Footprint / Eco-Savings Counter Widget */}
          <div className="bg-gradient-to-r from-emerald-50 to-teal-50 border border-emerald-200 rounded-xl p-3 shadow-sm flex items-center justify-between text-xs">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-full bg-emerald-600 text-white flex items-center justify-center font-bold text-base shadow-sm">
                🌱
              </div>
              <div>
                <span className="font-bold text-emerald-950 block text-xs">Eco-Savings Counter</span>
                <span className="text-[10px] text-emerald-700">CO₂ Avoided vs Private Car</span>
              </div>
            </div>
            <div className="text-right">
              <span className="text-base font-extrabold text-emerald-700 block">
                {activeRoute.co2_saved_kg || (activeRoute.total_distance_km * 0.12).toFixed(2)} kg CO₂
              </span>
              <span className="text-[10px] text-slate-500">
                Kochi1 Card: <b className="text-slate-800">₹{activeRoute.kochi1_card_fare || Math.round(activeRoute.total_fare * 0.8)}</b>
              </span>
            </div>
          </div>

          {/* Multiple Route Options Tabs if available */}
          {activeRoute.options && activeRoute.options.length > 1 && (
            <div className="space-y-1.5">
              <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">
                Alternative Route Options ({activeRoute.options.length})
              </span>
              <div className="space-y-1">
                {activeRoute.options.map((opt, idx) => {
                  const isSelected = activeRoute.option_id === opt.option_id || (idx === 0 && !activeRoute.option_id);
                  return (
                    <div
                      key={idx}
                      onClick={() => onSelectOption?.(opt)}
                      className={`p-2 rounded-lg border text-xs cursor-pointer transition flex items-center justify-between ${
                        isSelected
                          ? "bg-blue-600 text-white border-blue-600 shadow"
                          : "bg-white border-slate-200 hover:bg-slate-50 text-slate-800"
                      }`}
                    >
                      <div>
                        <span className="font-bold block">{opt.title || `Option ${idx + 1}`}</span>
                        <span className={`text-[10px] ${isSelected ? "text-blue-100" : "text-slate-500"}`}>
                          {opt.total_duration_min} min • {opt.total_distance_km} km • {opt.modes?.join(", ")}
                        </span>
                      </div>
                      <div className="text-right">
                        <span className={`font-bold text-xs block ${isSelected ? "bg-white text-blue-700 px-2 py-0.5 rounded" : "text-slate-800"}`}>
                          ₹{opt.total_fare}
                        </span>
                        <span className={`text-[9px] ${isSelected ? "text-blue-200" : "text-emerald-600 font-semibold"}`}>
                          🌱 {opt.co2_saved_kg || (opt.total_distance_km * 0.12).toFixed(2)}kg CO₂
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Active Option Card */}
          <div className="bg-blue-50 border border-blue-200 rounded-xl p-3.5 shadow-sm">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-bold uppercase tracking-wider text-blue-700">
                {activeRoute.title || "Optimal Journey"}
              </span>
              <div className="text-right">
                <span className="text-sm font-bold text-slate-800 bg-white px-2 py-0.5 rounded border border-blue-200 block">
                  ₹{activeRoute.total_fare}
                </span>
                <span className="text-[9px] text-blue-600 font-medium block mt-0.5">
                  Smart Card: ₹{activeRoute.kochi1_card_fare || Math.round(activeRoute.total_fare * 0.8)}
                </span>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-2 text-center text-xs">
              <div className="bg-white p-2 rounded-lg border border-blue-100">
                <span className="text-slate-400 block text-[10px]">TOTAL TIME</span>
                <span className="text-sm font-bold text-slate-800">{activeRoute.total_duration_min} min</span>
              </div>
              <div className="bg-white p-2 rounded-lg border border-blue-100">
                <span className="text-slate-400 block text-[10px]">TOTAL DISTANCE</span>
                <span className="text-sm font-bold text-slate-800">{activeRoute.total_distance_km} km</span>
              </div>
            </div>
            <div className="mt-2 text-[11px] text-slate-600 flex items-center justify-between">
              <span>
                Modes: <b className="uppercase text-blue-800">{activeRoute.modes?.join(", ")}</b>
              </span>
              <span>
                Transfers: <b className="text-slate-800">{activeRoute.transfer_count}</b>
              </span>
            </div>
          </div>

          {/* Turn-by-Turn Legs */}
          <div>
            <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Turn-by-Turn Guidance</h3>
            <div className="space-y-2 text-xs">
              {activeRoute.legs?.map((leg) => (
                <div key={leg.step} className="flex items-start gap-2.5 p-2 rounded-lg bg-white border border-slate-200 shadow-sm">
                  <div className="w-6 h-6 rounded-full bg-slate-100 text-slate-700 flex items-center justify-center font-bold text-xs flex-shrink-0">
                    {leg.step}
                  </div>
                  <div className="flex-1">
                    <p className="font-medium text-slate-800">{leg.instruction}</p>
                    <div className="flex items-center gap-3 text-[10px] text-slate-500 mt-1">
                      <span>⏱ {leg.duration_min} min</span>
                      <span>📏 {leg.distance_km} km</span>
                      {leg.fare > 0 && <span>🎟 ₹{leg.fare}</span>}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
