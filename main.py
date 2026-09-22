from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import requests

app = FastAPI()

# アプリ（Capacitor）からの通信を許可するCORS設定
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
        # 1. 外部のYouTube変換APIを呼び出す
        # (※実際にお使いの変換APIのURLに変更してください)
        response = requests.get(f"https://your-converter-api.com/fetch?url={url}")
        api_data = response.json()

        # 2. 取得したデータから音声URLとタイトルを取り出す
        audio_url = api_data.get("link")
        title = api_data.get("title", "Unknown Title")
        duration = api_data.get("duration", 0)

        if not audio_url:
            raise HTTPException(status_code=400, detail="音声URLの取得に失敗しました。")

        # 3. アプリ側にデータを返す
        return {
            "status": "success",
            "url": audio_url,
            "title": title,
            "duration": duration
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))