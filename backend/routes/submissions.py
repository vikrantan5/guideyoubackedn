from fastapi import APIRouter, HTTPException, Depends
from models.submission import Submission, SubmissionCreate, SubmissionUpdate
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

@router.post("/", response_model=Submission)
async def create_submission(submission: SubmissionCreate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "student":
        raise HTTPException(status_code=403, detail="Only students can submit")
    
    # Check if task exists
    task = await db.tasks.find_one({"id": submission.task_id}, {"_id": 0})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Check if student is assigned to this task
    if current_user["sub"] not in task.get("assigned_to", []):
        raise HTTPException(status_code=403, detail="Not assigned to this task")
    
    # Check if already submitted
    existing = await db.submissions.find_one({
        "task_id": submission.task_id,
        "student_id": current_user["sub"]
    }, {"_id": 0})
    
    if existing:
        raise HTTPException(status_code=400, detail="Already submitted for this task")
    
    # Check if submission is late
    deadline = datetime.fromisoformat(task['deadline']) if isinstance(task['deadline'], str) else task['deadline']
    is_late = datetime.now(deadline.tzinfo) > deadline
    
    # Set defaults for simplified submission
    content = submission.content if submission.content else "Task marked as complete"
    submission_type = submission.submission_type if submission.submission_type else "text"
    
    submission_obj = Submission(
        task_id=submission.task_id,
        content=content,
        submission_type=submission_type,
        student_id=current_user["sub"],
        is_late=is_late
    )
    submission_data = submission_obj.model_dump()
    submission_data['submitted_at'] = submission_data['submitted_at'].isoformat()
    
    await db.submissions.insert_one(submission_data)
    
    # Update student progress
    await db.progress.update_one(
        {"student_id": current_user["sub"]},
        {"$inc": {"completed_tasks": 1}}
    )
    
    return submission_obj

@router.get("/")
async def get_submissions(current_user: dict = Depends(get_current_user)):
    if current_user["role"] == "admin":
        submissions = await db.submissions.find({}, {"_id": 0}).to_list(1000)
    else:
        submissions = await db.submissions.find(
            {"student_id": current_user["sub"]},
            {"_id": 0}
        ).to_list(1000)
    
    for sub in submissions:
        if isinstance(sub.get('submitted_at'), str):
            sub['submitted_at'] = datetime.fromisoformat(sub['submitted_at'])
    
    return submissions

@router.get("/task/{task_id}")
async def get_task_submissions(task_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    
    submissions = await db.submissions.find({"task_id": task_id}, {"_id": 0}).to_list(1000)
    
    for sub in submissions:
        if isinstance(sub.get('submitted_at'), str):
            sub['submitted_at'] = datetime.fromisoformat(sub['submitted_at'])
        
        # Get student info
        student = await db.users.find_one({"id": sub['student_id']}, {"_id": 0, "name": 1, "email": 1})
        if student:
            sub['student_name'] = student.get('name')
            sub['student_email'] = student.get('email')
    
    return submissions

@router.get("/{submission_id}", response_model=Submission)
async def get_submission(submission_id: str, current_user: dict = Depends(get_current_user)):
    submission = await db.submissions.find_one({"id": submission_id}, {"_id": 0})
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    # Check access
    if current_user["role"] == "student" and submission['student_id'] != current_user["sub"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    if isinstance(submission.get('submitted_at'), str):
        submission['submitted_at'] = datetime.fromisoformat(submission['submitted_at'])
    
    return Submission(**submission)

@router.put("/{submission_id}", response_model=Submission)
async def update_submission(submission_id: str, submission_update: SubmissionUpdate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    
    submission = await db.submissions.find_one({"id": submission_id}, {"_id": 0})
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    update_data = submission_update.model_dump(exclude_unset=True)
    await db.submissions.update_one({"id": submission_id}, {"$set": update_data})
    
    updated_submission = await db.submissions.find_one({"id": submission_id}, {"_id": 0})
    if isinstance(updated_submission.get('submitted_at'), str):
        updated_submission['submitted_at'] = datetime.fromisoformat(updated_submission['submitted_at'])
    
    return Submission(**updated_submission)

@router.post("/{submission_id}/like")
async def like_submission(submission_id: str, current_user: dict = Depends(get_current_user)):
    submission = await db.submissions.find_one({"id": submission_id}, {"_id": 0})
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    await db.submissions.update_one(
        {"id": submission_id},
        {"$inc": {"likes": 1}}
    )
    
    return {"message": "Liked successfully"}

@router.delete("/{submission_id}")
async def delete_submission(submission_id: str, current_user: dict = Depends(get_current_user)):
    submission = await db.submissions.find_one({"id": submission_id}, {"_id": 0})
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    # Only admin or the student who submitted can delete
    if current_user["role"] != "admin" and submission['student_id'] != current_user["sub"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    result = await db.submissions.delete_one({"id": submission_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    # Update progress if deleted by student
    if current_user["role"] == "student":
        await db.progress.update_one(
            {"student_id": current_user["sub"]},
            {"$inc": {"completed_tasks": -1}}
        )
    
    return {"message": "Submission deleted successfully"}
