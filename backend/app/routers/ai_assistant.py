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
    """
    AI Travel Assistant Endpoint.
    Uses NLP / keyword matching to extract origin & destination stops from user query,
    then generates multimodal travel recommendations or calls Gemini API if key is present.
    """
    user_msg = req.message.lower()
    stops = db.query(Stop).all()

    # Detect known stops mentioned in user prompt
    detected_stops = []
    for s in stops:
        clean_name = s.name.lower().replace(" metro", "").replace(" water metro", "").replace(" bus stop", "")
        if clean_name in user_msg or s.name.lower() in user_msg:
            detected_stops.append(s)

    gemini_key = os.getenv("GEMINI_API_KEY")

    # If Gemini API Key is configured, use Google GenAI LLM
    if gemini_key:
        try:
            from google import genai
            client = genai.Client(api_key=gemini_key)
            prompt = f"""You are the smartRoute AI Travel Assistant for Greater Kochi Multimodal Transit (Kochi Metro, Water Metro, Feeder Buses).
User Query: {req.message}
Provide a polite, concise travel recommendation in 3-4 bullet points."""
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
            )
            return AIChatResponse(reply=response.text)
        except Exception:
            pass

    # Intelligent local route detection fallback
    if len(detected_stops) >= 2:
        orig, dest = detected_stops[0], detected_stops[1]
        router_instance = MultimodalRouter(db)
        itinerary = router_instance.find_shortest_path(orig.id, dest.id)
        if itinerary:
            steps_summary = " ➔ ".join([leg["to_stop"]["name"] for leg in itinerary["legs"][:4]])
            reply = (
                f"Recommended multimodal route from **{orig.name}** to **{dest.name}**:\n\n"
                f"• **Duration**: ~{itinerary['total_duration_min']} mins\n"
                f"• **Estimated Fare**: ₹{itinerary['total_fare']}\n"
                f"• **Transport Modes**: {', '.join(itinerary['modes']).upper()}\n\n"
                f"**Key Stops**: {steps_summary}\n"
                f"The complete route is mapped in your Journey Planner!"
            )
            return AIChatResponse(
                reply=reply,
                suggested_origin=orig.id,
                suggested_destination=dest.id,
                itinerary_preview=itinerary
            )

    return AIChatResponse(
        reply=(
            "Hello! I am your **smartRoute AI Travel Assistant**. "
            "Ask me how to travel between any points in Greater Kochi "
            "(e.g., *'How to go from Rajagiri to Fort Kochi?'* or *'Fastest route from Aluva to Infopark'*)!"
        )
    )
