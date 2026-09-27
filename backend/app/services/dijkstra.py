import json
import heapq
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from ..db.models import Stop, Route, Edge

class MultimodalRouter:
    def __init__(self, db: Session):
        self.db = db
        self.stops = {s.id: s for s in db.query(Stop).all()}
        self.routes = {r.id: r for r in db.query(Route).all()}
        self.graph = self._build_graph()

    def _build_graph(self) -> Dict[str, List[Dict[str, Any]]]:
        adj: Dict[str, List[Dict[str, Any]]] = {sid: [] for sid in self.stops}
        edges = self.db.query(Edge).all()
        for e in edges:
            if e.from_stop_id in adj and e.to_stop_id in self.stops:
                geom = []
                if e.geometry:
                    try:
                        geom = json.loads(e.geometry)
                    except:
                        pass
                if not geom:
                    s1 = self.stops[e.from_stop_id]
                    s2 = self.stops[e.to_stop_id]
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
        preference: str = "fastest" # 'fastest', 'cheapest', 'least_transfers'
    ) -> Optional[Dict[str, Any]]:
        """
        Executes Multimodal Dijkstra's Algorithm from origin to destination.
        Applies mode switch penalties and dynamic weight optimization.
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

        # Priority Queue: (weight, count, current_stop_id, current_mode, path_edges)
        TRANSFER_PENALTY_MIN = 4.0 if preference == "least_transfers" else 2.5
        
        best_cost: Dict[str, float] = {}
        count = 0
        pq = [(0.0, count, origin_id, None, [])]

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
                
                # Weight calculation
                if preference == "cheapest":
                    edge_weight = edge["fare"] + (edge["duration"] * 0.1)
                elif preference == "greenest":
                    # Greenest prioritizes lowest carbon footprint (walk=0, water_metro/metro=low, bus=moderate)
                    mode_eco_penalty = {"walk": 0.0, "water_metro": 0.5, "metro": 1.0, "bus": 3.0}
                    edge_weight = edge["duration"] + (mode_eco_penalty.get(edge_mode, 2.0) * edge["distance"])
                else: # fastest or least_transfers
                    edge_weight = edge["duration"]
                    # Add penalty when switching between different public transit modes
                    if last_mode and edge_mode != last_mode and edge_mode != "walk" and last_mode != "walk":
                        edge_weight += TRANSFER_PENALTY_MIN

                new_cost = cost + edge_weight
                if v not in best_cost or new_cost < best_cost[v]:
                    count += 1
                    heapq.heappush(pq, (new_cost, count, v, edge_mode, path + [edge | {"from": u}]))

        return None

    def find_nearest_stop(self, lat: float, lon: float) -> Optional[Stop]:
        import math
        def haversine(lat1, lon1, lat2, lon2):
            R = 6371.0
            dlat = math.radians(lat2 - lat1)
            dlon = math.radians(lon2 - lon1)
            a = (math.sin(dlat / 2) ** 2 +
                 math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
                 math.sin(dlon / 2) ** 2)
            return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        best_stop = None
        min_dist = float('inf')
        for s in self.stops.values():
            d = haversine(lat, lon, s.lat, s.lon)
            if d < min_dist:
                min_dist = d
                best_stop = s
        return best_stop

    def _attach_custom_endpoints(
        self,
        itinerary: Dict[str, Any],
        custom_origin: Optional[Dict[str, Any]],
        custom_dest: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        if not itinerary:
            return itinerary

        import math
        def haversine(lat1, lon1, lat2, lon2):
            R = 6371.0
            dlat = math.radians(lat2 - lat1)
            dlon = math.radians(lon2 - lon1)
            a = (math.sin(dlat / 2) ** 2 +
                 math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
                 math.sin(dlon / 2) ** 2)
            return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        legs = list(itinerary.get("legs", []))
        route_polyline = list(itinerary.get("route_polyline", []))
        total_duration = itinerary.get("total_duration_min", 0.0)
        total_distance = itinerary.get("total_distance_km", 0.0)

        # Prepend origin walk leg if custom origin
        if custom_origin and legs:
            first_stop = legs[0]["from_stop"]
            dist_km = haversine(custom_origin["lat"], custom_origin["lon"], first_stop["lat"], first_stop["lon"])
            if dist_km >= 0.03:
                duration_min = round((dist_km / 4.5) * 60, 1)
                walk_leg = {
                    "step": 0,
                    "from_stop": {
                        "id": custom_origin["id"],
                        "name": custom_origin["name"],
                        "lat": custom_origin["lat"],
                        "lon": custom_origin["lon"],
                        "mode": "walk"
                    },
                    "to_stop": first_stop,
                    "mode": "walk",
                    "route_name": "Walk to Station",
                    "duration_min": duration_min,
                    "distance_km": round(dist_km, 2),
                    "fare": 0.0,
                    "intermediate_stops_count": 0,
                    "instruction": f"Walk {int(dist_km * 1000)}m from {custom_origin['name']} to {first_stop['name']}",
                    "geometry": [[custom_origin["lat"], custom_origin["lon"]], [first_stop["lat"], first_stop["lon"]]]
                }
                legs.insert(0, walk_leg)
                route_polyline = [[custom_origin["lat"], custom_origin["lon"]]] + route_polyline
                total_duration += duration_min
                total_distance += dist_km
            itinerary["origin"] = custom_origin

        # Append dest walk leg if custom dest
        if custom_dest and legs:
            last_stop = legs[-1]["to_stop"]
            dist_km = haversine(last_stop["lat"], last_stop["lon"], custom_dest["lat"], custom_dest["lon"])
            if dist_km >= 0.03:
                duration_min = round((dist_km / 4.5) * 60, 1)
                walk_leg = {
                    "step": len(legs) + 1,
                    "from_stop": last_stop,
                    "to_stop": {
                        "id": custom_dest["id"],
                        "name": custom_dest["name"],
                        "lat": custom_dest["lat"],
                        "lon": custom_dest["lon"],
                        "mode": "walk"
                    },
                    "mode": "walk",
                    "route_name": "Walk to Destination",
                    "duration_min": duration_min,
                    "distance_km": round(dist_km, 2),
                    "fare": 0.0,
                    "intermediate_stops_count": 0,
                    "instruction": f"Walk {int(dist_km * 1000)}m from {last_stop['name']} to {custom_dest['name']}",
                    "geometry": [[last_stop["lat"], last_stop["lon"]], [custom_dest["lat"], custom_dest["lon"]]]
                }
                legs.append(walk_leg)
                route_polyline = route_polyline + [[custom_dest["lat"], custom_dest["lon"]]]
                total_duration += duration_min
                total_distance += dist_km
            itinerary["destination"] = custom_dest

        # Re-index leg step numbers
        for idx, leg in enumerate(legs):
            leg["step"] = idx + 1

        itinerary["legs"] = legs
        itinerary["route_polyline"] = route_polyline
        itinerary["total_duration_min"] = round(total_duration, 1)
        itinerary["total_distance_km"] = round(total_distance, 2)

        return itinerary

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
        import math
        def haversine(lat1, lon1, lat2, lon2):
            R = 6371.0
            dlat = math.radians(lat2 - lat1)
            dlon = math.radians(lon2 - lon1)
            a = (math.sin(dlat / 2) ** 2 +
                 math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
                 math.sin(dlon / 2) ** 2)
            return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        # Determine exact origin coords & name
        orig_lat, orig_lon, orig_n = None, None, None
        start_stop_id = origin_id
        custom_origin = None

        if origin_lat is not None and origin_lon is not None:
            orig_lat, orig_lon = origin_lat, origin_lon
            orig_n = origin_name or f"Point ({origin_lat:.4f}, {origin_lon:.4f})"
            near_stop = self.find_nearest_stop(origin_lat, origin_lon)
            if near_stop:
                start_stop_id = near_stop.id
                custom_origin = {
                    "id": f"POINT_{round(origin_lat,4)}_{round(origin_lon,4)}",
                    "name": orig_n,
                    "lat": origin_lat,
                    "lon": origin_lon,
                    "mode": "walk"
                }
        elif start_stop_id and start_stop_id in self.stops:
            s = self.stops[start_stop_id]
            orig_lat, orig_lon, orig_n = s.lat, s.lon, s.name
        elif start_stop_id and "," in start_stop_id:
            try:
                parts = start_stop_id.split(",")
                plat, plon = float(parts[0]), float(parts[1])
                orig_lat, orig_lon = plat, plon
                orig_n = origin_name or f"Point ({plat:.4f}, {plon:.4f})"
                near_stop = self.find_nearest_stop(plat, plon)
                if near_stop:
                    start_stop_id = near_stop.id
                    custom_origin = {
                        "id": f"POINT_{round(plat,4)}_{round(plon,4)}",
                        "name": orig_n,
                        "lat": plat,
                        "lon": plon,
                        "mode": "walk"
                    }
            except Exception:
                pass

        # Determine exact destination coords & name
        dest_l_lat, dest_l_lon, dest_n = None, None, None
        target_stop_id = destination_id
        custom_dest = None

        if dest_lat is not None and dest_lon is not None:
            dest_l_lat, dest_l_lon = dest_lat, dest_lon
            dest_n = dest_name or f"Point ({dest_lat:.4f}, {dest_lon:.4f})"
            near_stop = self.find_nearest_stop(dest_lat, dest_lon)
            if near_stop:
                target_stop_id = near_stop.id
                custom_dest = {
                    "id": f"POINT_{round(dest_lat,4)}_{round(dest_lon,4)}",
                    "name": dest_n,
                    "lat": dest_lat,
                    "lon": dest_lon,
                    "mode": "walk"
                }
        elif target_stop_id and target_stop_id in self.stops:
            s = self.stops[target_stop_id]
            dest_l_lat, dest_l_lon, dest_n = s.lat, s.lon, s.name
        elif target_stop_id and "," in target_stop_id:
            try:
                parts = target_stop_id.split(",")
                plat, plon = float(parts[0]), float(parts[1])
                dest_l_lat, dest_l_lon = plat, plon
                dest_n = dest_name or f"Point ({dest_lat:.4f}, {dest_lon:.4f})"
                near_stop = self.find_nearest_stop(plat, plon)
                if near_stop:
                    target_stop_id = near_stop.id
                    custom_dest = {
                        "id": f"POINT_{round(dest_lat,4)}_{round(dest_lon,4)}",
                        "name": dest_n,
                        "lat": plat,
                        "lon": plon,
                        "mode": "walk"
                    }
            except Exception:
                pass

        # Compute direct walk option if coordinates exist
        direct_walk_opt = None
        if orig_lat is not None and orig_lon is not None and dest_l_lat is not None and dest_l_lon is not None:
            direct_dist_km = haversine(orig_lat, orig_lon, dest_l_lat, dest_l_lon)
            direct_walk_min = round((direct_dist_km / 4.5) * 60, 1)

            orig_info = custom_origin or (self.stops[origin_id].to_dict() if origin_id in self.stops else {
                "id": f"POINT_{round(orig_lat,4)}_{round(orig_lon,4)}",
                "name": orig_n, "lat": orig_lat, "lon": orig_lon, "mode": "walk"
            })
            dest_info = custom_dest or (self.stops[destination_id].to_dict() if destination_id in self.stops else {
                "id": f"POINT_{round(dest_l_lat,4)}_{round(dest_l_lon,4)}",
                "name": dest_n, "lat": dest_l_lat, "lon": dest_l_lon, "mode": "walk"
            })

            walk_instruction = (
                f"Walk direct {int(direct_dist_km * 1000)}m to {dest_n}"
                if direct_dist_km < 1.0 else
                f"Walk direct {round(direct_dist_km, 2)}km to {dest_n} (No transport needed)"
            )

            direct_walk_opt = {
                "origin": orig_info,
                "destination": dest_info,
                "total_duration_min": direct_walk_min,
                "total_distance_km": round(direct_dist_km, 2),
                "total_fare": 0.0,
                "modes": ["walk"],
                "transfer_count": 0,
                "legs": [{
                    "step": 1,
                    "from_stop": orig_info,
                    "to_stop": dest_info,
                    "mode": "walk",
                    "route_name": "Direct Walk",
                    "duration_min": direct_walk_min,
                    "distance_km": round(direct_dist_km, 2),
                    "fare": 0.0,
                    "intermediate_stops_count": 0,
                    "instruction": walk_instruction,
                    "geometry": [[orig_lat, orig_lon], [dest_l_lat, dest_l_lon]]
                }],
                "route_polyline": [[orig_lat, orig_lon], [dest_l_lat, dest_l_lon]],
                "title": "Direct Walk Route",
                "description": f"Direct walking route ({round(direct_dist_km, 2)} km, ₹0 fare)",
                "preference_type": "walk"
            }

        options = []
        if start_stop_id and target_stop_id:
            options = self.find_all_routes(start_stop_id, target_stop_id)

        enhanced_options = []
        for opt in options:
            enhanced_opt = self._attach_custom_endpoints(dict(opt), custom_origin, custom_dest)
            enhanced_options.append(enhanced_opt)

        if direct_walk_opt:
            direct_dist = direct_walk_opt["total_distance_km"]
            direct_dur = direct_walk_opt["total_duration_min"]
            transit_best_dur = enhanced_options[0]["total_duration_min"] if enhanced_options else float('inf')

            # If direct walk is shorter/faster or <= 1.5km, make it Option 1
            if direct_dist <= 1.5 or direct_dur <= transit_best_dur or not enhanced_options:
                direct_walk_opt["title"] = "Direct Walk (Shortest Distance)"
                enhanced_options.insert(0, direct_walk_opt)
            elif direct_dist <= 12.0:
                direct_walk_opt["title"] = "Direct Walk Route (Zero Fare)"
                enhanced_options.append(direct_walk_opt)

        if not enhanced_options and direct_walk_opt:
            enhanced_options.append(direct_walk_opt)

        # Re-index option IDs & titles
        for idx, opt in enumerate(enhanced_options):
            opt["option_id"] = idx + 1
            raw_title = opt.get("title", "Alternative Route")
            if raw_title.startswith("Option "):
                raw_title = raw_title.split(":", 1)[-1].strip()
            opt["title"] = f"Option {idx + 1}: {raw_title}"

        return enhanced_options


    def find_all_routes(self, origin_id: str, destination_id: str) -> List[Dict[str, Any]]:
        """
        Calculates all viable alternative routes (Fastest, Cheapest, Least Transfers,
        and distinct alternative mode combinations) between origin and destination.
        """
        if origin_id not in self.stops or destination_id not in self.stops:
            return []

        options = []
        seen_path_keys = set()
        used_edges_set = set()

        def add_option(itinerary, title, desc, pref_type):
            if itinerary and itinerary.get("legs"):
                path_key = tuple((leg["mode"], leg["from_stop"]["id"], leg["to_stop"]["id"]) for leg in itinerary["legs"])
                if path_key not in seen_path_keys:
                    seen_path_keys.add(path_key)
                    itinerary["option_id"] = len(options) + 1
                    itinerary["title"] = f"Option {len(options) + 1}: {title}"
                    itinerary["description"] = desc
                    itinerary["preference_type"] = pref_type
                    options.append(itinerary)
                    for leg in itinerary["legs"]:
                        used_edges_set.add((leg["from_stop"]["id"], leg["to_stop"]["id"]))
                    return True
            return False

        # 1. Primary Preferences
        add_option(self.find_shortest_path(origin_id, destination_id, preference="fastest"), "Fastest Route", "Direct & fastest travel time", "fastest")
        add_option(self.find_shortest_path(origin_id, destination_id, preference="cheapest"), "Cheapest Route", "Lowest total fare cost", "cheapest")
        add_option(self.find_shortest_path(origin_id, destination_id, preference="greenest"), "Greenest Eco Route", "Minimizes carbon footprint", "greenest")
        add_option(self.find_shortest_path(origin_id, destination_id, preference="least_transfers"), "Minimum Transfers Route", "Minimizes mode switches", "least_transfers")

        # 2. Mode Diversity Search (Penalize each primary mode used in initial paths)
        modes_to_penalize = set()
        for opt in list(options):
            for mode in opt.get("modes", []):
                if mode != "walk":
                    modes_to_penalize.add(mode)

        for mode in modes_to_penalize:
            alt_itinerary = self.find_penalized_alternative(origin_id, destination_id, penalize_mode=mode)
            mode_label = mode.replace('_', ' ').capitalize()
            add_option(alt_itinerary, f"Alternative (Non-{mode_label}) Route", f"Bypasses main {mode_label} corridor", "alternative")

        # 3. K-Shortest Path Edge-Penalty Search (Discover up to 5 total unique viable routes)
        penalty_weights = [15.0, 30.0, 50.0]
        for penalty in penalty_weights:
            if len(options) >= 5:
                break
            k_itinerary = self.find_edge_penalized_path(origin_id, destination_id, penalized_edges=used_edges_set, penalty=penalty)
            add_option(k_itinerary, "Alternative Transit Route", "Alternative transit & transfer combination", "alternative")

        return options

    def find_penalized_alternative(self, origin_id: str, destination_id: str, penalize_mode: str) -> Optional[Dict[str, Any]]:
        """
        Calculates a route while penalizing the primary mode to force alternative transport options.
        """
        best_cost: Dict[str, float] = {}
        count = 0
        pq = [(0.0, count, origin_id, None, [])]

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
                edge_weight = edge["duration"]

                if edge_mode == penalize_mode:
                    edge_weight += 20.0  # Artificial penalty to discover alternative modes

                new_cost = cost + edge_weight
                if v not in best_cost or new_cost < best_cost[v]:
                    count += 1
                    heapq.heappush(pq, (new_cost, count, v, edge_mode, path + [edge | {"from": u}]))

        return None

    def find_edge_penalized_path(
        self,
        origin_id: str,
        destination_id: str,
        penalized_edges: set,
        penalty: float = 20.0
    ) -> Optional[Dict[str, Any]]:
        """
        Runs Dijkstra with a penalty on previously used edges to uncover distinct alternative paths.
        """
        best_cost: Dict[str, float] = {}
        count = 0
        pq = [(0.0, count, origin_id, None, [])]

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
                edge_weight = edge["duration"]

                if (u, v) in penalized_edges:
                    edge_weight += penalty

                new_cost = cost + edge_weight
                if v not in best_cost or new_cost < best_cost[v]:
                    count += 1
                    heapq.heappush(pq, (new_cost, count, v, edge_mode, path + [edge | {"from": u}]))

        return None

    def _format_itinerary(self, origin_id: str, dest_id: str, path: List[Dict[str, Any]]) -> Dict[str, Any]:
        total_duration = 0.0
        total_distance = 0.0
        total_fare = 0.0
        all_coords = []
        modes_used = set()

        if not path:
            return None

        # Group consecutive edges with the same mode and route_id
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
        for idx, group in enumerate(grouped_legs):
            first_edge = group[0]
            last_edge = group[-1]
            from_s = self.stops[first_edge["from"]]
            to_s = self.stops[last_edge["to"]]

            mode = first_edge["mode"]
            route_id = first_edge["route_id"]
            route = self.routes.get(route_id)
            route_name = route.short_name if route else ("Walking Transfer" if mode == "walk" else "Transit")

            group_duration = sum(e["duration"] for e in group)
            group_distance = sum(e["distance"] for e in group)
            group_fare = sum(e["fare"] for e in group)
            group_stops_count = len(group)

            total_duration += group_duration
            total_distance += group_distance
            total_fare += group_fare
            modes_used.add(mode)

            # Combine geometry for entire leg
            group_geom = []
            for e in group:
                geom = e.get("geometry", [[self.stops[e["from"]].lat, self.stops[e["from"]].lon], [self.stops[e["to"]].lat, self.stops[e["to"]].lon]])
                group_geom.extend(geom)
                all_coords.extend(geom)

            # Human-readable consolidated instruction
            if mode == "walk":
                instruction = f"Walk {int(group_distance * 1000)}m to {to_s.name}"
            elif mode == "metro":
                stop_str = f" ({group_stops_count} stops)" if group_stops_count > 1 else ""
                instruction = f"Board Kochi Metro ({route_name}) at {from_s.name} to {to_s.name}{stop_str}"
            elif mode == "water_metro":
                stop_str = f" ({group_stops_count} stops)" if group_stops_count > 1 else ""
                instruction = f"Board Water Metro Ferry ({route_name}) from {from_s.name} to {to_s.name}{stop_str}"
            else: # bus
                stop_str = f" ({group_stops_count} stops)" if group_stops_count > 1 else ""
                instruction = f"Take Feeder Bus ({route_name}) from {from_s.name} to {to_s.name}{stop_str}"

            legs.append({
                "step": idx + 1,
                "from_stop": from_s.to_dict(),
                "to_stop": to_s.to_dict(),
                "mode": mode,
                "route_name": route_name,
                "duration_min": round(group_duration, 1),
                "distance_km": round(group_distance, 2),
                "fare": round(group_fare, 2),
                "intermediate_stops_count": group_stops_count,
                "instruction": instruction,
                "geometry": group_geom
            })

        origin_s = self.stops[origin_id]
        dest_s = self.stops[dest_id]

        transfer_count = max(0, len([l for l in legs if l["mode"] != "walk"]) - 1)
        tot_dist = round(total_distance, 2)
        tot_fare = round(total_fare, 2)
        co2_saved = round(tot_dist * 0.12, 2)
        kochi1_fare = round(tot_fare * 0.8, 2)

        return {
            "origin": origin_s.to_dict(),
            "destination": dest_s.to_dict(),
            "total_duration_min": round(total_duration, 1),
            "total_distance_km": tot_dist,
            "total_fare": tot_fare,
            "kochi1_card_fare": kochi1_fare,
            "co2_saved_kg": co2_saved,
            "car_emissions_kg": round(tot_dist * 0.14, 2),
            "modes": list(modes_used),
            "transfer_count": transfer_count,
            "legs": legs,
            "route_polyline": all_coords
        }
