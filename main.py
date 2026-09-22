from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import requests

app = FastAPI()

# Capacitor（WKWebView）からのアクセスを許可するCORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"status": "ok", "message": "MusicSpace Pro Backend Running"}

@app.get("/api/audio")
def get_audio(url: str = Query(..., description="YouTubeの動画URL")):
    try:
        # ※外部APIを呼び出す処理（すでにお使いのAPI呼び出し部分）
        # 例:
        # response = requests.get(f"https://your-converter-api.com/fetch?url={url}")
        # data = response.json()
        
        # 取得できたJSONレスポンス（link, title, duration）から整形して返却
        # もし手元で `data` 変数に外部APIのレスポンスが入っている場合:
        audio_url = data.get("link")
        title = data.get("title", "Unknown Title")
        duration = data.get("duration", 0)

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