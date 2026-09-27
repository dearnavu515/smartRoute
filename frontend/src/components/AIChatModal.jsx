import React, { useState, useRef, useEffect } from "react";
import { sendAIChat } from "../services/api";

export default function AIChatModal({ onSelectTrip }) {
  const [messages, setMessages] = useState([
    { role: "assistant", text: "👋 Hi! I am your **smartRoute AI**. Ask me how to travel between stations or campuses in Greater Kochi!" }
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef(null);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userText = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", text: userText }]);
    setLoading(true);

    try {
      const res = await sendAIChat(userText);
      setMessages((prev) => [...prev, { role: "assistant", text: res.reply }]);
      if (res.suggested_origin && res.suggested_destination && onSelectTrip) {
        onSelectTrip(res.suggested_origin, res.suggested_destination, res.itinerary_preview);
      }
    } catch (err) {
      setMessages((prev) => [...prev, { role: "assistant", text: "⚠️ Error contacting AI service." }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="absolute bottom-5 right-5 z-20 w-80 bg-white rounded-2xl shadow-2xl border border-slate-200 overflow-hidden flex flex-col">
      <div className="bg-slate-900 text-white px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" />
          <span className="text-xs font-bold tracking-wide">smartRoute AI Assistant</span>
        </div>
      </div>

      <div className="h-52 overflow-y-auto p-3 text-xs space-y-2 bg-slate-50">
        {messages.map((m, i) => (
          <div
            key={i}
            className={`p-2.5 rounded-xl text-xs whitespace-pre-line shadow-sm ${
              m.role === "user"
                ? "bg-blue-600 text-white ml-6 rounded-tr-none text-right"
                : "bg-white text-slate-800 mr-6 border border-slate-200"
            }`}
          >
            {m.text}
          </div>
        ))}
        {loading && (
          <div className="bg-white p-2 rounded-xl border border-slate-200 text-slate-400 text-[11px] italic mr-6">
            Consulting transit engine...
          </div>
        )}
        <div ref={scrollRef} />
      </div>

      <form onSubmit={handleSend} className="p-2 bg-white border-t border-slate-200 flex gap-1.5">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="e.g. Fastest route from Rajagiri to Fort Kochi?"
          className="flex-1 text-xs px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
        <button type="submit" className="bg-blue-600 hover:bg-blue-700 text-white px-3 py-2 rounded-lg text-xs font-semibold">
          Send
        </button>
      </form>
    </div>
  );
}
