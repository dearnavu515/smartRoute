from sqlalchemy import Column, Integer, String, Float, ForeignKey, Text
from sqlalchemy.orm import relationship
from .database import Base

class Stop(Base):
    __tablename__ = "stops"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    mode = Column(String, nullable=False)   # 'metro', 'water_metro', 'bus'
    agency = Column(String, nullable=False) # 'KMRL', 'KWML', 'FeederBus'
    zone_id = Column(String, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "lat": self.lat,
            "lon": self.lon,
            "mode": self.mode,
            "agency": self.agency,
            "zone_id": self.zone_id
        }

class Route(Base):
    __tablename__ = "routes"

    id = Column(String, primary_key=True, index=True)
    short_name = Column(String, nullable=False)
    long_name = Column(String, nullable=False)
    mode = Column(String, nullable=False)   # 'metro', 'water_metro', 'bus'
    agency = Column(String, nullable=False)
    color = Column(String, default="#3B82F6")

    def to_dict(self):
        return {
            "id": self.id,
            "short_name": self.short_name,
            "long_name": self.long_name,
            "mode": self.mode,
            "agency": self.agency,
            "color": self.color
        }

class Edge(Base):
    __tablename__ = "edges"

    id = Column(Integer, primary_key=True, autoincrement=True)
    route_id = Column(String, ForeignKey("routes.id"), nullable=True)
    from_stop_id = Column(String, ForeignKey("stops.id"), nullable=False, index=True)
    to_stop_id = Column(String, ForeignKey("stops.id"), nullable=False, index=True)
    mode = Column(String, nullable=False)   # 'metro', 'water_metro', 'bus', 'walk'
    distance_km = Column(Float, default=0.0)
    duration_min = Column(Float, default=0.0)
    fare = Column(Float, default=0.0)
    geometry = Column(Text, nullable=True)  # JSON-encoded array of [lat, lon]

    def to_dict(self):
        return {
            "id": self.id,
            "route_id": self.route_id,
            "from_stop_id": self.from_stop_id,
            "to_stop_id": self.to_stop_id,
            "mode": self.mode,
            "distance_km": self.distance_km,
            "duration_min": self.duration_min,
            "fare": self.fare,
            "geometry": self.geometry
        }

class FareRule(Base):
    __tablename__ = "fare_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    mode = Column(String, nullable=False)
    origin_id = Column(String, nullable=False)
    destination_id = Column(String, nullable=False)
    fare = Column(Float, nullable=False)
