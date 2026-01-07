from fastapi import APIRouter, HTTPException, Depends
from models.chat import Message, MessageCreate, ChatSession
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

@router.post("/sessions", response_model=ChatSession)
async def create_chat_session(student_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Check if session exists
    existing = await db.chat_sessions.find_one(
        {"admin_id": current_user["sub"], "student_id": student_id},
        {"_id": 0}
    )
    
    if existing:
        if isinstance(existing['created_at'], str):
            existing['created_at'] = datetime.fromisoformat(existing['created_at'])
        return ChatSession(**existing)
    
    # Create new session
    session = ChatSession(admin_id=current_user["sub"], student_id=student_id)
    session_data = session.model_dump()
    session_data['created_at'] = session_data['created_at'].isoformat()
    
    await db.chat_sessions.insert_one(session_data)
    return session

@router.get("/sessions", response_model=List[ChatSession])
async def get_chat_sessions(current_user: dict = Depends(get_current_user)):
    if current_user["role"] == "admin":
        sessions = await db.chat_sessions.find(
            {"admin_id": current_user["sub"]},
            {"_id": 0}
        ).to_list(1000)
    else:
        sessions = await db.chat_sessions.find(
            {"student_id": current_user["sub"]},
            {"_id": 0}
        ).to_list(1000)
    
    for session in sessions:
        if isinstance(session['created_at'], str):
            session['created_at'] = datetime.fromisoformat(session['created_at'])
    
    return [ChatSession(**session) for session in sessions]

@router.get("/messages/{chat_id}", response_model=List[Message])
async def get_messages(chat_id: str, current_user: dict = Depends(get_current_user)):
    # Verify access to chat
    session = await db.chat_sessions.find_one({"id": chat_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    
    if session['admin_id'] != current_user["sub"] and session['student_id'] != current_user["sub"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    messages = await db.messages.find(
        {"chat_id": chat_id, "is_deleted": False},
        {"_id": 0}
    ).sort("created_at", 1).to_list(1000)
    
    for msg in messages:
        if isinstance(msg['created_at'], str):
            msg['created_at'] = datetime.fromisoformat(msg['created_at'])
    
    # Mark as read
    await db.messages.update_many(
        {"chat_id": chat_id, "sender_id": {"$ne": current_user["sub"]}},
        {"$set": {"is_read": True}}
    )
    
    return [Message(**msg) for msg in messages]

@router.post("/messages", response_model=Message)
async def send_message(message: MessageCreate, current_user: dict = Depends(get_current_user)):
    # Verify access to chat
    session = await db.chat_sessions.find_one({"id": message.chat_id}, {"_id": 0})
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    
    if session['admin_id'] != current_user["sub"] and session['student_id'] != current_user["sub"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    message_obj = Message(**message.model_dump())
    message_data = message_obj.model_dump()
    message_data['created_at'] = message_data['created_at'].isoformat()
    
    await db.messages.insert_one(message_data)
    return message_obj

@router.delete("/messages/{message_id}")
async def delete_message(message_id: str, delete_for_everyone: bool = False, current_user: dict = Depends(get_current_user)):
    message = await db.messages.find_one({"id": message_id}, {"_id": 0})
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    # Admin can delete any message, users can delete their own
    if current_user["role"] != "admin" and message['sender_id'] != current_user["sub"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    if delete_for_everyone or current_user["role"] == "admin":
        await db.messages.update_one(
            {"id": message_id},
            {"$set": {"is_deleted": True}}
        )
    
    return {"message": "Message deleted successfully"}