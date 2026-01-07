from fastapi import APIRouter, HTTPException, Depends
from models.announcement import Announcement, AnnouncementCreate
from utils.auth import get_current_user
from typing import List
from datetime import datetime
import os
from pathlib import Path
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

router = APIRouter()

@router.post("/", response_model=Announcement)
async def create_announcement(announcement: AnnouncementCreate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    
    announcement_obj = Announcement(**announcement.model_dump(), created_by=current_user["sub"])
    announcement_data = announcement_obj.model_dump()
    announcement_data['created_at'] = announcement_data['created_at'].isoformat()
    
    await db.announcements.insert_one(announcement_data)
    return announcement_obj

@router.get("/", response_model=List[Announcement])
async def get_announcements(current_user: dict = Depends(get_current_user)):
    announcements = await db.announcements.find({}, {"_id": 0}).sort("created_at", -1).to_list(100)
    
    for ann in announcements:
        if isinstance(ann['created_at'], str):
            ann['created_at'] = datetime.fromisoformat(ann['created_at'])
    
    return [Announcement(**ann) for ann in announcements]

@router.delete("/{announcement_id}")
async def delete_announcement(announcement_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    
    result = await db.announcements.delete_one({"id": announcement_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Announcement not found")
    
    return {"message": "Announcement deleted successfully"}