from fastapi import APIRouter, HTTPException, Depends
from utils.auth import get_current_user
from pydantic import BaseModel
import os
from dotenv import load_dotenv
from pathlib import Path
from google import genai
from google.genai import types
import base64
from PIL import Image
from io import BytesIO

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')

router = APIRouter()

class ImageAnalysisRequest(BaseModel):
    image_base64: str
    prompt: str = "Analyze this student's work and provide constructive feedback. Focus on quality, clarity, and effort."

class ChatRequest(BaseModel):
    question: str
    chat_history: list = []

@router.post("/analyze-image")
async def analyze_image(request: ImageAnalysisRequest, current_user: dict = Depends(get_current_user)):
    try:
        api_key = os.environ.get('GEMINI_API_KEY')
        if not api_key:
            raise HTTPException(status_code=500, detail="AI service not configured")
        
        # Initialize Gemini client
        client = genai.Client(api_key=api_key)
        
        # Decode base64 image
        image_data = request.image_base64
        if ',' in image_data:
            image_data = image_data.split(',')[1]
        
        image_bytes = base64.b64decode(image_data)
        image = Image.open(BytesIO(image_bytes))
        
        # Save to temporary bytes for upload
        img_byte_arr = BytesIO()
        image.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        
        # Create prompt with educational context
        full_prompt = f"""You are an educational AI assistant that provides constructive feedback on student work.

{request.prompt}

Provide detailed, encouraging feedback that:
- Highlights what was done well
- Identifies areas for improvement
- Offers specific suggestions
- Maintains a supportive tone"""
        
        # Generate response with image
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text=full_prompt),
                        types.Part.from_bytes(data=img_byte_arr.read(), mime_type="image/png")
                    ]
                )
            ]
        )
        
        return {"feedback": response.text}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI analysis failed: {str(e)}")

@router.post("/doubt-solver")
async def doubt_solver(request: ChatRequest, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "student":
        raise HTTPException(status_code=403, detail="Not authorized")
    
    try:
        api_key = os.environ.get('GEMINI_API_KEY')
        if not api_key:
            raise HTTPException(status_code=500, detail="AI service not configured")
        
        # Initialize Gemini client
        client = genai.Client(api_key=api_key)
        
        # System instruction
        system_instruction = "You are a helpful educational AI assistant. Answer student questions clearly and concisely. Encourage learning by explaining concepts rather than just giving answers. Be supportive and patient."
        
        # Generate response
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=f"{system_instruction}\n\nStudent Question: {request.question}")]
                )
            ]
        )
        
        return {"answer": response.text}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI chat failed: {str(e)}")