import os
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from ..db.database import get_db
from ..db.models import Stop
from ..services.dijkstra import MultimodalRouter

router = APIRouter(prefix="/api/ai", tags=["ai"])

class AIChatRequest(BaseModel):
    message: str

class AIChatResponse(BaseModel):
    reply: str
    suggested_origin: str = None
    suggested_destination: str = None
    itinerary_preview: dict = None

@router.post("/chat", response_model=AIChatResponse)
def ai_chat(req: AIChatRequest, db: Session = Depends(get_db)):
    user_msg = req.message.lower()
    stops = db.query(Stop).all()

    # Detect if any known stops are mentioned
    detected_stops = []
    for s in stops:
        s_clean = s.name.lower().replace(" metro", "").replace(" water metro", "").replace(" bus stop", "")
        if s_clean in user_msg or s.name.lower() in user_msg:
            detected_stops.append(s)

    gemini_key = os.getenv("GEMINI_API_KEY")

    # If Gemini API key is available, attempt LLM call
    if gemini_key:
        try:
            from google import genai
            client = genai.Client(api_key=gemini_key)
            prompt = f"""You are the smartRoute AI Travel Assistant for the Greater Kochi Multimodal Transit Network (Kochi Metro, Kochi Water Metro, and Feeder Buses).
User Query: {req.message}
Known transit modes:
1. Kochi Metro Line 1 (Aluva to Thripunithura - 25 stations).
2. Kochi Water Metro (Line 1: Vyttila ↔ Kakkanad | Line 2: High Court ↔ Fort Kochi via Vypin). Note: Kakkanad Water Metro connects Kakkanad to Vyttila, not directly to Fort Kochi.
3. Feeder Buses: Kalamassery, Kakkanad Civil Station, Infopark Phase 1 & 2, Rajagiri College / RSET, CUSAT, MG Road, Kadavanthra.

Provide a concise, polite, and practical multimodal transit recommendation."""
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
            )
            return AIChatResponse(reply=response.text)
        except Exception as e:
            pass

    # Intelligent fallback when LLM key is not configured
    if len(detected_stops) >= 2:
        orig = detected_stops[0]
        dest = detected_stops[1]
        router_instance = MultimodalRouter(db)
        itinerary = router_instance.find_shortest_path(orig.id, dest.id)
        if itinerary:
            steps_summary = " -> ".join([leg["to_stop"]["name"] for leg in itinerary["legs"][:4]])
            reply = (
                f"Based on your query, here is the recommended multimodal route from **{orig.name}** to **{dest.name}**:\n\n"
                f"- **Total Duration**: ~{itinerary['total_duration_min']} mins\n"
                f"- **Estimated Fare**: Rs. {itinerary['total_fare']}\n"
                f"- **Modes Used**: {', '.join(itinerary['modes']).upper()}\n\n"
                f"**Key Segments**: {steps_summary}...\n"
                f"The complete route is mapped in the Journey Planner!"
            )
            return AIChatResponse(
                reply=reply,
                suggested_origin=orig.id,
                suggested_destination=dest.id,
                itinerary_preview=itinerary
            )

    # General assistance
    return AIChatResponse(
        reply=(
            "Hello! I am your **smartRoute AI Travel Assistant**. "
            "You can ask me how to travel between any points in Greater Kochi (e.g. *'How to go from Rajagiri to Fort Kochi?'* or *'Fastest route from Aluva to Infopark'*) "
            "and I will calculate the best multimodal combination of Metro, Water Metro, and Feeder Bus for you!"
        )
    )
