import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

def register_socket_events(sio, db):
    @sio.event
    async def connect(sid, environ):
        logger.info(f"Client connected: {sid}")
    
    @sio.event
    async def disconnect(sid):
        logger.info(f"Client disconnected: {sid}")
    
    @sio.event
    async def join_chat(sid, data):
        chat_id = data.get('chat_id')
        user_id = data.get('user_id')
        
        if not chat_id or not user_id:
            return {"error": "Missing chat_id or user_id"}
        
        # Verify access
        session = await db.chat_sessions.find_one({"id": chat_id}, {"_id": 0})
        if not session:
            return {"error": "Chat session not found"}
        
        if session['admin_id'] != user_id and session['student_id'] != user_id:
            return {"error": "Not authorized"}
        
        await sio.enter_room(sid, chat_id)
        logger.info(f"User {user_id} joined chat {chat_id}")
        return {"status": "joined"}
    
    @sio.event
    async def leave_chat(sid, data):
        chat_id = data.get('chat_id')
        await sio.leave_room(sid, chat_id)
        logger.info(f"Socket {sid} left chat {chat_id}")
    
    @sio.event
    async def send_message(sid, data):
        chat_id = data.get('chat_id')
        sender_id = data.get('sender_id')
        content = data.get('content')
        message_type = data.get('message_type', 'text')
        
        if not all([chat_id, sender_id, content]):
            return {"error": "Missing required fields"}
        
        # Create message
        from models.chat import Message
        message_obj = Message(
            chat_id=chat_id,
            sender_id=sender_id,
            content=content,
            message_type=message_type
        )
        
        message_data = message_obj.model_dump()
        message_data['created_at'] = message_data['created_at'].isoformat()
        
        await db.messages.insert_one(message_data)
        
        # Broadcast to room
        await sio.emit('new_message', message_obj.model_dump(mode='json'), room=chat_id)
        logger.info(f"Message sent in chat {chat_id}")
        
        return {"status": "sent", "message_id": message_obj.id}
    
    @sio.event
    async def typing(sid, data):
        chat_id = data.get('chat_id')
        user_id = data.get('user_id')
        is_typing = data.get('is_typing', True)
        
        await sio.emit('user_typing', {
            'user_id': user_id,
            'is_typing': is_typing
        }, room=chat_id, skip_sid=sid)
    
    @sio.event
    async def mark_read(sid, data):
        chat_id = data.get('chat_id')
        user_id = data.get('user_id')
        
        # Mark messages as read
        await db.messages.update_many(
            {"chat_id": chat_id, "sender_id": {"$ne": user_id}, "is_read": False},
            {"$set": {"is_read": True}}
        )
        
        await sio.emit('messages_read', {'user_id': user_id}, room=chat_id)