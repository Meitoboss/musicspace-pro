import os
import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import yt_dlp

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------------------
# 音声ストリームURL 多重取得ロジック (Bot判定回避 & 超高速)
# -------------------------------------------------------------

async def get_audio_from_innertube_android(video_id: str):
    """1. InnerTube API (Android Client) - Bot回避率最高レベル"""
    url = "https://www.youtube.com/youtubei/v1/player"
    payload = {
        "videoId": video_id,
        "context": {
            "client": {
                "clientName": "ANDROID",
                "clientVersion": "19.29.37",
                "androidSdkVersion": 30,
                "hl": "ja",
                "gl": "JP"
            }
        }
    }
    headers = {
        "User-Agent": "com.google.android.youtube/19.29.37 (Linux; U; Android 11; ja_JP)",
        "Content-Type": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=8.0, verify=False) as client:
            res = await client.post(url, json=payload, headers=headers)
            if res.status_code == 200:
                data = res.json()
                streaming_data = data.get("streamingData", {})
                adaptive_formats = streaming_data.get("adaptiveFormats", [])
                
                audio_formats = [
                    f for f in adaptive_formats 
                    if f.get("mimeType", "").startswith("audio/") and "url" in f
                ]
                if audio_formats:
                    best = sorted(audio_formats, key=lambda x: x.get("bitrate", 0), reverse=True)[0]
                    return best["url"]
    except Exception as e:
        print(f"InnerTube Android error: {e}")
    return None

async def get_audio_from_innertube_tv(video_id: str):
    """2. InnerTube API (TV Client)"""
    url = "https://www.youtube.com/youtubei/v1/player"
    payload = {
        "videoId": video_id,
        "context": {
            "client": {
                "clientName": "TVHTML5_SIMPLY_EMBEDDED_PLAYER",
                "clientVersion": "2.0",
                "hl": "ja",
                "gl": "JP"
            }
        }
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (SmartHub; SMART-TV; U; Linux/SmartTV) AppleWebKit/537.42",
        "Content-Type": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=8.0, verify=False) as client:
            res = await client.post(url, json=payload, headers=headers)
            if res.status_code == 200:
                data = res.json()
                streaming_data = data.get("streamingData", {})
                adaptive_formats = streaming_data.get("adaptiveFormats", [])
                audio_formats = [
                    f for f in adaptive_formats 
                    if f.get("mimeType", "").startswith("audio/") and "url" in f
                ]
                if audio_formats:
                    best = sorted(audio_formats, key=lambda x: x.get("bitrate", 0), reverse=True)[0]
                    return best["url"]
    except Exception as e:
        print(f"InnerTube TV error: {e}")
    return None

async def get_audio_from_cobalt(video_id: str):
    """3. Cobalt API"""
    cobalt_instances = [
        "https://api.cobalt.tools",
        "https://cobalt-api.koyeb.app",
    ]
    payload = {
        "url": f"https://www.youtube.com/watch?v={video_id}",
        "downloadMode": "audio",
        "audioFormat": "m4a"
    }
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0"
    }
    async with httpx.AsyncClient(timeout=8.0, verify=False) as client:
        for instance in cobalt_instances:
            try:
                res = await client.post(f"{instance}/", json=payload, headers=headers)
                if res.status_code in (200, 201):
                    data = res.json()
                    if "url" in data:
                        return data["url"]
            except Exception as e:
                print(f"Cobalt ({instance}) error: {e}")
    return None

async def get_audio_from_piped(video_id: str):
    """4. Piped API (SSL証明書エラー無視)"""
    piped_instances = [
        "https://pipedapi.kavin.rocks",
        "https://pipedapi.moomoo.me",
        "https://pipedapi.syncpundit.io",
        "https://piped-api.garudalinux.org",
    ]
    async with httpx.AsyncClient(timeout=8.0, verify=False, follow_redirects=True) as client:
        for instance in piped_instances:
            try:
                res = await client.get(f"{instance}/streams/{video_id}")
                if res.status_code == 200:
                    data = res.json()
                    audio_streams = data.get("audioStreams", [])
                    if audio_streams:
                        m4a_stream = next((s for s in audio_streams if s.get("mimeType") == "audio/mp4"), audio_streams[0])
                        return m4a_stream["url"]
            except Exception as e:
                print(f"Piped ({instance}) error: {e}")
    return None

async def get_audio_stream_info(video_id: str):
    # 順に試行
    url = await get_audio_from_innertube_android(video_id)
    if url:
        return url, {"User-Agent": "com.google.android.youtube/19.29.37"}

    url = await get_audio_from_innertube_tv(video_id)
    if url:
        return url, {"User-Agent": "Mozilla/5.0"}

    url = await get_audio_from_cobalt(video_id)
    if url:
        return url, {"User-Agent": "Mozilla/5.0"}

    url = await get_audio_from_piped(video_id)
    if url:
        return url, {"User-Agent": "Mozilla/5.0"}

    raise RuntimeError("すべてのAPIで音声の取得に失敗しました。")

# -------------------------------------------------------------
# API エンドポイント
# -------------------------------------------------------------

# 1. 音声ストリーミングプロキシ (通信量節約: m4aのみストリーミング)
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

    client = httpx.AsyncClient(verify=False)
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
        background=client.aclose
    )

# 2. 楽曲検索API (InnerTubeで爆速取得)
@app.get("/api/search")
async def search_music(q: str):
    url = "https://www.youtube.com/youtubei/v1/search"
    payload = {
        "query": q,
        "context": {
            "client": {
                "clientName": "WEB",
                "clientVersion": "2.20240320.00.00",
                "hl": "ja",
                "gl": "JP"
            }
        }
    }
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    try:
        async with httpx.AsyncClient(timeout=8.0, verify=False) as client:
            res = await client.post(url, json=payload, headers=headers)
            if res.status_code == 200:
                data = res.json()
                results = []
                contents = data.get("contents", {}).get("twoColumnSearchResultsRenderer", {}).get("primaryContents", {}).get("sectionListRenderer", {}).get("contents", [])
                for section in contents:
                    items = section.get("itemSectionRenderer", {}).get("contents", [])
                    for item in items:
                        v = item.get("videoRenderer")
                        if v:
                            v_id = v.get("videoId")
                            title = v.get("title", {}).get("runs", [{}])[0].get("text", "Unknown")
                            uploader = v.get("ownerText", {}).get("runs", [{}])[0].get("text", "Unknown Artist")
                            if v_id:
                                results.append({
                                    "id": v_id,
                                    "title": title,
                                    "uploader": uploader,
                                    "thumbnail": f"https://i.ytimg.com/vi/{v_id}/hqdefault.jpg"
                                })
                            if len(results) >= 10:
                                break
                    if len(results) >= 10:
                        break
                if results:
                    return {"results": results}
    except Exception as e:
        print(f"InnerTube Search error: {e}")

    # 予備検索: yt-dlp
    try:
        ydl_opts = {'quiet': True, 'extract_flat': True, 'skip_download': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch10:{q}", download=False)
            results = []
            for entry in info.get('entries', []):
                results.append({
                    "id": entry.get("id"),
                    "title": entry.get("title"),
                    "uploader": entry.get("uploader", "Unknown Artist"),
                    "thumbnail": f"https://i.ytimg.com/vi/{entry.get('id')}/hqdefault.jpg"
                })
            return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

# 3. トップページ（スマホ最適化 & バックグラウンド再生機能付き Web 音楽プレイヤー）
@app.get("/", response_class=HTMLResponse)
def home_player():
    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <title>Music Player</title>
        <style>
            * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
            body { background-color: #121212; color: #fff; display: flex; flex-direction: column; height: 100vh; }
            .header { padding: 16px; background: #1e1e1e; text-align: center; font-weight: bold; font-size: 1.2rem; }
            .search-box { padding: 12px; display: flex; gap: 8px; background: #181818; }
            input { flex: 1; padding: 12px; border-radius: 8px; border: none; background: #2a2a2a; color: #fff; font-size: 1rem; }
            button { padding: 12px 16px; border-radius: 8px; border: none; background: #1db954; color: #fff; font-weight: bold; cursor: pointer; }
            .results { flex: 1; overflow-y: auto; padding: 12px; }
            .item { display: flex; align-items: center; gap: 12px; padding: 10px; background: #1e1e1e; margin-bottom: 8px; border-radius: 8px; cursor: pointer; }
            .item img { width: 50px; height: 50px; border-radius: 6px; object-fit: cover; }
            .item-info { flex: 1; overflow: hidden; }
            .item-title { font-size: 0.95rem; font-weight: bold; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
            .item-artist { font-size: 0.8rem; color: #aaa; margin-top: 4px; }
            .player-bar { background: #282828; padding: 12px 16px; display: flex; flex-direction: column; gap: 8px; border-top: 1px solid #333; }
            .now-playing { display: flex; align-items: center; gap: 12px; }
            .now-playing img { width: 42px; height: 42px; border-radius: 4px; }
            audio { width: 100%; height: 36px; margin-top: 4px; }
        </style>
    </head>
    <body>
        <div class="header">🎵 Web Music Player</div>
        <div class="search-box">
            <input type="text" id="searchInput" placeholder="曲名やアーティスト名で検索...">
            <button onclick="search()">検索</button>
        </div>
        <div class="results" id="results"></div>
        <div class="player-bar">
            <div class="now-playing">
                <img id="playerThumb" src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='1' height='1'%3E%3C/svg%3E">
                <div class="item-info">
                    <div class="item-title" id="playerTitle">未再生</div>
                    <div class="item-artist" id="playerArtist">曲を選択してください</div>
                </div>
            </div>
            <audio id="audioPlayer" controls autoplay></audio>
        </div>

        <script>
            async function search() {
                const q = document.getElementById('searchInput').value;
                if (!q) return;
                const resList = document.getElementById('results');
                resList.innerHTML = '<div style="text-align:center; padding:20px; color:#aaa;">検索中...</div>';
                
                try {
                    const res = await fetch(`/api/search?q=${encodeURIComponent(q)}`);
                    const data = await res.json();
                    resList.innerHTML = '';
                    
                    data.results.forEach(item => {
                        const div = document.createElement('div');
                        div.className = 'item';
                        div.onclick = () => playSong(item);
                        div.innerHTML = `
                            <img src="${item.thumbnail}">
                            <div class="item-info">
                                <div class="item-title">${item.title}</div>
                                <div class="item-artist">${item.uploader}</div>
                            </div>
                        `;
                        resList.appendChild(div);
                    });
                } catch(e) {
                    resList.innerHTML = '<div style="text-align:center; padding:20px; color:#f55;">検索失敗</div>';
                }
            }

            function playSong(item) {
                document.getElementById('playerTitle').innerText = item.title;
                document.getElementById('playerArtist').innerText = item.uploader;
                document.getElementById('playerThumb').src = item.thumbnail;
                
                const audio = document.getElementById('audioPlayer');
                audio.src = `/api/proxy/${item.id}`;
                audio.play();

                // ロック画面・通知バーのメディア表示連携 (MediaSession)
                if ('mediaSession' in navigator) {
                    navigator.mediaSession.metadata = new MediaMetadata({
                        title: item.title,
                        artist: item.uploader,
                        artwork: [{ src: item.thumbnail, sizes: '512x512', type: 'image/jpeg' }]
                    });
                }
            }
        </script>
    </body>
    </html>
    """)