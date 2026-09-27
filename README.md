# smartRoute: AI-Enabled Multimodal MaaS Platform

**Guide**: Mr. Paul Augustine  
**Team**: Martina Ajish (U2303147), Merin Benny (U2303151), Milee B Kokkatt (U2303152), Navami Anilkumar (U2303164)  
**Institution**: Rajagiri School of Engineering & Technology (RSET)

---

## 30% Code Implementation Prototype

This repository contains the working **30% Milestone Prototype** for the smartRoute platform, unifying Greater Kochi's public transit network into an integrated Mobility-as-a-Service (MaaS) system.

### 1. Real Datasets Integrated
- **Kochi Metro Rail Limited (KMRL)**: Complete official GTFS feed (25 stations from Aluva to Thripunithura, shapes, timetables, and fare tables).
- **Kochi Water Metro (KWML)**: 13 Jetties and 5 backwater ferry routes (Vyttila ↔ Kakkanad, High Court ↔ Fort Kochi, etc.).
- **Feeder Buses**: Real feeder bus timetables and stops connecting Kalamassery Metro, **Rajagiri College (RSET)**, CUSAT, Kakkanad Civil Station, and Infopark Phase 1 & 2.
- **Multimodal Interchanges**: 34 walking transfer links between nearby stations (< 500m) with automatic mode-switching penalties.

---

## 2. Team Work Division (30% Deliverables)

| Member | Domain | Delivered Code & Files |
| :--- | :--- | :--- |
| **Member 3** | **Database & GIS Pipeline** | `backend/app/services/data_ingestion.py`, `backend/app/db/models.py`, `smartroute.db` SQLite spatial database with 60 stops and 144 multimodal edges. |
| **Member 2** | **Backend & Routing Logic** | `backend/app/services/dijkstra.py` (Multimodal Dijkstra shortest path algorithm), `backend/app/routers/routing.py`, `backend/main.py`. |
| **Member 1** | **Frontend & Visualization** | `frontend/index.html` (Interactive Leaflet Map dashboard), `frontend/src/components/MapVisualizer.jsx`, `frontend/src/components/JourneyPlanner.jsx`. |
| **Member 4** | **AI Systems & Validation** | `backend/app/routers/ai_assistant.py` (Gemini API travel assistant + NLP query parsing), `backend/test_dijkstra.py`, `backend/test_api.py`. |

---

## 3. Quick Start (Run in 1 Command)

### Prerequisites
- Python 3.10+
- Installed packages: `pip install -r backend/requirements.txt`

### Step 1: Run the Server
From the project root:
```powershell
python backend/main.py
```

### Step 2: Open in Browser
Open your browser and visit:
👉 **[http://localhost:8000](http://localhost:8000)**

You will immediately see the interactive **Leaflet Map Dashboard** loaded with:
- All 60 stations/jetties/bus stops plotted across Greater Kochi.
- Metro lines (Blue), Water Metro routes (Teal), Feeder bus corridors (Orange), and Walk links (Dotted).
- Origin $\to$ Destination journey search box.
- Step-by-step multimodal itinerary breakdown with fares and durations.
- AI Travel Assistant chat widget in the bottom right corner!

---

## 4. Running Verification Tests

To verify that the Dijkstra routing and API endpoints work properly from the command line:

```powershell
# 1. Test Multimodal Dijkstra Pathfinding
python backend/test_dijkstra.py

# 2. Test All FastAPI Endpoints
python backend/test_api.py
```
