from __future__ import annotations

from sqlalchemy import ARRAY, Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Hotel(Base):
    __tablename__ = "hotels"

    id = Column(Integer, primary_key=True, autoincrement=False)
    name = Column(String(255), nullable=False)
    accommodation_type = Column(String(100))
    star_rating = Column(Float)
    is_luxury = Column(Boolean, default=False)
    review_score = Column(Float)
    review_count = Column(Integer, default=0)
    address = Column(Text)
    city = Column(String(100))
    latitude = Column(Float)
    longitude = Column(Float)
    description = Column(Text)
    amenities = Column(ARRAY(String))
    amenity_groups = Column(JSONB)
    useful_info = Column(JSONB)
    policy_notes = Column(ARRAY(String))
    suitable_for = Column(ARRAY(String))
    reviews_detail = Column(JSONB)
    images = Column(ARRAY(String))
    source_url = Column(Text)
    crawled_at = Column(DateTime)
    amenities_general = Column(ARRAY(String))
    amenities_leisure = Column(ARRAY(String))
    amenities_dining = Column(ARRAY(String))


class Room(Base):
    __tablename__ = "rooms"

    hotel_id = Column(Integer, ForeignKey("hotels.id"), primary_key=True)
    room_type_id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    price_per_night = Column(Float)
    original_price = Column(Float)
    room_size = Column(String(50))
    max_occupancy = Column(Integer)
    bed_type = Column(String(255))
    room_view = Column(String(100))
    room_amenities = Column(ARRAY(String))
    images = Column(ARRAY(String))
    review_score = Column(Float)


class NearbyPlace(Base):
    __tablename__ = "nearby_places"

    hotel_id = Column(Integer, ForeignKey("hotels.id"), primary_key=True)
    name = Column(String(255), primary_key=True)
    type = Column(String(100))
    distance_km = Column(Float)


class Activity(Base):
    __tablename__ = "activities"

    hotel_id = Column(Integer, ForeignKey("hotels.id"), primary_key=True)
    title = Column(String(255), primary_key=True)
    description = Column(Text)
    price_amount = Column(Float)
    review_score = Column(Float)
    activity_id = Column(Integer)
