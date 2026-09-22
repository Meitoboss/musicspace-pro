import os
import shutil
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

# --- yt-dlp 共通設定（Read-only回避 & ローカル両対応） ---
SECRET_COOKIE = '/etc/secrets/cookies.txt'
LOCAL_COOKIE = 'cookies.txt'
TMP_COOKIE = '/tmp/cookies.txt'

COOKIE_FILE = None

if os.path.exists(SECRET_COOKIE):
    try:
        shutil.copyfile(SECRET_COOKIE, TMP_COOKIE)
        COOKIE_FILE = TMP_COOKIE
        print(f"Copied secret cookie to {TMP_COOKIE}")
    except Exception as e:
        print(f"Failed to copy cookie: {e}")
        COOKIE_FILE = SECRET_COOKIE
elif os.path.exists(LOCAL_COOKIE):
    COOKIE_FILE = LOCAL_COOKIE

BASE_YTDL_OPTS = {
    'quiet': True,
    'no_warnings': True,
    'javascript_runtimes': ['nodejs'],
}

if COOKIE_FILE and os.path.exists(COOKIE_FILE):
    BASE_YTDL_OPTS['cookiefile'] = COOKIE_FILE
    print(f"Loaded cookie file: {COOKIE_FILE}")
else:
    print(f"Warning: Cookie file NOT found")

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

# 音声ストリームURLを取得する関数 (Bot対策強化 + 複数代替API自動フォールバック)
async def get_audio_stream_info(video_id: str):
    # 【方法1】yt-dlp で取得（tv_embedded / android_vr 等を優先してBot回避）
    player_clients_to_try = [
        ['tv_embedded', 'android_vr', 'web_embedded'],
        ['ios', 'mweb', 'web_creator'],
    ]

    for clients in player_clients_to_try:
        try:
            url = f"https://www.youtube.com/watch?v={video_id}"
            ydl_opts = {
                **BASE_YTDL_OPTS,
                'format': 'bestaudio[ext=m4a]/bestaudio',
                'extractor_args': {
                    'youtube': {
                        'player_client': clients,
                    }
                }
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if info and 'url' in info:
                    return info['url'], info.get('http_headers', {})
        except Exception as e:
            print(f"yt-dlp (clients={clients}) 失敗: {e}")

    print("yt-dlpが失敗したため、Piped / Invidious API に切り替えます")

    # 【方法2】最新 Piped API インスタンス群
    piped_instances = [
        "https://pipedapi.tokhmi.xyz",
        "https://pipedapi.syncpundit.io",
        "https://pipedapi.moomoo.me",
        "https://pipedapi.kavin.rocks",
        "https://api.piped.privacydev.net",
    ]

    async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
        for instance in piped_instances:
            try:
                res = await client.get(f"{instance}/streams/{video_id}")
                if res.status_code == 200:
                    data = res.json()
                    audio_streams = data.get("audioStreams", [])
                    if audio_streams:
                        m4a_stream = next((s for s in audio_streams if s.get("mimeType") == "audio/mp4"), audio_streams[0])
                        return m4a_stream["url"], {"User-Agent": "Mozilla/5.0"}
            except Exception as e:
                print(f"Piped ({instance}) エラー: {e}")

    # 【方法3】Invidious API インスタンス群 (追加のバックアップ)
    invidious_instances = [
        "https://inv.tux.pizza",
        "https://invidious.nerdvpn.de",
        "https://invidious.drgns.space",
    ]

    async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
        for instance in invidious_instances:
            try:
                res = await client.get(f"{instance}/api/v1/videos/{video_id}")
                if res.status_code == 200:
                    data = res.json()
                    adaptive_formats = data.get("adaptiveFormats", [])
                    audio_streams = [f for f in adaptive_formats if f.get("type", "").startswith("audio/")]
                    if audio_streams:
                        m4a_stream = next((s for s in audio_streams if "container=m4a" in s.get("type", "") or s.get("encoding") == "aac"), audio_streams[0])
                        return m4a_stream["url"], {"User-Agent": "Mozilla/5.0"}
            except Exception as e:
                print(f"Invidious ({instance}) エラー: {e}")

    raise RuntimeError("すべてのソース（yt-dlp, Piped, Invidious）から音声の取得に失敗しました。")

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
        'extractor_args': {
            'youtube': {
                'player_client': ['tv_embedded', 'android_vr', 'web_embedded'],
            }
        }
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