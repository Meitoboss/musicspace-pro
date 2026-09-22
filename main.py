import os
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx
import yt_dlp

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- yt-dlp 共通設定（cookies.txt と Node.js サポートの統合） ---
COOKIE_FILE = 'cookies.txt'

BASE_YTDL_OPTS = {
    'quiet': True,
    'no_warnings': True,
    'javascript_runtimes': ['nodejs'],
}

if os.path.exists(COOKIE_FILE):
    BASE_YTDL_OPTS['cookiefile'] = COOKIE_FILE
    print(f"Loaded cookie file: {COOKIE_FILE}")

@app.get("/")
def home():
    return {"status": "ok"}

# 1. 既存の Web View用 iframe プレイヤー
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

# 音声ストリームURLを取得する関数 (Bot対策 + 自動フォールバック)
async def get_audio_stream_info(video_id: str):
    # 【方法1】yt-dlp で取得を試みる (cookies.txt & Node.js 統合版)
    try:
        url = f"https://www.youtube.com/watch?v={video_id}"
        ydl_opts = {
            **BASE_YTDL_OPTS,
            'format': 'bestaudio[ext=m4a]/bestaudio',
            'extractor_args': {
                'youtube': {
                    'player_client': ['ios', 'android', 'mweb'],
                }
            }
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info['url'], info.get('http_headers', {})
    except Exception as e:
        print(f"yt-dlp 失敗: {e} -> Piped API に自動切り替えします")

    # 【方法2】yt-dlp が失敗した場合、Piped API (分散代替API) から取得する
    piped_instances = [
        "https://pipedapi.kavin.rocks",
        "https://api.piped.privacydev.net",
        "https://pipedapi.mha.fi"
    ]
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        for instance in piped_instances:
            try:
                res = await client.get(f"{instance}/streams/{video_id}")
                if res.status_code == 200:
                    data = res.json()
                    audio_streams = data.get("audioStreams", [])
                    if audio_streams:
                        # m4a(AAC)形式のストリームを優先的に探す
                        m4a_stream = next((s for s in audio_streams if s.get("mimeType") == "audio/mp4"), audio_streams[0])
                        return m4a_stream["url"], {"User-Agent": "Mozilla/5.0"}
            except Exception:
                continue

    raise RuntimeError("すべてのソースから音声の取得に失敗しました。")

# 2. モバイルアプリ用 音声ストリームプロキシ
@app.get("/api/proxy/{video_id}")
async def proxy_audio(video_id: str, request: Request):
    try:
        stream_url, headers = await get_audio_stream_info(video_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    req_headers = {
        "User-Agent": headers.get("User-Agent", "Mozilla/5.0"),
    }
    if "range" in request.headers:
        req_headers["Range"] = request.headers["range"]

    client = httpx.AsyncClient()
    req = client.build_request("GET", stream_url, headers=req_headers)
    r = await client.send(req, stream=True)

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

# 3. 楽曲検索API
@app.get("/api/search")
async def search_music(q: str):
    ydl_opts = {
        **BASE_YTDL_OPTS,
        'extract_flat': True,
        'skip_download': True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch5:{q}", download=False)
            results = []
            for entry in info.get('entries', []):
                results.append({
                    "id": entry.get("id"),
                    "title": entry.get("title"),
                    "uploader": entry.get("uploader", "Unknown Artist"),
                    "duration": entry.get("duration"),
                    "thumbnail": f"https://i.ytimg.com/vi/{entry.get('id')}/hqdefault.jpg"
                })
            return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")