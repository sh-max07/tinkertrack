from fastapi import FastAPI, HTTPException
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Resource
from pydantic import BaseModel

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