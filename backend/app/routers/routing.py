from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional
from ..db.database import get_db
from ..services.dijkstra import MultimodalRouter

router = APIRouter(prefix="/api/routing", tags=["routing"])

class PlanRequest(BaseModel):
    origin_id: Optional[str] = None
    destination_id: Optional[str] = None
    origin_lat: Optional[float] = None
    origin_lon: Optional[float] = None
    origin_name: Optional[str] = None
    dest_lat: Optional[float] = None
    dest_lon: Optional[float] = None
    dest_name: Optional[str] = None
    preference: Optional[str] = "fastest" # 'fastest', 'cheapest', 'least_transfers'

@router.post("/plan")
def plan_journey(req: PlanRequest, db: Session = Depends(get_db)):
    router_instance = MultimodalRouter(db)
    options = router_instance.find_all_routes_for_points(
        origin_id=req.origin_id,
        destination_id=req.destination_id,
        origin_lat=req.origin_lat,
        origin_lon=req.origin_lon,
        origin_name=req.origin_name,
        dest_lat=req.dest_lat,
        dest_lon=req.dest_lon,
        dest_name=req.dest_name
    )

    if not options:
        raise HTTPException(
            status_code=404,
            detail="No viable multimodal path found between selected origin and destination."
        )

    result = dict(options[0])
    result["options"] = options
    return result

