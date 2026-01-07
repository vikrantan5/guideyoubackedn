from fastapi import APIRouter, HTTPException, Depends
from models.progress import Progress
from utils.auth import get_current_user
from typing import List, Dict
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

@router.get("/me", response_model=Progress)
async def get_my_progress(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "student":
        raise HTTPException(status_code=403, detail="Not authorized")
    
    progress = await db.progress.find_one({"student_id": current_user["sub"]}, {"_id": 0})
    if not progress:
        # Create if not exists
        progress_obj = Progress(student_id=current_user["sub"])
        progress_data = progress_obj.model_dump()
        progress_data['last_activity'] = progress_data['last_activity'].isoformat()
        await db.progress.insert_one(progress_data)
        return progress_obj
    
    if isinstance(progress['last_activity'], str):
        progress['last_activity'] = datetime.fromisoformat(progress['last_activity'])
    
    return Progress(**progress)

@router.get("/leaderboard", response_model=List[Dict])
async def get_leaderboard(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Get all progress
    progress_list = await db.progress.find({}, {"_id": 0}).to_list(1000)
    
    # Get student names
    leaderboard = []
    for prog in progress_list:
        student = await db.users.find_one({"id": prog['student_id']}, {"_id": 0})
        if student:
            completion_rate = (prog['completed_tasks'] / prog['total_tasks'] * 100) if prog['total_tasks'] > 0 else 0
            leaderboard.append({
                "student_id": prog['student_id'],
                "name": student['name'],
                "completed_tasks": prog['completed_tasks'],
                "total_tasks": prog['total_tasks'],
                "completion_rate": completion_rate,
                "current_streak": prog['current_streak'],
                "badges": prog['badges']
            })
    
    # Sort by completion rate and streak
    leaderboard.sort(key=lambda x: (x['completion_rate'], x['current_streak']), reverse=True)
    return leaderboard

@router.get("/student/{student_id}", response_model=Progress)
async def get_student_progress(student_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    
    progress = await db.progress.find_one({"student_id": student_id}, {"_id": 0})
    if not progress:
        raise HTTPException(status_code=404, detail="Progress not found")
    
    if isinstance(progress['last_activity'], str):
        progress['last_activity'] = datetime.fromisoformat(progress['last_activity'])
    
    return Progress(**progress)