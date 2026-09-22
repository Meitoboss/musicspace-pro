import re
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import innertube
import yt_dlp

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# InnerTube クライアント初期化 (YouTube Music クライアント)
ytm_client = innertube.InnerTube("WEB_REMIX")

def extract_video_id(url: str) -> str:
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11})',
        r'youtu\.be\/([0-9A-Za-z_-]{11})'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    if len(url) == 11 and re.match(r'^[0-9A-Za-z_-]{11}$', url):
        return url
    return url

def fetch_audio_via_innertube(video_url: str):
    # 公式iOS/Android MusicアプリのInnerTubeクライアントになりすまして抽出
    ydl_opts = {
        'format': 'm4a/bestaudio/best',
        'quiet': True,
        'no_warnings': True,
        'extractor_args': {
            'youtube': {
                'player_client': ['ios', 'android_music']
            }
        }
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=False)
        audio_url = info.get('url')

        if not audio_url:
            raise HTTPException(status_code=400, detail="音声URLの取得に失敗しました。")

        # iOS ATS対策 (http -> https)
        if audio_url.startswith("http://"):
            audio_url = audio_url.replace("http://", "https://", 1)

        return {
            "status": "ok",
            "result": "success",
            "success": True,
            "code": 200,
            "message": "ok",
            "url": audio_url,
            "audioUrl": audio_url,
            "audio_url": audio_url,
            "stream_url": audio_url,
            "title": info.get("title", "YouTube Audio"),
            "artist": info.get("uploader", "YouTube"),
            "duration": info.get("duration", 0),
            "data": {
                "status": "ok",
                "url": audio_url,
                "audioUrl": audio_url,
                "audio_url": audio_url
            }
        }

@app.get("/")
def root():
    return {"status": "ok", "message": "InnerTube Powered Backend"}

# GET リクエスト対応
@app.get("/api/audio")
def get_audio(url: str = Query(..., description="YouTube URL or Video ID")):
    try:
        return fetch_audio_via_innertube(url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# POST リクエスト対応
class AudioBody(BaseModel):
    url: str = None
    youtubeUrl: str = None
    youtube_url: str = None

@app.post("/api/audio")
def post_audio(body: AudioBody):
    target_url = body.url or body.youtubeUrl or body.youtube_url
    if not target_url:
        raise HTTPException(status_code=400, detail="URLが指定されていません。")
    try:
        return fetch_audio_via_innertube(target_url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))