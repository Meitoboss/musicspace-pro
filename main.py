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
    print(f"--- 音源抽出リクエスト受信: {v} ---")
    
    # YouTubeのボット対策を回避するためにiOS/mwebクライアントを偽装
    cmd = [
        "yt-dlp",
        "-g",
        "-f", "ba[ext=m4a]/ba/b",
        "--extractor-args", "youtube:player_client=ios,mweb",
        "--no-warnings",
        yt_url
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        urls = result.stdout.strip().split('\n')
        direct_url = urls[0] if urls else ""
        
        if direct_url:
            print(f"抽出成功!")
            return {"status": "ok", "url": direct_url}
        else:
            print("エラー: 抽出結果のURLが空でした")
            return {"status": "error", "message": "URLを取得できませんでした"}

    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.strip() if e.stderr else e.stdout.strip()
        print(f"yt-dlp実行エラー: {error_msg}")
        return {"status": "error", "message": f"yt-dlpエラー: {error_msg}"}
    except Exception as e:
        print(f"予期せぬエラー: {str(e)}")
        return {"status": "error", "message": str(e)}