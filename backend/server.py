from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import socketio
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create Socket.IO server
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins='*',
    logger=True,
    engineio_logger=True
)

# Create FastAPI app
app = FastAPI(redirect_slashes=False)
api_router = APIRouter(prefix="/api")

# Import routes
from routes.auth import router as auth_router
from routes.users import router as users_router
from routes.tasks import router as tasks_router
from routes.submissions import router as submissions_router
from routes.chat import router as chat_router
from routes.progress import router as progress_router
from routes.announcements import router as announcements_router
from routes.ai import router as ai_router

# Include routers
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(users_router, prefix="/users", tags=["users"])
api_router.include_router(tasks_router, prefix="/tasks", tags=["tasks"])
api_router.include_router(submissions_router, prefix="/submissions", tags=["submissions"])
api_router.include_router(chat_router, prefix="/chat", tags=["chat"])
api_router.include_router(progress_router, prefix="/progress", tags=["progress"])
api_router.include_router(announcements_router, prefix="/announcements", tags=["announcements"])
api_router.include_router(ai_router, prefix="/ai", tags=["ai"])

app.include_router(api_router)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Socket.IO events
from sockets.chat_socket import register_socket_events
register_socket_events(sio, db)

# Add shutdown event before wrapping
@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()

# Wrap app with Socket.IO
socket_app = socketio.ASGIApp(sio, app)

# Make app point to socket_app for uvicorn to serve Socket.IO
app = socket_app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@api_router.get("/")
async def root():
    return {"message": "Student Task Management API"}