from fastapi import APIRouter, HTTPException, Depends
from models.user import UserCreate, UserLogin, Token, User
from utils.auth import get_password_hash, verify_password, create_access_token
from motor.motor_asyncio import AsyncIOMotorDatabase
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

@router.post("/register", response_model=Token)
async def register(user: UserCreate):
    # Check if user exists
    existing_user = await db.users.find_one({"email": user.email}, {"_id": 0})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    user_dict = user.model_dump()
    user_dict['hashed_password'] = get_password_hash(user_dict.pop('password'))
    
    from models.user import UserInDB
    user_in_db = UserInDB(**user_dict)
    user_data = user_in_db.model_dump()
    user_data['created_at'] = user_data['created_at'].isoformat()
    
    await db.users.insert_one(user_data)
    
    # Create progress for student
    if user.role == "student":
        from models.progress import Progress
        progress = Progress(student_id=user_in_db.id)
        progress_data = progress.model_dump()
        progress_data['last_activity'] = progress_data['last_activity'].isoformat()
        await db.progress.insert_one(progress_data)
    
    # Create token
    access_token = create_access_token(data={"sub": user_in_db.id, "role": user_in_db.role})
    
    user_response = User(
        id=user_in_db.id,
        email=user_in_db.email,
        name=user_in_db.name,
        role=user_in_db.role,
        created_at=user_in_db.created_at
    )
    
    return Token(access_token=access_token, token_type="bearer", user=user_response)

@router.post("/login", response_model=Token)
async def login(user_login: UserLogin):
    # Find user
    user_data = await db.users.find_one({"email": user_login.email}, {"_id": 0})
    if not user_data:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Verify password
    if not verify_password(user_login.password, user_data['hashed_password']):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Create token
    access_token = create_access_token(data={"sub": user_data['id'], "role": user_data['role']})
    
    user_response = User(
        id=user_data['id'],
        email=user_data['email'],
        name=user_data['name'],
        role=user_data['role'],
        created_at=user_data['created_at'] if isinstance(user_data['created_at'], str) else user_data['created_at'].isoformat()
    )
    
    return Token(access_token=access_token, token_type="bearer", user=user_response)