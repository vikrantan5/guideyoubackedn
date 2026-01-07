from fastapi import APIRouter, HTTPException, Depends
from models.task import Task, TaskCreate, TaskUpdate
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

@router.post("/", response_model=Task)
async def create_task(task: TaskCreate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    
    task_obj = Task(**task.model_dump(), created_by=current_user["sub"])
    task_data = task_obj.model_dump()
    task_data['created_at'] = task_data['created_at'].isoformat()
    task_data['deadline'] = task_data['deadline'].isoformat()
    
    await db.tasks.insert_one(task_data)
    
    # Update total_tasks for assigned students
    if task.assigned_to:
        for student_id in task.assigned_to:
            await db.progress.update_one(
                {"student_id": student_id},
                {"$inc": {"total_tasks": 1}}
            )
    
    return task_obj

@router.get("/")
async def get_tasks(current_user: dict = Depends(get_current_user)):
    if current_user["role"] == "admin":
        tasks = await db.tasks.find({}, {"_id": 0}).to_list(1000)
    else:
        tasks = await db.tasks.find(
            {"assigned_to": current_user["sub"]}, 
            {"_id": 0}
        ).to_list(1000)
    
    for task in tasks:
        if isinstance(task['created_at'], str):
            task['created_at'] = datetime.fromisoformat(task['created_at'])
        if isinstance(task['deadline'], str):
            task['deadline'] = datetime.fromisoformat(task['deadline'])
        
        # Attach submission data for students
        if current_user["role"] == "student":
            submission = await db.submissions.find_one(
                {"task_id": task['id'], "student_id": current_user["sub"]},
                {"_id": 0}
            )
            if submission:
                if isinstance(submission.get('submitted_at'), str):
                    submission['submitted_at'] = datetime.fromisoformat(submission['submitted_at'])
                task['submission'] = submission
            else:
                task['submission'] = None
    
    return tasks

@router.get("/today")
async def get_today_tasks(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "student":
        raise HTTPException(status_code=403, detail="Not authorized")
    
    from datetime import date, timedelta, timezone as tz
    today_start = datetime.combine(date.today(), datetime.min.time()).replace(tzinfo=tz.utc)
    tomorrow_start = today_start + timedelta(days=1)
    
    tasks = await db.tasks.find({
        "assigned_to": current_user["sub"],
        "deadline": {
            "$gte": today_start.isoformat(),
            "$lt": tomorrow_start.isoformat()
        }
    }, {"_id": 0}).to_list(1000)
    
    for task in tasks:
        if isinstance(task['created_at'], str):
            task['created_at'] = datetime.fromisoformat(task['created_at'])
        if isinstance(task['deadline'], str):
            task['deadline'] = datetime.fromisoformat(task['deadline'])
        
        # Attach submission data
        submission = await db.submissions.find_one(
            {"task_id": task['id'], "student_id": current_user["sub"]},
            {"_id": 0}
        )
        if submission:
            if isinstance(submission.get('submitted_at'), str):
                submission['submitted_at'] = datetime.fromisoformat(submission['submitted_at'])
            task['submission'] = submission
        else:
            task['submission'] = None
    
    return tasks

@router.get("/{task_id}", response_model=Task)
async def get_task(task_id: str, current_user: dict = Depends(get_current_user)):
    task = await db.tasks.find_one({"id": task_id}, {"_id": 0})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if isinstance(task['created_at'], str):
        task['created_at'] = datetime.fromisoformat(task['created_at'])
    if isinstance(task['deadline'], str):
        task['deadline'] = datetime.fromisoformat(task['deadline'])
    
    return Task(**task)

@router.put("/{task_id}", response_model=Task)
async def update_task(task_id: str, task_update: TaskUpdate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    
    task = await db.tasks.find_one({"id": task_id}, {"_id": 0})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    update_data = task_update.model_dump(exclude_unset=True)
    if 'deadline' in update_data and update_data['deadline']:
        update_data['deadline'] = update_data['deadline'].isoformat()
    
    await db.tasks.update_one({"id": task_id}, {"$set": update_data})
    
    updated_task = await db.tasks.find_one({"id": task_id}, {"_id": 0})
    if isinstance(updated_task['created_at'], str):
        updated_task['created_at'] = datetime.fromisoformat(updated_task['created_at'])
    if isinstance(updated_task['deadline'], str):
        updated_task['deadline'] = datetime.fromisoformat(updated_task['deadline'])
    
    return Task(**updated_task)

@router.delete("/{task_id}")
async def delete_task(task_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    
    result = await db.tasks.delete_one({"id": task_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return {"message": "Task deleted successfully"}