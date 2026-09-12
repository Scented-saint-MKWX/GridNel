from sqlalchemy import JSON, ARRAY, Column, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Camera(Base):
    __tablename__ = "cameras"
    camera_id = Column(String, primary_key=True)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    zone = Column(String, nullable=False)
    road_node_id = Column(String, nullable=False)


class Plate(Base):
    __tablename__ = "plates"
    plate_hash = Column(String, primary_key=True)
    plate_text_enc = Column(Text, nullable=False)
    first_seen = Column(DateTime(timezone=True), nullable=False)
    last_seen = Column(DateTime(timezone=True), nullable=False)


class Sighting(Base):
    __tablename__ = "sightings"
    id = Column(UUID(as_uuid=True), primary_key=True)
    plate_hash = Column(String, ForeignKey("plates.plate_hash"), nullable=False)
    camera_id = Column(String, ForeignKey("cameras.camera_id"), nullable=False)
    ts = Column(DateTime(timezone=True), nullable=False)
    conf = Column(Float, nullable=False)
    outcome = Column(String, nullable=False)
    alt_hashes = Column(ARRAY(String), nullable=False)
    quality = Column(String, nullable=False)


class Blacklist(Base):
    __tablename__ = "blacklist"
    plate_hash = Column(String, primary_key=True)
    reason = Column(Text, nullable=False)
    added_by = Column(String, nullable=False)
    added_ts = Column(DateTime(timezone=True), nullable=False)


class AlertEvent(Base):
    __tablename__ = "alert_events"
    id = Column(UUID(as_uuid=True), primary_key=True)
    type = Column(String, nullable=False)
    plate_hash = Column(String, nullable=False)
    camera_id = Column(String, nullable=False)
    ts = Column(DateTime(timezone=True), nullable=False)
    detail = Column(JSON, nullable=False)
