from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import subprocess

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"status": "ok", "message": "yt-dlp API is running"}

@app.get("/audio")
def get_audio_url(v: str):
    yt_url = f"https://www.youtube.com/watch?v={v}"
    # yt-dlpでm4a音源の直リンクを取得
    cmd = ["yt-dlp", "-g", "-f", "ba[ext=m4a]/ba", yt_url]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        direct_url = result.stdout.strip().split('\n')[0]
        return {"status": "ok", "url": direct_url}
    except Exception as e:
        return {"status": "error", "message": str(e)}