# 🎓 smartRoute: Viva Voce & Code Explanation Guide

> **Project Name**: smartRoute – AI-Enabled Multimodal Mobility-as-a-Service (MaaS) Platform  
> **Target Domain**: Greater Kochi Integrated Public Transit (Kochi Metro + Water Metro + Feeder Buses)  
> **Tech Stack**: Python 3.10+, FastAPI, SQLite / SQLAlchemy, Multimodal Dijkstra Algorithm, Leaflet.js, React / HTML5, Gemini AI.

---

## 1. High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           FRONTEND LAYER                                │
│   Interactive Leaflet.js Map Dashboard + Journey Planner Sidebar + AI   │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │ REST APIs (JSON)
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        FASTAPI BACKEND SERVER                           │
│  Main API Gateway (main.py) -> Routers (routing.py, transit.py, ai.py) │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                   MULTIMODAL DIJKSTRA ROUTING ENGINE                    │
│   • Graph Construction (stops -> nodes, transit lines -> edges)        │
│   • Priority Queue (heapq) Min-Cost Pathfinding                         │
│   • Mode Transfer Penalties & Dynamic Weight Optimization                │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                            DATABASE LAYER                               │
│      SQLite (`smartroute.db`) created via GTFS & Excel Ingestion        │
│      Tables: `stops`, `routes`, `edges`, `fare_rules`                  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Core Code Modules Explanation

### 1. `backend/app/services/dijkstra.py` (Routing Engine)
* **`haversine_km(lat1, lon1, lat2, lon2)`**: Computes the spherical distance in kilometers between two GPS coordinates using the Haversine formula:
  $$d = 2R \arcsin\left(\sqrt{\sin^2\left(\frac{\Delta \phi}{2}\right) + \cos(\phi_1)\cos(\phi_2)\sin^2\left(\frac{\Delta \lambda}{2}\right)}\right)$$
* **`_build_graph()`**: Loads all stops and directed edges from the database into an adjacency list dictionary: `adj[from_stop_id] = [{to, mode, route_id, duration, distance, fare, geometry}]`.
* **`find_shortest_path(origin_id, destination_id, preference)`**:
  - Uses Python's `heapq` (Min-Heap Priority Queue) for $O((E + V) \log V)$ pathfinding.
  - State tracked in queue: `(cost, count, current_stop_id, last_mode, path_edges)`.
  - **Dynamic Weight Calculation**:
    - **Fastest**: weight = travel duration + transfer penalty (+2.5 to 4 min) when switching between public transit modes.
    - **Cheapest**: weight = fare + (duration $\times$ 0.1).
    - **Greenest**: weight = duration + eco penalty (Walk: 0, Water Metro: 0.5, Metro: 1.0, Bus: 3.0).
* **`_format_itinerary(...)`**: Takes raw graph edges and groups consecutive stops on the same line into human-readable instructions (e.g. *"Board Kochi Metro at Aluva to Kalamassery (4 stops)"*).

---

### 2. `backend/app/services/data_ingestion.py` (Data Pipeline)
* **Step 1 (KMRL Metro)**: Reads the official GTFS ZIP feed (`stops.txt`, `stop_times.txt`), populates 25 metro stations, Metro Line 1 route, and calculates inter-station travel times (average speed ~36 km/h).
* **Step 2 (KWML Water Metro)**: Reads Water Metro Excel dataset (13 jetties, 4 ferry routes: Vyttila ↔ Kakkanad, High Court ↔ Fort Kochi, etc., boat speed ~15 km/h).
* **Step 3 (Feeder Buses)**: Ingests 22 key feeder bus stops connecting major campuses (**Rajagiri / RSET**, CUSAT, Infopark Phase 1 & 2, Kakkanad Civil Station, MG Road, Kadavanthra).
* **Step 4 (Multimodal Transfer Links)**: Automatically calculates Haversine distance between stops of *different modes*. If distance $\le 500$ meters, it inserts synthetic bidirectional `walk` edges to allow seamless transfers between Metro, Water Metro, and Buses.

---

### 3. `backend/main.py` & Routers (`routing.py`, `transit.py`, `ai_assistant.py`)
* **`main.py`**: Initializes FastAPI, enables CORS, mounts static frontend files, and exposes `/docs` (Swagger UI).
* **`routing.py`**: Endpoint `POST /api/routing/plan`. Takes origin/destination IDs or GPS coordinates, invokes `MultimodalRouter`, and returns route options.
* **`transit.py`**: Endpoint `GET /api/transit/network-graph`. Delivers full transit network (stops, routes, edges) to render the map dashboard.
* **`ai_assistant.py`**: Endpoint `POST /api/ai/chat`. Parses natural language query from user, extracts stop names, generates itinerary summary, or calls Gemini API if key is present.

---

## 3. Top 10 Viva Voce Questions & Answers

### Q1: Why did you choose Dijkstra's algorithm for journey planning?
**Answer**: BFS only works for unweighted graphs. In a real multimodal transit network, edges have varying weights (travel times, fares, walking transfers). Dijkstra’s algorithm guarantees finding the optimal shortest path in non-negative weighted graphs using a min-heap priority queue in $O((E + V) \log V)$ time complexity.

### Q2: How does your algorithm handle transfers between different transport modes?
**Answer**: Our data pipeline connects stops of different modes within 500m using synthetic `walk` transfer edges. During Dijkstra search, when the current edge mode differs from the previous edge mode, a transfer time penalty (2.5 to 4 minutes) is added to the cost function to reflect real-world waiting and walking time.

### Q3: How do map pick clicks work when the user clicks an arbitrary location on the map?
**Answer**: When a user clicks a custom point, `find_nearest_stop()` finds the closest transit stop using Haversine distance. `_attach_custom_endpoints()` then prepends/appends a walking leg from the custom map point to the nearest station.

### Q4: What datasets did you integrate?
**Answer**: 
1. Official GTFS Feed from **Kochi Metro Rail Limited (KMRL)** (25 stations, Line 1 timetables).
2. Official Excel dataset from **Kochi Water Metro Limited (KWML)** (13 jetties, 4 ferry routes).
3. **Feeder Bus** network dataset covering Rajagiri (RSET), CUSAT, Infopark, Kakkanad, MG Road.

### Q5: How is fare calculated?
**Answer**: Each edge in the database has a designated fare. The total trip fare is the sum of leg fares. We also compute a 20% discounted fare for **Kochi1 Smart Card** holders (`total_fare * 0.8`).

### Q6: What is the database schema?
**Answer**: We use SQLite via SQLAlchemy with 4 main tables:
1. `stops`: `id`, `name`, `lat`, `lon`, `mode`, `agency`.
2. `routes`: `id`, `short_name`, `long_name`, `mode`, `agency`, `color`.
3. `edges`: `id`, `route_id`, `from_stop_id`, `to_stop_id`, `mode`, `distance_km`, `duration_min`, `fare`, `geometry`.
4. `fare_rules`: `mode`, `origin_id`, `destination_id`, `fare`.

### Q7: How does the AI Travel Assistant work?
**Answer**: The assistant parses user text queries (e.g., *"How to go from Rajagiri to Fort Kochi?"*). It extracts mentioned stop names, runs the Dijkstra router, and formats a quick summary. If a Gemini API key is configured, it calls `gemini-2.5-flash` for enhanced conversational recommendations.

### Q8: How is the frontend integrated with Leaflet maps?
**Answer**: The frontend uses Leaflet.js to render interactive tiles (Google Maps / OpenStreetMap). It fetches the network graph from `/api/transit/network-graph`, plots station markers with custom mode icons (🚆 Metro, 🚤 Water Metro, 🚌 Bus), and draws polylines for calculated journey routes.

### Q9: How do you measure environmental impact?
**Answer**: We calculate CO₂ saved vs private car trips using average transit emissions factors: $\text{CO}_2 \text{ Saved (kg)} = \text{Distance (km)} \times 0.12$.

### Q10: How can this system be scaled for production?
**Answer**: SQLite can be replaced with PostgreSQL + PostGIS (using our included `init_postgis.sql` migration script) for spatial indexing (`ST_DWithin`, `GIST` indices) and Redis caching for ultra-fast route lookups.

---

## 4. Quick Commands Reference

```powershell
# 1. Ingest Data & Initialize SQLite DB
python backend/app/services/data_ingestion.py

# 2. Run Multimodal Dijkstra Test Suite
python backend/test_dijkstra.py

# 3. Run FastAPI Backend Server
python backend/main.py

# 4. Open in Browser
# http://127.0.0.1:8000
```
