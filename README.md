# smartRoute: AI-Enabled Multimodal MaaS Platform


This repository contains the working **30% Prototype** for the smartRoute platform, unifying Kochi's public transit network into an integrated Mobility-as-a-Service (MaaS) system.

### 1. Real Datasets Integrated
- **Kochi Metro Rail Limited (KMRL)**: Complete official GTFS feed (25 stations from Aluva to Thripunithura, shapes, timetables, and fare tables).
- **Kochi Water Metro (KWML)**: 13 Jetties and 5 backwater ferry routes (Vyttila ↔ Kakkanad, High Court ↔ Fort Kochi, etc.).
- **Feeder Buses**: Real feeder bus timetables and stops connecting Kalamassery Metro, **Rajagiri College (RSET)**, CUSAT, Kakkanad Civil Station, and Infopark Phase 1 & 2.
- **Multimodal Interchanges**: 34 walking transfer links between nearby stations (< 500m) with automatic mode-switching penalties.

---

## 2. Quick Start (Run in 1 Command)

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

## 3. Running Verification Tests

To verify that the Dijkstra routing and API endpoints work properly from the command line:

```powershell
# 1. Test Multimodal Dijkstra Pathfinding
python backend/test_dijkstra.py

# 2. Test All FastAPI Endpoints
python backend/test_api.py
```
