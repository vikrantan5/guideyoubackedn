from fastapi import APIRouter, HTTPException, Depends
from utils.auth import get_current_user
from pydantic import BaseModel
import os
from dotenv import load_dotenv
from pathlib import Path
from groq import Groq
import base64

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
        api_key = os.environ.get('GROQ_API_KEY')
        if not api_key:
            raise HTTPException(status_code=500, detail="AI service not configured")
        
        # Initialize Groq client
        client = Groq(api_key=api_key)
        
        # Decode base64 image
        image_data = request.image_base64
        if ',' in image_data:
            image_data = image_data.split(',')[1]
        
        # Create prompt with educational context
        full_prompt = f"""You are an educational AI assistant that provides constructive feedback on student work.

{request.prompt}

Based on the provided image, provide detailed, encouraging feedback that:
- Highlights what was done well
- Identifies areas for improvement
- Offers specific suggestions
- Maintains a supportive tone"""
        
        # Generate response with image using vision model
        response = client.chat.completions.create(
            model="llama-3.2-90b-vision-preview",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": full_prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_data}"
                            }
                        }
                    ]
                }
            ],
            temperature=0.7,
            max_tokens=1024
        )
        
        return {"feedback": response.choices[0].message.content}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI analysis failed: {str(e)}")

@router.post("/doubt-solver")
async def doubt_solver(request: ChatRequest, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "student":
        raise HTTPException(status_code=403, detail="Not authorized")
    
    try:
        api_key = os.environ.get('GROQ_API_KEY')
        if not api_key:
            raise HTTPException(status_code=500, detail="AI service not configured")
        
        # Initialize Groq client
        client = Groq(api_key=api_key)
        
        # System instruction
        system_instruction = "You are a helpful educational AI assistant. Answer student questions clearly and concisely. Encourage learning by explaining concepts rather than just giving answers. Be supportive and patient."
        
        # Generate response
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": request.question}
            ],
            temperature=0.7,
            max_tokens=1024
        )
        
        return {"answer": response.choices[0].message.content}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI chat failed: {str(e)}")