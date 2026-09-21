from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx
import yt_dlp

app = FastAPI()

# CORS許可設定（アプリやWebからのリクエストを許可）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"status": "ok"}

# ==========================================
# 1. 既存機能：Web View用 iframe プレイヤー
# ==========================================
@app.get("/player", response_class=HTMLResponse)
def player_page(v: str):
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta name="referrer" content="strict-origin-when-cross-origin">
        <style>
            body, html {{ margin: 0; padding: 0; width: 100%; height: 100%; background: #000; overflow: hidden; }}
            iframe {{ width: 100%; height: 100%; border: 0; }}
        </style>
    </head>
    <body>
        <iframe id="yt" 
                src="https://www.youtube-nocookie.com/embed/{v}?enablejsapi=1&autoplay=1&playsinline=1&controls=0&rel=0" 
                allow="autoplay; encrypted-media" 
                referrerpolicy="strict-origin-when-cross-origin"
                allowfullscreen></iframe>
        <script>
            window.addEventListener('message', function(e) {{
                var iframe = document.getElementById('yt');
                if (iframe && iframe.contentWindow) {{
                    iframe.contentWindow.postMessage(e.data, '*');
                }}
            }});
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

# ==========================================
# 2. 新機能：モバイルアプリ用 バックグラウンド音声ストリーム (403回避プロキシ)
# ==========================================
def _get_youtube_audio_info(video_id: str):
    url = f"https://www.youtube.com/watch?v={video_id}"
    ydl_opts = {
        'format': 'bestaudio[ext=m4a]/bestaudio',  # iOS/Android共に再生可能なm4aを優先
        'quiet': True,
        'no_warnings': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return info['url'], info.get('http_headers', {})

@app.get("/api/proxy/{video_id}")
async def proxy_audio(video_id: str, request: Request):
    try:
        # yt-dlp で音声直URLと要求ヘッダーを取得
        stream_url, headers = _get_youtube_audio_info(video_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"yt-dlp error: {str(e)}")

    # アプリ側からのRangeヘッダー（シーク再生用）を保持して転送
    req_headers = {
        "User-Agent": headers.get("User-Agent", "Mozilla/5.0"),
    }
    if "range" in request.headers:
        req_headers["Range"] = request.headers["range"]

    client = httpx.AsyncClient()
    req = client.build_request("GET", stream_url, headers=req_headers)
    r = await client.send(req, stream=True)

    # サーバー経由で音声データをストリーミング返却（IPバインドによる403回避）
    return StreamingResponse(
        r.aiter_raw(),
        status_code=r.status_code,
        headers={
            "Content-Type": r.headers.get("Content-Type", "audio/mp4"),
            "Content-Length": r.headers.get("Content-Length", ""),
            "Accept-Ranges": r.headers.get("Accept-Ranges", "bytes"),
            "Content-Range": r.headers.get("Content-Range", ""),
        },
        background=httpx.AsyncClient().aclose
    )