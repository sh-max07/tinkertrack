from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Resource, Reservation, User
from pydantic import BaseModel
from datetime import datetime
from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta
from fastapi.security import OAuth2PasswordBearer

app = FastAPI()

SECRET_KEY = "your-secret-key-change-this-later"
ALGORITHM = "HS256"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        role = payload.get("role")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return {"user_id": user_id, "role": role}
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

def get_current_admin(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

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
def create_resource(resource: ResourceCreate, current_admin: dict = Depends(get_current_admin)):
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
def update_resource(resource_id: int, updates: ResourceUpdate, current_admin: dict = Depends(get_current_admin)):
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

@app.patch("/reservations/{reservation_id}/cancel")
def cancel_reservation(reservation_id: int, current_user: dict = Depends(get_current_user)):
    db = SessionLocal()
    reservation = db.query(Reservation).filter(Reservation.id == reservation_id).first()

    if reservation is None:
        db.close()
        raise HTTPException(status_code=404, detail="Reservation not found")

    if reservation.user_id != current_user["user_id"]:
        db.close()
        raise HTTPException(status_code=403, detail="You can only cancel your own reservations")

    reservation.status = "cancelled"
    db.commit()
    db.refresh(reservation)
    db.close()
    return reservation

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class UserCreate(BaseModel):
    name: str
    email: str
    password: str

@app.post("/signup")
def signup(user: UserCreate):
    db = SessionLocal()

    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        db.close()
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = pwd_context.hash(user.password)

    new_user = User(
        name=user.name,
        email=user.email,
        password=hashed_password,
        role="user"
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    db.close()
    return {"id": new_user.id, "name": new_user.name, "email": new_user.email}


class LoginRequest(BaseModel):
    email: str
    password: str

@app.post("/login")
def login(credentials: LoginRequest):
    db = SessionLocal()
    user = db.query(User).filter(User.email == credentials.email).first()
    db.close()

    if user is None:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not pwd_context.verify(credentials.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token_data = {
        "user_id": user.id,
        "role": user.role,
        "exp": datetime.utcnow() + timedelta(hours=24)
    }
    token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)

    return {"access_token": token, "token_type": "bearer"}

