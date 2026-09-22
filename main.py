from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import yt_dlp

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"status": "ok", "message": "MusicSpace Pro Backend"}

@app.get("/api/audio")
def get_audio(url: str = Query(..., description="YouTube URL")):
    try:
        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'no_warnings': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            audio_url = info.get('url')
            title = info.get('title', 'Unknown Title')
            duration = info.get('duration', 0)

            if not audio_url:
                raise HTTPException(status_code=400, detail="音声URLの取得に失敗しました。")

            return {
                "status": "success",
                "url": audio_url,
                "title": title,
                "duration": duration
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))