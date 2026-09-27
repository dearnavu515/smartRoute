import os
import csv
import json
import math
import zipfile
import xml.etree.ElementTree as ET
from sqlalchemy.orm import Session
from ..db.database import SessionLocal, engine, Base
from ..db.models import Stop, Route, Edge, FareRule

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates distance in kilometers between two lat/lon coordinates."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def read_xlsx_sheet(xlsx_path: str, sheet_idx: int = 1):
    """Simple XML-based XLSX reader (reads rows without needing heavy external dependencies)."""
    z = zipfile.ZipFile(xlsx_path)
    shared = []
    if 'xl/sharedStrings.xml' in z.namelist():
        tree = ET.fromstring(z.read('xl/sharedStrings.xml'))
        for si in tree.iter('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}si'):
            shared.append(''.join(t.text for t in si.iter('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t') if t.text))
    
    sheet_file = f'xl/worksheets/sheet{sheet_idx}.xml'
    if sheet_file not in z.namelist():
        return []
    
    tree = ET.fromstring(z.read(sheet_file))
    rows = []
    for row in tree.iter('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}row'):
        row_vals = []
        for c in row.iter('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c'):
            t, v = c.attrib.get('t'), c.find('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}v')
            val = ''
            if v is not None and v.text is not None:
                val = v.text
                if t == 's' and val.isdigit() and int(val) < len(shared):
                    val = shared[int(val)]
            row_vals.append(val)
        if any(row_vals):
            rows.append(row_vals)
    return rows

def ingest_all(db: Session):
    """
    Ingests official transit datasets (Kochi Metro GTFS, Water Metro, Feeder Buses)
    and constructs the spatial multimodal transit graph in SQLite.
    """
    print("Re-creating database tables...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    # =========================================================================
    # STEP 1: INGEST KOCHI METRO (KMRL) FROM GTFS ZIP
    # =========================================================================
    metro_zip = next((os.path.join(PROJECT_ROOT, f) for f in os.listdir(PROJECT_ROOT) if f.startswith("kochi metro") and f.endswith(".zip")), None)
    metro_stops_map = {}
    metro_stop_sequence = []

    if metro_zip and os.path.exists(metro_zip):
        print(f"Ingesting KMRL GTFS Feed: {os.path.basename(metro_zip)}")
        with zipfile.ZipFile(metro_zip, 'r') as z:
            stops_file = [f for f in z.namelist() if f.endswith('stops.txt')][0]
            reader = csv.DictReader(z.read(stops_file).decode('utf-8', errors='replace').splitlines())
            for row in reader:
                stop_id = f"KMRL_{row['stop_id']}"
                s = Stop(
                    id=stop_id,
                    name=f"{row['stop_name'].strip()} Metro",
                    lat=float(row['stop_lat']),
                    lon=float(row['stop_lon']),
                    mode="metro",
                    agency="KMRL",
                    zone_id=row.get('zone_id', '')
                )
                db.add(s)
                metro_stops_map[row['stop_id']] = s

            db.add(Route(
                id="KMRL_L1",
                short_name="Metro Line 1",
                long_name="Aluva to Thripunithura",
                mode="metro",
                agency="KMRL",
                color="#1E40AF"
            ))

            st_file = [f for f in z.namelist() if f.endswith('stop_times.txt')][0]
            st_reader = csv.DictReader(z.read(st_file).decode('utf-8', errors='replace').splitlines())
            trip_stops = {}
            for row in st_reader:
                tid = row['trip_id']
                trip_stops.setdefault(tid, []).append((int(row['stop_sequence']), row['stop_id']))

            longest_trip = max(trip_stops.values(), key=len)
            longest_trip.sort(key=lambda x: x[0])
            metro_stop_sequence = [item[1] for item in longest_trip]

        for i in range(len(metro_stop_sequence) - 1):
            s1_id, s2_id = metro_stop_sequence[i], metro_stop_sequence[i+1]
            if s1_id in metro_stops_map and s2_id in metro_stops_map:
                s1, s2 = metro_stops_map[s1_id], metro_stops_map[s2_id]
                dist = haversine_km(s1.lat, s1.lon, s2.lat, s2.lon)
                dur = round((dist / 36.0) * 60 + 0.5, 1) # Speed ~36km/h + dwell time
                geom = json.dumps([[s1.lat, s1.lon], [s2.lat, s2.lon]])

                # Forward & Backward Edges
                db.add(Edge(route_id="KMRL_L1", from_stop_id=s1.id, to_stop_id=s2.id, mode="metro", distance_km=round(dist, 2), duration_min=max(dur, 1.5), fare=10.0, geometry=geom))
                db.add(Edge(route_id="KMRL_L1", from_stop_id=s2.id, to_stop_id=s1.id, mode="metro", distance_km=round(dist, 2), duration_min=max(dur, 1.5), fare=10.0, geometry=geom))
        print(f"Successfully ingested {len(metro_stops_map)} Metro Stations.")

    # =========================================================================
    # STEP 2: INGEST KOCHI WATER METRO (KWML)
    # =========================================================================
    wm_path = os.path.join(PROJECT_ROOT, "FINIAL EXCEL COMPLETE 2nd version.xlsx")
    wm_stops_map = {}
    if os.path.exists(wm_path):
        print("Ingesting Water Metro (KWML) dataset...")
        stops_rows = read_xlsx_sheet(wm_path, sheet_idx=2)
        default_coords = {"S10": (9.9892, 76.2698), "S11": (10.0125, 76.2736), "S6": (9.9800, 76.3334)}

        header = [h.lower() for h in stops_rows[0]]
        id_idx, name_idx = header.index("stop_id"), header.index("stop_name")
        lat_idx = header.index("stop_lat") if "stop_lat" in header else -1
        lon_idx = header.index("stop_lon") if "stop_lon" in header else -1

        for r in stops_rows[1:]:
            if len(r) > max(id_idx, name_idx):
                sid, name = r[id_idx].strip(), r[name_idx].strip()
                lat = float(r[lat_idx]) if (lat_idx != -1 and len(r) > lat_idx and r[lat_idx]) else None
                lon = float(r[lon_idx]) if (lon_idx != -1 and len(r) > lon_idx and r[lon_idx]) else None
                
                if (not lat or not lon) and sid in default_coords:
                    lat, lon = default_coords[sid]
                
                if lat and lon:
                    stop_obj = Stop(id=f"WM_{sid}", name=f"{name} Water Metro", lat=lat, lon=lon, mode="water_metro", agency="KWML")
                    db.add(stop_obj)
                    wm_stops_map[sid] = stop_obj

        wm_routes_data = [
            ("WM_R1", "VYT-KKD", "Vyttila to Kakkanad", ["S1", "S6", "S2"]),
            ("WM_R2", "HCT-VYP-FKI", "High Court to Fort Kochi via Vypin", ["S7", "S5", "S8"]),
            ("WM_R3", "HCT-MAT-WLI", "High Court to Mattancherry & Willingdon", ["S7", "S13", "S9"]),
            ("WM_R4", "CRL-ELR-SCR-HCT", "Cheranalloor to High Court", ["S4", "S3", "S12", "S10", "S7"])
        ]

        for rid, sname, lname, seq in wm_routes_data:
            db.add(Route(id=rid, short_name=sname, long_name=lname, mode="water_metro", agency="KWML", color="#0D9488"))
            for i in range(len(seq) - 1):
                s1_id, s2_id = seq[i], seq[i+1]
                if s1_id in wm_stops_map and s2_id in wm_stops_map:
                    s1, s2 = wm_stops_map[s1_id], wm_stops_map[s2_id]
                    dist = haversine_km(s1.lat, s1.lon, s2.lat, s2.lon)
                    dur = round((dist / 15.0) * 60 + 2.0, 1) # Boat speed ~15km/h
                    geom = json.dumps([[s1.lat, s1.lon], [s2.lat, s2.lon]])

                    db.add(Edge(route_id=rid, from_stop_id=s1.id, to_stop_id=s2.id, mode="water_metro", distance_km=round(dist, 2), duration_min=max(dur, 4.0), fare=20.0, geometry=geom))
                    db.add(Edge(route_id=rid, from_stop_id=s2.id, to_stop_id=s1.id, mode="water_metro", distance_km=round(dist, 2), duration_min=max(dur, 4.0), fare=20.0, geometry=geom))
        print(f"Successfully ingested {len(wm_stops_map)} Water Metro Jetties.")

    # =========================================================================
    # STEP 3: INGEST FEEDER BUSES (Connecting Campuses, Infopark, Metro)
    # =========================================================================
    feeder_stops_def = [
        ("BUS_MUTTOM", "Muttom Bus Stop", 10.0725, 76.3331),
        ("BUS_KLMS_MS", "Kalamassery Municipal Stand", 10.0543, 76.3315),
        ("BUS_HMT", "HMT Junction", 10.0512, 76.3395),
        ("BUS_TOSHIBA", "Toshiba Junction", 10.0435, 76.3421),
        ("BUS_VALLATHOL", "Vallathol Junction", 10.0354, 76.3442),
        ("BUS_BMC", "Bharat Mata College", 10.0261, 76.3435),
        ("BUS_CIVIL_STN", "Kakkanad Civil Station", 10.0159, 76.3419),
        ("BUS_KKD_WM", "Kakkanad Water Metro Feeder Stop", 9.9930, 76.3520),
        ("BUS_INFOPARK_P1", "Infopark Phase 1 (Rajagiri Valley)", 10.0104, 76.3606),
        ("BUS_INFOPARK_P2", "Infopark Phase 2", 10.0028, 76.3689),
        ("BUS_RAJAGIRI", "Rajagiri College of Social Sciences / RSET", 10.0541, 76.3542),
        ("BUS_CUSAT", "CUSAT University Campus", 10.0441, 76.3275),
        ("BUS_MED_COLL", "Govt. Medical College Kalamassery", 10.0594, 76.3533),
        ("BUS_GOVT_ITI", "Govt. ITI Kalamassery", 10.0538, 76.3482),
        ("BUS_MG_METRO", "MG Road Feeder Bus Stop", 9.9835, 76.2824),
        ("BUS_HIGH_COURT", "High Court Feeder Stop", 9.9845, 76.2735),
        ("BUS_MENAKA", "Menaka Junction", 9.9782, 76.2778),
        ("BUS_EKM_JETTY", "Ernakulam Boat Jetty", 9.9712, 76.2798),
        ("BUS_SOUTH_MS", "Ernakulam South Bus Stop", 9.9675, 76.2892),
        ("BUS_KADAVANTHRA", "Kadavanthra Junction", 9.9682, 76.2995),
        ("BUS_SHIPYARD", "Cochin Shipyard", 9.9575, 76.2934),
        ("BUS_EDAP_JN", "Edappally Toll Bus Stop", 10.0245, 76.3090)
    ]

    feeder_stops_map = {}
    for sid, name, lat, lon in feeder_stops_def:
        s = Stop(id=sid, name=name, lat=lat, lon=lon, mode="bus", agency="FeederBus")
        db.add(s)
        feeder_stops_map[sid] = s

    feeder_routes = [
        ("BUS_R1", "KLM-INFO", "Kalamassery to Infopark Express", ["BUS_MUTTOM", "BUS_KLMS_MS", "BUS_HMT", "BUS_TOSHIBA", "BUS_VALLATHOL", "BUS_BMC", "BUS_CIVIL_STN", "BUS_KKD_WM", "BUS_INFOPARK_P1", "BUS_INFOPARK_P2"], "#EA580C"),
        ("BUS_R2", "KLM-RSET-CUSAT", "Kalamassery - Rajagiri - CUSAT Campus Feeder", ["BUS_KLMS_MS", "BUS_CUSAT", "BUS_HMT", "BUS_GOVT_ITI", "BUS_RAJAGIRI", "BUS_MED_COLL", "BUS_CIVIL_STN"], "#F59E0B"),
        ("BUS_R3", "MGRD-HC-KDV", "MG Road - High Court - Kadavanthra Circular", ["BUS_MG_METRO", "BUS_HIGH_COURT", "BUS_MENAKA", "BUS_EKM_JETTY", "BUS_SOUTH_MS", "BUS_KADAVANTHRA", "BUS_SHIPYARD", "BUS_MG_METRO"], "#10B981"),
        ("BUS_R4", "KKD-EXPRESS", "Rajagiri Kakkanad - Infopark Shuttle", ["BUS_RAJAGIRI", "BUS_CIVIL_STN", "BUS_INFOPARK_P1"], "#8B5CF6")
    ]

    for rid, sname, lname, seq, color in feeder_routes:
        db.add(Route(id=rid, short_name=sname, long_name=lname, mode="bus", agency="FeederBus", color=color))
        for i in range(len(seq) - 1):
            s1_id, s2_id = seq[i], seq[i+1]
            s1, s2 = feeder_stops_map[s1_id], feeder_stops_map[s2_id]
            dist = haversine_km(s1.lat, s1.lon, s2.lat, s2.lon)
            dur = round((dist / 20.0) * 60 + 1.0, 1) # Bus speed ~20km/h
            geom = json.dumps([[s1.lat, s1.lon], [s2.lat, s2.lon]])

            db.add(Edge(route_id=rid, from_stop_id=s1.id, to_stop_id=s2.id, mode="bus", distance_km=round(dist, 2), duration_min=max(dur, 2.0), fare=15.0, geometry=geom))
            db.add(Edge(route_id=rid, from_stop_id=s2.id, to_stop_id=s1.id, mode="bus", distance_km=round(dist, 2), duration_min=max(dur, 2.0), fare=15.0, geometry=geom))
    print(f"Successfully ingested {len(feeder_stops_def)} Feeder Bus Stops.")

    # =========================================================================
    # STEP 4: CREATE MULTIMODAL INTERCHANGE / WALKING TRANSFER EDGES
    # =========================================================================
    all_stops = db.query(Stop).all()
    transfers_count = 0

    # Auto-connect stops of DIFFERENT modes within 500 meters
    for i in range(len(all_stops)):
        for j in range(i + 1, len(all_stops)):
            s1, s2 = all_stops[i], all_stops[j]
            if s1.mode != s2.mode:
                dist = haversine_km(s1.lat, s1.lon, s2.lat, s2.lon)
                if dist <= 0.50: # <= 500 meters
                    walk_dur = round(dist * 13.3 + 1.5, 1) # Walk ~4.5 km/h + 1.5min transfer overhead
                    geom = json.dumps([[s1.lat, s1.lon], [s2.lat, s2.lon]])
                    db.add(Edge(route_id=None, from_stop_id=s1.id, to_stop_id=s2.id, mode="walk", distance_km=round(dist, 3), duration_min=max(walk_dur, 1.5), fare=0.0, geometry=geom))
                    db.add(Edge(route_id=None, from_stop_id=s2.id, to_stop_id=s1.id, mode="walk", distance_km=round(dist, 3), duration_min=max(walk_dur, 1.5), fare=0.0, geometry=geom))
                    transfers_count += 2

    db.commit()
    print(f"Successfully created {transfers_count} Multimodal Transfer Edges.")
    print("Database Ingestion Complete! SQLite database 'smartroute.db' ready.")

if __name__ == "__main__":
    db = SessionLocal()
    try:
        ingest_all(db)
    finally:
        db.close()
