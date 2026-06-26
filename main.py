from fastapi import FastAPI
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Resource

app = FastAPI()

@app.get("/resources")
def get_resources():
    db = SessionLocal()
    resources = db.query(Resource).all()
    db.close()
    return resources