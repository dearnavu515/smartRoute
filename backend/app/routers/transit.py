import json
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from ..db.database import get_db
from ..db.models import Stop, Route, Edge

router = APIRouter(prefix="/api/transit", tags=["transit"])

@router.get("/stops")
def get_stops(mode: Optional[str] = Query(None), db: Session = Depends(get_db)):
    query = db.query(Stop)
    if mode:
        query = query.filter(Stop.mode == mode)
    stops = query.all()
    return [s.to_dict() for s in stops]

@router.get("/routes")
def get_routes(db: Session = Depends(get_db)):
    routes = db.query(Route).all()
    return [r.to_dict() for r in routes]

@router.get("/network-graph")
def get_network_graph(db: Session = Depends(get_db)):
    stops = db.query(Stop).all()
    routes = db.query(Route).all()
    edges = db.query(Edge).all()

    edge_list = []
    for e in edges:
        geom = []
        if e.geometry:
            try:
                geom = json.loads(e.geometry)
            except:
                pass
        edge_list.append({
            "id": e.id,
            "route_id": e.route_id,
            "from_stop_id": e.from_stop_id,
            "to_stop_id": e.to_stop_id,
            "mode": e.mode,
            "distance_km": e.distance_km,
            "duration_min": e.duration_min,
            "fare": e.fare,
            "geometry": geom
        })

    return {
        "stops": [s.to_dict() for s in stops],
        "routes": [r.to_dict() for r in routes],
        "edges": edge_list
    }
