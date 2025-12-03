import os
from typing import Optional
import shutil

from fastapi import FastAPI, Request, File, UploadFile
from pymongo import MongoClient
from dotenv import load_dotenv
from pydantic import BaseModel
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.templating import Jinja2Templates

load_dotenv()

app = FastAPI()

MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client.get_database("emogo")
templates = Jinja2Templates(directory="templates")

# Create an uploads directory if it doesn't exist
UPLOADS_DIR = "uploads"
if not os.path.exists(UPLOADS_DIR):
    os.makedirs(UPLOADS_DIR)


class Vlog(BaseModel):
    user_id: str
    video_url: str

class Sentiment(BaseModel):
    user_id: str
    sentiment_score: float

class GPS(BaseModel):
    user_id: str
    latitude: float
    longitude: float


@app.get("/")
async def root():
    return {"message": "EmoGo Backend is running!"}

@app.get("/items/{item_id}")
def read_item(item_id: int, q: Optional[str] = None):
    return {"item_id": item_id, "q": q}

@app.post("/vlogs/")
async def create_vlog(user_id: str, video: UploadFile = File(...)):
    video_path = os.path.join(UPLOADS_DIR, video.filename)
    with open(video_path, "wb") as buffer:
        shutil.copyfileobj(video.file, buffer)
    
    vlog_data = {
        "user_id": user_id,
        "video_url": f"/videos/{video.filename}"
    }
    db.vlogs.insert_one(vlog_data)
    return {"filename": video.filename, "user_id": user_id}

@app.post("/sentiments/")
async def create_sentiment(sentiment: Sentiment):
    db.sentiments.insert_one(sentiment.dict())
    return sentiment

@app.post("/gps/")
async def create_gps(gps: GPS):
    db.gps.insert_one(gps.dict())
    return gps

@app.get("/videos/{video_name}")
async def get_video(video_name: str):
    video_path = os.path.join(UPLOADS_DIR, video_name)
    if not os.path.exists(video_path):
        return {"error": "Video not found"}
    return FileResponse(video_path)

@app.get("/data", response_class=HTMLResponse)
async def read_data(request: Request):
    vlogs = list(db.vlogs.find({}, {'_id': 0}))
    sentiments = list(db.sentiments.find({}, {'_id': 0}))
    gps = list(db.gps.find({}, {'_id': 0}))
    return templates.TemplateResponse("data.html", {"request": request, "vlogs": vlogs, "sentiments": sentiments, "gps": gps})

@app.get("/data/vlogs")
async def download_vlogs():
    vlogs = list(db.vlogs.find({}, {'_id': 0}))
    return JSONResponse(content=vlogs, media_type="application/json", headers={"Content-Disposition": "attachment; filename=vlogs.json"})

@app.get("/data/sentiments")
async def download_sentiments():
    sentiments = list(db.sentiments.find({}, {'_id': 0}))
    return JSONResponse(content=sentiments, media_type="application/json", headers={"Content-Disposition": "attachment; filename=sentiments.json"})

@app.get("/data/gps")
async def download_gps():
    gps = list(db.gps.find({}, {'_id': 0}))
    return JSONResponse(content=gps, media_type="application/json", headers={"Content-Disposition": "attachment; filename=gps.json"})

@app.get("/populate-fake-data")
async def populate_fake_data():
    # Clear existing data
    db.vlogs.delete_many({})
    db.sentiments.delete_many({})
    db.gps.delete_many({})

    # Add fake data
    db.vlogs.insert_one({"user_id": "user1", "video_url": "fake_video.mp4"})
    db.sentiments.insert_one({"user_id": "user1", "sentiment_score": 0.8})
    db.gps.insert_one({"user_id": "user1", "latitude": 34.0522, "longitude": -118.2437})
    
    return {"message": "Fake data has been populated."}