import re
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests

app = FastAPI()

# CORS制限を全開放
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

RAPIDAPI_KEY = "29d81488fdmsh21f3d3d5b6ba2eap1b9d75jsn3a69ea14ce28"
RAPIDAPI_HOST = "youtube-mp3-audio-video-downloader.p.rapidapi.com"

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
    return None

def process_audio(url: str):
    video_id = extract_video_id(url)
    if not video_id:
        raise HTTPException(status_code=400, detail="無効なYouTube URLです。")

    api_url = f"https://{RAPIDAPI_HOST}/get_m4a_download_link/{video_id}"
    headers = {
        "x-rapidapi-host": RAPIDAPI_HOST,
        "x-rapidapi-key": RAPIDAPI_KEY
    }

    response = requests.get(api_url, headers=headers)
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="RapidAPIからの取得に失敗しました。")

    data = response.json()
    audio_url = data.get("file")

    if not audio_url:
        raise HTTPException(status_code=400, detail="音声URLが見つかりませんでした。")

    # iOSのHTTP通信制限対策 (http -> https)
    if audio_url.startswith("http://"):
        audio_url = audio_url.replace("http://", "https://", 1)

    # アプリ側がどの構造・キー名を求めていても合致するよう全パターン返却
    return {
        "status": "success",
        "success": True,
        "code": 200,
        "url": audio_url,
        "audioUrl": audio_url,
        "audio_url": audio_url,
        "link": audio_url,
        "download_url": audio_url,
        "src": audio_url,
        "title": "YouTube Audio",
        "duration": 0,
        "data": {
            "url": audio_url,
            "audioUrl": audio_url,
            "audio_url": audio_url,
            "link": audio_url
        }
    }

@app.get("/")
def root():
    return {"status": "ok", "message": "MusicSpace Pro Backend"}

# 1. GET リクエスト（クエリパラメータ）対応
@app.get("/api/audio")
def get_audio(url: str = Query(..., description="YouTube URL")):
    return process_audio(url)

# 2. POST リクエスト（JSONボディ）対応
class AudioBody(BaseModel):
    url: str = None
    youtubeUrl: str = None
    youtube_url: str = None

@app.post("/api/audio")
def post_audio(body: AudioBody):
    target_url = body.url or body.youtubeUrl or body.youtube_url
    if not target_url:
        raise HTTPException(status_code=400, detail="URLが指定されていません。")
    return process_audio(target_url)