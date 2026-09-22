import re
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import requests

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# RapidAPIの設定情報
RAPIDAPI_KEY = "29d81488fdmsh21f3d3d5b6ba2eap1b9d75jsn3a69ea14ce28"
RAPIDAPI_HOST = "youtube-mp3-audio-video-downloader.p.rapidapi.com"

def extract_video_id(url: str) -> str:
    """YouTube URLから11桁の動画IDを取り出す"""
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

@app.get("/")
def root():
    return {"status": "ok", "message": "MusicSpace Pro Backend"}

@app.get("/api/audio")
def get_audio(url: str = Query(..., description="YouTube URL")):
    try:
        # 1. URLから動画IDを抽出
        video_id = extract_video_id(url)
        if not video_id:
            raise HTTPException(status_code=400, detail="無効なYouTube URLです。")

        # 2. RapidAPIへリクエスト送信
        api_url = f"https://{RAPIDAPI_HOST}/get_m4a_download_link/{video_id}"
        headers = {
            "x-rapidapi-host": RAPIDAPI_HOST,
            "x-rapidapi-key": RAPIDAPI_KEY
        }

        response = requests.get(api_url, headers=headers)
        
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="RapidAPIからの取得に失敗しました。")

        data = response.json()
        # {"file": "https://...", "comment": "..."} からURLを取得
        audio_url = data.get("file")

        if not audio_url:
            raise HTTPException(status_code=400, detail="音声URLが見つかりませんでした。")

        # 3. アプリ側に返すデータ構造
        return {
            "status": "success",
            "url": audio_url,
            "title": "YouTube Audio",
            "duration": 0
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))