import json
import math
import heapq
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from ..db.models import Stop, Route, Edge

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates the Great Circle distance in kilometers between two geographic coordinates."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

class MultimodalRouter:
    """
    Multimodal Dijkstra Routing Engine.
    Combines Metro, Water Metro, and Feeder Buses into a unified graph.
    """
    def __init__(self, db: Session):
        self.db = db
        self.stops = {s.id: s for s in db.query(Stop).all()}
        self.routes = {r.id: r for r in db.query(Route).all()}
        self.graph = self._build_graph()

    def _build_graph(self) -> Dict[str, List[Dict[str, Any]]]:
        """Builds an adjacency list graph mapping stop_id -> outgoing edges."""
        adj: Dict[str, List[Dict[str, Any]]] = {sid: [] for sid in self.stops}
        edges = self.db.query(Edge).all()
        for e in edges:
            if e.from_stop_id in adj and e.to_stop_id in self.stops:
                geom = []
                if e.geometry:
                    try:
                        geom = json.loads(e.geometry)
                    except Exception:
                        pass
                if not geom:
                    s1, s2 = self.stops[e.from_stop_id], self.stops[e.to_stop_id]
                    geom = [[s1.lat, s1.lon], [s2.lat, s2.lon]]

                adj[e.from_stop_id].append({
                    "to": e.to_stop_id,
                    "mode": e.mode,
                    "route_id": e.route_id,
                    "duration": e.duration_min,
                    "distance": e.distance_km,
                    "fare": e.fare,
                    "geometry": geom
                })
        return adj

    def find_shortest_path(
        self,
        origin_id: str,
        destination_id: str,
        preference: str = "fastest"
    ) -> Optional[Dict[str, Any]]:
        """
        Executes Dijkstra's algorithm to find the optimal multimodal path.
        Applies mode switch penalties and dynamic weight optimization based on user preference.
        """
        if origin_id not in self.stops or destination_id not in self.stops:
            return None

        if origin_id == destination_id:
            s = self.stops[origin_id]
            return {
                "origin": s.to_dict(),
                "destination": s.to_dict(),
                "total_duration_min": 0,
                "total_distance_km": 0,
                "total_fare": 0,
                "legs": [],
                "summary": "Origin and destination are the same station."
            }

        # Min-Priority Queue stores tuples of: (accumulated_cost, counter, current_stop_id, last_mode, path_edges)
        best_cost: Dict[str, float] = {}
        count = 0
        pq = [(0.0, count, origin_id, None, [])]

        transfer_penalty = 4.0 if preference == "least_transfers" else 2.5

        while pq:
            cost, _, u, last_mode, path = heapq.heappop(pq)

            if u == destination_id:
                return self._format_itinerary(origin_id, destination_id, path)

            if u in best_cost and best_cost[u] <= cost:
                continue
            best_cost[u] = cost

            for edge in self.graph.get(u, []):
                v = edge["to"]
                edge_mode = edge["mode"]

                # Calculate edge weight based on user optimization preference
                if preference == "cheapest":
                    edge_weight = edge["fare"] + (edge["duration"] * 0.1)
                elif preference == "greenest":
                    eco_penalty = {"walk": 0.0, "water_metro": 0.5, "metro": 1.0, "bus": 3.0}
                    edge_weight = edge["duration"] + (eco_penalty.get(edge_mode, 2.0) * edge["distance"])
                else:  # fastest / least_transfers
                    edge_weight = edge["duration"]
                    # Add mode transfer penalty if switching transit modes
                    if last_mode and edge_mode != last_mode and edge_mode != "walk" and last_mode != "walk":
                        edge_weight += transfer_penalty

                new_cost = cost + edge_weight
                if v not in best_cost or new_cost < best_cost[v]:
                    count += 1
                    heapq.heappush(pq, (new_cost, count, v, edge_mode, path + [edge | {"from": u}]))

        return None

    def find_all_routes(self, origin_id: str, destination_id: str) -> List[Dict[str, Any]]:
        """Calculates distinct route options (Fastest, Cheapest, Greenest, Minimum Transfers)."""
        if origin_id not in self.stops or destination_id not in self.stops:
            return []

        options = []
        seen_keys = set()

        preferences = [
            ("fastest", "Fastest Route", "Direct & fastest travel time"),
            ("cheapest", "Cheapest Route", "Lowest total fare cost"),
            ("greenest", "Greenest Eco Route", "Minimizes carbon footprint"),
            ("least_transfers", "Minimum Transfers Route", "Minimizes mode switches")
        ]

        for pref_code, title, desc in preferences:
            itinerary = self.find_shortest_path(origin_id, destination_id, preference=pref_code)
            if itinerary and itinerary.get("legs"):
                path_key = tuple((leg["mode"], leg["from_stop"]["id"], leg["to_stop"]["id"]) for leg in itinerary["legs"])
                if path_key not in seen_keys:
                    seen_keys.add(path_key)
                    itinerary["option_id"] = len(options) + 1
                    itinerary["title"] = f"Option {len(options) + 1}: {title}"
                    itinerary["description"] = desc
                    itinerary["preference_type"] = pref_code
                    options.append(itinerary)

        return options

    def find_nearest_stop(self, lat: float, lon: float) -> Optional[Stop]:
        """Finds the nearest transit stop to a given (lat, lon) coordinate using Haversine distance."""
        best_stop, min_dist = None, float("inf")
        for s in self.stops.values():
            d = haversine_km(lat, lon, s.lat, s.lon)
            if d < min_dist:
                min_dist, best_stop = d, s
        return best_stop

    def find_all_routes_for_points(
        self,
        origin_id: Optional[str] = None,
        destination_id: Optional[str] = None,
        origin_lat: Optional[float] = None,
        origin_lon: Optional[float] = None,
        origin_name: Optional[str] = None,
        dest_lat: Optional[float] = None,
        dest_lon: Optional[float] = None,
        dest_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Handles route calculation between station IDs or arbitrary map click coordinates."""
        start_stop_id = origin_id
        custom_origin = None
        orig_lat, orig_lon = origin_lat, origin_lon
        orig_label = origin_name or "Start Location"

        if origin_lat is not None and origin_lon is not None:
            near_stop = self.find_nearest_stop(origin_lat, origin_lon)
            if near_stop:
                start_stop_id = near_stop.id
                custom_origin = {"id": "START_POINT", "name": orig_label, "lat": origin_lat, "lon": origin_lon, "mode": "walk"}
        elif start_stop_id in self.stops:
            s = self.stops[start_stop_id]
            orig_lat, orig_lon, orig_label = s.lat, s.lon, s.name

        target_stop_id = destination_id
        custom_dest = None
        dest_l_lat, dest_l_lon = dest_lat, dest_lon
        dest_label = dest_name or "Destination Location"

        if dest_lat is not None and dest_lon is not None:
            near_stop = self.find_nearest_stop(dest_lat, dest_lon)
            if near_stop:
                target_stop_id = near_stop.id
                custom_dest = {"id": "DEST_POINT", "name": dest_label, "lat": dest_lat, "lon": dest_lon, "mode": "walk"}
        elif target_stop_id in self.stops:
            s = self.stops[target_stop_id]
            dest_l_lat, dest_l_lon, dest_label = s.lat, s.lon, s.name

        # Calculate primary transit options
        options = []
        if start_stop_id and target_stop_id:
            options = self.find_all_routes(start_stop_id, target_stop_id)

        # Enhance options by attaching walk legs if custom start/end points exist
        enhanced = []
        for opt in options:
            enhanced.append(self._attach_custom_endpoints(dict(opt), custom_origin, custom_dest))

        # Check for direct walking option if distance is short
        if orig_lat and orig_lon and dest_l_lat and dest_l_lon:
            direct_dist = haversine_km(orig_lat, orig_lon, dest_l_lat, dest_l_lon)
            if direct_dist <= 1.5 or not enhanced:
                walk_dur = round((direct_dist / 4.5) * 60, 1)
                orig_info = custom_origin or (self.stops[origin_id].to_dict() if origin_id in self.stops else {"id": "START", "name": orig_label, "lat": orig_lat, "lon": orig_lon, "mode": "walk"})
                dest_info = custom_dest or (self.stops[destination_id].to_dict() if destination_id in self.stops else {"id": "DEST", "name": dest_label, "lat": dest_l_lat, "lon": dest_l_lon, "mode": "walk"})
                walk_opt = {
                    "origin": orig_info,
                    "destination": dest_info,
                    "total_duration_min": walk_dur,
                    "total_distance_km": round(direct_dist, 2),
                    "total_fare": 0.0,
                    "modes": ["walk"],
                    "transfer_count": 0,
                    "legs": [{
                        "step": 1,
                        "from_stop": orig_info,
                        "to_stop": dest_info,
                        "mode": "walk",
                        "route_name": "Direct Walk",
                        "duration_min": walk_dur,
                        "distance_km": round(direct_dist, 2),
                        "fare": 0.0,
                        "intermediate_stops_count": 0,
                        "instruction": f"Direct walk {round(direct_dist, 2)}km from {orig_label} to {dest_label}",
                        "geometry": [[orig_lat, orig_lon], [dest_l_lat, dest_l_lon]]
                    }],
                    "route_polyline": [[orig_lat, orig_lon], [dest_l_lat, dest_l_lon]],
                    "title": "Option 1: Direct Walk",
                    "description": "Short walking distance (No transit required)",
                    "preference_type": "walk"
                }
                enhanced.insert(0, walk_opt)

        for idx, opt in enumerate(enhanced):
            opt["option_id"] = idx + 1
            raw_title = opt.get("title", "Alternative Route")
            if "Option" in raw_title:
                raw_title = raw_title.split(":", 1)[-1].strip()
            opt["title"] = f"Option {idx + 1}: {raw_title}"

        return enhanced

    def _attach_custom_endpoints(
        self,
        itinerary: Dict[str, Any],
        custom_origin: Optional[Dict[str, Any]],
        custom_dest: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Prepends/appends walking legs when user picks arbitrary map points instead of fixed stations."""
        if not itinerary or not itinerary.get("legs"):
            return itinerary

        legs = list(itinerary.get("legs", []))
        polyline = list(itinerary.get("route_polyline", []))
        total_duration = itinerary.get("total_duration_min", 0.0)
        total_distance = itinerary.get("total_distance_km", 0.0)

        if custom_origin:
            first_stop = legs[0]["from_stop"]
            dist_km = haversine_km(custom_origin["lat"], custom_origin["lon"], first_stop["lat"], first_stop["lon"])
            if dist_km >= 0.03:
                dur_min = round((dist_km / 4.5) * 60, 1)
                walk_leg = {
                    "step": 0,
                    "from_stop": custom_origin,
                    "to_stop": first_stop,
                    "mode": "walk",
                    "route_name": "Walk to Station",
                    "duration_min": dur_min,
                    "distance_km": round(dist_km, 2),
                    "fare": 0.0,
                    "intermediate_stops_count": 0,
                    "instruction": f"Walk {int(dist_km * 1000)}m from {custom_origin['name']} to {first_stop['name']}",
                    "geometry": [[custom_origin["lat"], custom_origin["lon"]], [first_stop["lat"], first_stop["lon"]]]
                }
                legs.insert(0, walk_leg)
                polyline = [[custom_origin["lat"], custom_origin["lon"]]] + polyline
                total_duration += dur_min
                total_distance += dist_km
            itinerary["origin"] = custom_origin

        if custom_dest:
            last_stop = legs[-1]["to_stop"]
            dist_km = haversine_km(last_stop["lat"], last_stop["lon"], custom_dest["lat"], custom_dest["lon"])
            if dist_km >= 0.03:
                dur_min = round((dist_km / 4.5) * 60, 1)
                walk_leg = {
                    "step": len(legs) + 1,
                    "from_stop": last_stop,
                    "to_stop": custom_dest,
                    "mode": "walk",
                    "route_name": "Walk to Destination",
                    "duration_min": dur_min,
                    "distance_km": round(dist_km, 2),
                    "fare": 0.0,
                    "intermediate_stops_count": 0,
                    "instruction": f"Walk {int(dist_km * 1000)}m from {last_stop['name']} to {custom_dest['name']}",
                    "geometry": [[last_stop["lat"], last_stop["lon"]], [custom_dest["lat"], custom_dest["lon"]]]
                }
                legs.append(walk_leg)
                polyline = polyline + [[custom_dest["lat"], custom_dest["lon"]]]
                total_duration += dur_min
                total_distance += dist_km
            itinerary["destination"] = custom_dest

        for idx, leg in enumerate(legs):
            leg["step"] = idx + 1

        itinerary["legs"] = legs
        itinerary["route_polyline"] = polyline
        itinerary["total_duration_min"] = round(total_duration, 1)
        itinerary["total_distance_km"] = round(total_distance, 2)
        return itinerary

    def _format_itinerary(self, origin_id: str, dest_id: str, path: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Consolidates consecutive edges of the same transit line into readable itinerary legs."""
        if not path:
            return None

        # Group consecutive edges sharing the same mode and route_id
        grouped_legs = []
        current_group = []
        for edge in path:
            if not current_group:
                current_group.append(edge)
            else:
                last_edge = current_group[-1]
                if edge["mode"] == last_edge["mode"] and edge["route_id"] == last_edge["route_id"]:
                    current_group.append(edge)
                else:
                    grouped_legs.append(current_group)
                    current_group = [edge]
        if current_group:
            grouped_legs.append(current_group)

        legs = []
        total_duration, total_distance, total_fare = 0.0, 0.0, 0.0
        all_coords, modes_used = [], set()

        for idx, group in enumerate(grouped_legs):
            first_edge, last_edge = group[0], group[-1]
            from_s, to_s = self.stops[first_edge["from"]], self.stops[last_edge["to"]]

            mode = first_edge["mode"]
            route = self.routes.get(first_edge["route_id"])
            route_name = route.short_name if route else ("Walking Transfer" if mode == "walk" else "Transit")

            dur = sum(e["duration"] for e in group)
            dist = sum(e["distance"] for e in group)
            fare = sum(e["fare"] for e in group)
            stop_cnt = len(group)

            total_duration += dur
            total_distance += dist
            total_fare += fare
            modes_used.add(mode)

            group_geom = []
            for e in group:
                geom = e.get("geometry", [[self.stops[e["from"]].lat, self.stops[e["from"]].lon], [self.stops[e["to"]].lat, self.stops[e["to"]].lon]])
                group_geom.extend(geom)
                all_coords.extend(geom)

            # Build human-readable step instruction
            if mode == "walk":
                instruction = f"Walk {int(dist * 1000)}m from {from_s.name} to {to_s.name}"
            elif mode == "metro":
                s_txt = f" ({stop_cnt} stops)" if stop_cnt > 1 else ""
                instruction = f"Take Kochi Metro ({route_name}) from {from_s.name} to {to_s.name}{s_txt}"
            elif mode == "water_metro":
                s_txt = f" ({stop_cnt} stops)" if stop_cnt > 1 else ""
                instruction = f"Take Water Metro Ferry ({route_name}) from {from_s.name} to {to_s.name}{s_txt}"
            else:  # bus
                s_txt = f" ({stop_cnt} stops)" if stop_cnt > 1 else ""
                instruction = f"Take Feeder Bus ({route_name}) from {from_s.name} to {to_s.name}{s_txt}"

            legs.append({
                "step": idx + 1,
                "from_stop": from_s.to_dict(),
                "to_stop": to_s.to_dict(),
                "mode": mode,
                "route_name": route_name,
                "duration_min": round(dur, 1),
                "distance_km": round(dist, 2),
                "fare": round(fare, 2),
                "intermediate_stops_count": stop_cnt,
                "instruction": instruction,
                "geometry": group_geom
            })

        origin_s, dest_s = self.stops[origin_id], self.stops[dest_id]
        transit_legs = [l for l in legs if l["mode"] != "walk"]
        transfer_count = max(0, len(transit_legs) - 1)

        tot_dist = round(total_distance, 2)
        tot_fare = round(total_fare, 2)

        return {
            "origin": origin_s.to_dict(),
            "destination": dest_s.to_dict(),
            "total_duration_min": round(total_duration, 1),
            "total_distance_km": tot_dist,
            "total_fare": tot_fare,
            "kochi1_card_fare": round(tot_fare * 0.8, 2),
            "co2_saved_kg": round(tot_dist * 0.12, 2),
            "modes": list(modes_used),
            "transfer_count": transfer_count,
            "legs": legs,
            "route_polyline": all_coords
        }
