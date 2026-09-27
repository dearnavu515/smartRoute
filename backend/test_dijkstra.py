import sys
import os

backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.db.database import SessionLocal
from app.services.dijkstra import MultimodalRouter

def test_routes():
    db = SessionLocal()
    try:
        router = MultimodalRouter(db)
        print(f"Loaded Router with {len(router.stops)} stops and {sum(len(v) for v in router.graph.values())} directed edges.")

        test_trips = [
            ("BUS_RAJAGIRI", "WM_S8", "Rajagiri College -> Fort Kochi Water Metro"),
            ("KMRL_ALVA", "BUS_INFOPARK_P1", "Aluva Metro -> Infopark Phase 1"),
            ("WM_S1", "KMRL_MGRD", "Vyttila Water Metro -> MG Road Metro"),
            ("BUS_CUSAT", "BUS_KADAVANTHRA", "CUSAT Campus -> Kadavanthra Junction")
        ]

        for orig, dest, label in test_trips:
            print(f"\n{'='*65}\nTEST JOURNEY: {label}\n{'='*65}")
            itinerary = router.find_shortest_path(orig, dest, preference="fastest")
            if not itinerary:
                print(f"FAILED: No path found between {orig} and {dest}")
                continue

            print(f"Total Duration : {itinerary['total_duration_min']} minutes")
            print(f"Total Distance : {itinerary['total_distance_km']} km")
            print(f"Estimated Fare : Rs. {itinerary['total_fare']}")
            print(f"Modes Involved : {', '.join(itinerary['modes']).upper()}")
            print(f"Transfers      : {itinerary['transfer_count']}")
            print("\nStep-by-step Itinerary:")
            for leg in itinerary["legs"]:
                mode_icon = {
                    "metro": "[METRO]",
                    "water_metro": "[FERRY]",
                    "bus": "[BUS]  ",
                    "walk": "[WALK] "
                }.get(leg["mode"], "[TRIP] ")
                print(f"  Step {leg['step']:<2}: {mode_icon} {leg['instruction']} ({leg['duration_min']} min, {leg['distance_km']} km, Rs. {leg['fare']})")

    finally:
        db.close()

if __name__ == "__main__":
    test_routes()
