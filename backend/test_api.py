import sys
import os

backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from starlette.testclient import TestClient
from main import app

client = TestClient(app)

def test_api():
    print("Testing SmartRoute Backend API Endpoints...\n")

    # 1. Root (Serves Frontend Map Dashboard)
    res = client.get("/")
    print(f"GET / -> Status: {res.status_code}, Content-Type: {res.headers.get('content-type')}")
    assert res.status_code == 200 and "text/html" in res.headers.get("content-type", "")
    print("Frontend Leaflet Map Dashboard is successfully served at /\n")

    # 2. Stops
    res = client.get("/api/transit/stops")
    stops = res.json()
    print(f"GET /api/transit/stops -> Status: {res.status_code}, Found {len(stops)} stops.")
    assert res.status_code == 200 and len(stops) > 0

    # 3. Plan Journey (Rajagiri -> Fort Kochi)
    res = client.post("/api/routing/plan", json={
        "origin_id": "BUS_RAJAGIRI",
        "destination_id": "WM_S8",
        "preference": "fastest"
    })
    print(f"POST /api/routing/plan (Rajagiri -> Fort Kochi) -> Status: {res.status_code}")
    data = res.json()
    print(f"Total Duration : {data['total_duration_min']} min")
    print(f"Total Fare     : Rs. {data['total_fare']}")
    print(f"Modes          : {data['modes']}")
    print(f"Legs Count     : {len(data['legs'])}\n")
    assert res.status_code == 200

    # 4. AI Chat
    res = client.post("/api/ai/chat", json={
        "message": "How do I get from Aluva to Infopark?"
    })
    print(f"POST /api/ai/chat -> Status: {res.status_code}")
    ai_data = res.json()
    print(f"AI Reply: {ai_data['reply'][:120]}...\n")
    assert res.status_code == 200

    print("ALL API ENDPOINT TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_api()
