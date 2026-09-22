import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------------------
# 音声ストリーム直URL 取得ロジック (InnerTube APIでBot回避)
# -------------------------------------------------------------

async def get_audio_url_from_innertube(video_id: str):
    """InnerTube (Android/TV) から音声直URL(m4a)を抽出"""
    clients = [
        {
            "name": "ANDROID",
            "version": "19.29.37",
            "ua": "com.google.android.youtube/19.29.37 (Linux; U; Android 11; ja_JP)"
        },
        {
            "name": "TVHTML5_SIMPLY_EMBEDDED_PLAYER",
            "version": "2.0",
            "ua": "Mozilla/5.0 (SmartHub; SMART-TV; U; Linux/SmartTV) AppleWebKit/537.42"
        }
    ]

    for c in clients:
        url = "https://www.youtube.com/youtubei/v1/player"
        payload = {
            "videoId": video_id,
            "context": {
                "client": {
                    "clientName": c["name"],
                    "clientVersion": c["version"],
                    "hl": "ja",
                    "gl": "JP"
                }
            }
        }
        headers = {
            "User-Agent": c["ua"],
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=8.0, verify=False) as client:
                res = await client.post(url, json=payload, headers=headers)
                if res.status_code == 200:
                    data = res.json()
                    adaptive_formats = data.get("streamingData", {}).get("adaptiveFormats", [])
                    audio_formats = [
                        f for f in adaptive_formats 
                        if f.get("mimeType", "").startswith("audio/") and "url" in f
                    ]
                    if audio_formats:
                        # 最高音質のm4a/audioストリームを選択
                        best = sorted(audio_formats, key=lambda x: x.get("bitrate", 0), reverse=True)[0]
                        return best["url"]
        except Exception as e:
            print(f"InnerTube Error ({c['name']}): {e}")

    # フォールバック: Cobalt API
    try:
        async with httpx.AsyncClient(timeout=8.0, verify=False) as client:
            res = await client.post(
                "https://api.cobalt.tools/",
                json={"url": f"https://www.youtube.com/watch?v={video_id}", "downloadMode": "audio", "audioFormat": "m4a"},
                headers={"Accept": "application/json", "Content-Type": "application/json"}
            )
            if res.status_code in (200, 201):
                data = res.json()
                if "url" in data:
                    return data["url"]
    except Exception as e:
        print(f"Cobalt Error: {e}")

    return None

# -------------------------------------------------------------
# API エンドポイント
# -------------------------------------------------------------

# 1. 音声直URL取得API (iOSアプリ用)
@app.get("/api/audio")
async def get_audio(v: str):
    audio_url = await get_audio_url_from_innertube(v)
    if not audio_url:
        raise HTTPException(status_code=500, detail="Audio URL extraction failed")
    return {
        "status": "success",
        "video_id": v,
        "audio_url": audio_url
    }

# 2. 検索API (iOSアプリ用)
@app.get("/api/search")
async def search(q: str):
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
                            if len(results) >= 15:
                                break
                    if len(results) >= 15:
                        break
                return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))