import os
import logging
import google.generativeai as genai
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv
from utils import extract_python_code
import subprocess
import uuid
import shutil

load_dotenv()

GOOGLE_API = os.getenv("GOOGLE_API_KEY")


logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

app = FastAPI()

os.makedirs("static/videos", exist_ok=True)
os.makedirs("temp_scenes",exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")

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
    

    manim_prompt = f"""
You are a Python developer using the Manim library.

Generate Python code that creates a short animation based on the following description: "{request.message}"

Requirements:
- The code must define a class named `GeneratedScene` that inherits from `Scene`
- Only output the code inside a markdown block that begins with ```python and ends with ```
- Do NOT include any explanations, comments, or text outside the code block
- Keep the animation under 10 seconds unless specified and visually simple

Respond with only the Manim code.

"""
    try:
        response = model.generate_content(manim_prompt)
        mainm_code = extract_python_code(response.text)
        if not mainm_code:
            logger.error("LLM failed to generate code")

        scene_id = str(uuid.uuid4())
        script_path = os.path.join("temp_scenes", f"scene_{scene_id}.py")
        with open(script_path, "w") as s:
            s.write("from manim import *\n\n" + mainm_code)
        try:
            command = [
                "manim",
                "-ql",
                script_path,
                "GeneratedScene",
            ]

            result = subprocess.run(command, check=True, capture_output=True, text=True)
            
            logger.info(result.stdout)

            video_name = "GeneratedScene.mp4"

            source_vid = os.path.join("media", "videos", f"scene_{scene_id}", "480p15", video_name)
            if not os.path.exists(source_vid):
                logger.error(f"Expected video file not found at {source_vid}")
                raise FileNotFoundError("Expected video file was not produced")

            final_vid = f"{scene_id}.mp4"
            final_destination = os.path.join("static", "videos", final_vid)
            shutil.move(source_vid, final_destination)
            vid_url = f"/static/videos/{final_vid}"

            return {
                "role": "LLM",
                "content": "Here ya go!",
                "type": "video",
                "url": vid_url,
            }

        except subprocess.CalledProcessError as e:
            logger.error(f"Manim command failed: {e.stderr}")
            raise HTTPException(status_code=500, detail=f"Could not render file: {e.stderr}")

    except Exception as e:
        logger.error(f"Error generating content from Gemini: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating content {e}")