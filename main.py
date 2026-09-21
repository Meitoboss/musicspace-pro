import os
import subprocess
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

COOKIE_FILE_PATH = "/tmp/youtube_cookies.txt"

def setup_cookies():
    cookie_data = os.getenv("YOUTUBE_COOKIES", "")
    if cookie_data:
        try:
            with open(COOKIE_FILE_PATH, "w", encoding="utf-8") as f:
                f.write(cookie_data)
            print("cookies.txt の生成に成功しました。")
        except Exception as e:
            print(f"クッキーファイルの書き込みエラー: {e}")

@app.on_event("startup")
def startup_event():
    setup_cookies()

@app.get("/")
def home():
    return {"status": "ok", "message": "yt-dlp API with Cookies is running"}

@app.get("/audio")
def get_audio_url(v: str):
    yt_url = f"https://www.youtube.com/watch?v={v}"
    
    # 毎回最新の環境変数からクッキーファイルをチェック/更新
    setup_cookies()
    cookie_exists = os.path.exists(COOKIE_FILE_PATH)
    
    cmd = [
        "yt-dlp",
        "-g",
        "-f", "ba[ext=m4a]/ba/b",
        "--no-warnings",
        "--extractor-args", "youtube:player_client=ios,mweb"
    ]
    
    if cookie_exists:
        cmd.extend(["--cookies", COOKIE_FILE_PATH])
        
    cmd.append(yt_url)
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        urls = result.stdout.strip().split('\n')
        direct_url = urls[0] if urls else ""
        
        if direct_url:
            return {"status": "ok", "url": direct_url}
        else:
            return {"status": "error", "message": "音源URLが空でした"}

    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.strip() if e.stderr else e.stdout.strip()
        return {"status": "error", "message": f"yt-dlp error: {error_msg}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}