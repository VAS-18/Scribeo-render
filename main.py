import os
import logging
from typing import Optional
import google.generativeai as genai
from google.genai import types
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

GOOGLE_API = os.getenv("GOOGLE_API_KEY")


logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

app = FastAPI()

os.makedirs("static/videos", exist_ok=True)
os.makedirs("temp_scenes",exist_ok=True)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


if not GOOGLE_API:
    logger.error("Google Api key not found")
    raise RuntimeError("Missing Google Api key")


try:
    genai.configure(api_key=GOOGLE_API)
    model = genai.GenerativeModel('gemini-2.5-pro')
except Exception as e:
    logger.error(f"Failed to configure Gemini API: {e}")
    raise

class RenderRequest(BaseModel):
    message: str

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.post("/render")
async def render_vid(request: RenderRequest):
    if not request.message or not request.message.strip():
        raise HTTPException(status_code=400,detail="Message cannot be empty")
    
    try:
        response = model.generate_content(request.message)
        return {"role":"LLM","content":response.text}
    except Exception as e:
        logger.error(f"Error generating content from Gemini: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating content {e}")