from fastapi import FastAPI, HTTPException
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Resource
from pydantic import BaseModel
from datetime import datetime
from models import Reservation

app = FastAPI()

@app.get("/resources")
def get_resources():
    db = SessionLocal()
    resources = db.query(Resource).all()
    db.close()
    return resources

class ResourceCreate(BaseModel):
    name: str
    description: str | None = None
    category: str

@app.post("/resources")
def create_resource(resource: ResourceCreate):
    db = SessionLocal()
    new_resource = Resource(
        name=resource.name,
        description=resource.description,
        category=resource.category,
        status="active"
    )
    db.add(new_resource)
    db.commit()
    db.refresh(new_resource)
    db.close()
    return new_resource

@app.get("/resources/{resource_id}")
def get_resource(resource_id: int):
    db = SessionLocal()
    resource = db.query(Resource).filter(Resource.id == resource_id).first()
    db.close()
    if resource is None:
        raise HTTPException(status_code=404, detail="Resource not found")
    return resource

class ResourceUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    category: str | None = None
    status: str | None = None
    operational_hours: str | None = None
    max_capacity: int | None = None

@app.patch("/resources/{resource_id}")
def update_resource(resource_id: int, updates: ResourceUpdate):
    db = SessionLocal()
    resource = db.query(Resource).filter(Resource.id == resource_id).first()

    if resource is None:
        db.close()
        raise HTTPException(status_code=404, detail="Resource not found")

    update_data = updates.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(resource, field, value)

    db.commit()
    db.refresh(resource)
    db.close()
    return resource

class ReservationCreate(BaseModel):
    user_id: int
    resource_id: int
    start_time: datetime
    end_time: datetime

@app.post("/reservations")
def create_reservation(reservation: ReservationCreate):
    db = SessionLocal()

    conflict = db.query(Reservation).filter(
        Reservation.resource_id == reservation.resource_id,
        Reservation.status == "confirmed",
        Reservation.start_time < reservation.end_time,
        Reservation.end_time > reservation.start_time
    ).first()

    if conflict:
        db.close()
        raise HTTPException(status_code=409, detail="This time slot conflicts with an existing reservation")

    new_reservation = Reservation(
        user_id=reservation.user_id,
        resource_id=reservation.resource_id,
        start_time=reservation.start_time,
        end_time=reservation.end_time,
        status="confirmed"
    )
    db.add(new_reservation)
    db.commit()
    db.refresh(new_reservation)
    db.close()
    return new_reservation

@app.get("/reservations")
def get_my_reservations(user_id: int):
    db = SessionLocal()
    reservations = db.query(Reservation).filter(Reservation.user_id == user_id).all()
    db.close()
    return reservations

@app.get("/reservations/all")
def get_all_reservations():
    db = SessionLocal()
    reservations = db.query(Reservation).all()
    db.close()
    return reservations