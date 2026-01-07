from fastapi import APIRouter, HTTPException, Depends
from models.user import User, UserCreate
from utils.auth import get_current_user, get_password_hash
from typing import List
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

@router.get("/me", response_model=User)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    user_data = await db.users.find_one({"id": current_user["sub"]}, {"_id": 0})
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")
    return User(**user_data)

@router.get("/students", response_model=List[User])
async def get_students(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    
    students = await db.users.find({"role": "student"}, {"_id": 0}).to_list(1000)
    return [User(**student) for student in students]

@router.post("/students", response_model=User)
async def create_student(user: UserCreate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Check if user exists
    existing_user = await db.users.find_one({"email": user.email}, {"_id": 0})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    user_dict = user.model_dump()
    user_dict['role'] = 'student'
    user_dict['hashed_password'] = get_password_hash(user_dict.pop('password'))
    
    from models.user import UserInDB
    user_in_db = UserInDB(**user_dict)
    user_data = user_in_db.model_dump()
    user_data['created_at'] = user_data['created_at'].isoformat()
    
    await db.users.insert_one(user_data)
    
    # Create progress
    from models.progress import Progress
    progress = Progress(student_id=user_in_db.id)
    progress_data = progress.model_dump()
    progress_data['last_activity'] = progress_data['last_activity'].isoformat()
    await db.progress.insert_one(progress_data)
    
    return User(
        id=user_in_db.id,
        email=user_in_db.email,
        name=user_in_db.name,
        role=user_in_db.role,
        created_at=user_in_db.created_at
    )