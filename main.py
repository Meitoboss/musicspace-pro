from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()

# 1. /player へのアクセス用（埋め込みプレイヤー）
@app.get("/player", response_class=HTMLResponse)
def player_page(v: str = ""):
    return HTMLResponse(content=f"""
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body, html {{ margin: 0; padding: 0; width: 100%; height: 100%; background: #000; overflow: hidden; }}
            iframe {{ width: 100%; height: 100%; border: 0; }}
        </style>
    </head>
    <body>
        <iframe src="https://www.youtube-nocookie.com/embed/{v}?autoplay=1&playsinline=1&controls=1" 
                allow="autoplay; encrypted-media" 
                allowfullscreen></iframe>
    </body>
    </html>
    """)

# 2. トップページ ( Web 音楽プレイヤー )
@app.get("/", response_class=HTMLResponse)
def index():
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
        .status { text-align: center; padding: 20px; color: #aaa; font-size: 0.9rem; }
    </style>
</head>
<body>
    <div class="header">🎵 Web Music Player</div>
    <div class="search-box">
        <input type="text" id="searchInput" placeholder="曲名やアーティスト名で検索...">
        <button onclick="search()">検索</button>
    </div>
    <div class="results" id="results">
        <div class="status">曲名を入力して検索してください</div>
    </div>
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
        const PIPED_INSTANCES = [
            "https://pipedapi.kavin.rocks",
            "https://pipedapi.tokhmi.xyz",
            "https://pipedapi.moomoo.me",
            "https://pipedapi.syncpundit.io"
        ];

        async function fetchWithFallback(path) {
            for (const instance of PIPED_INSTANCES) {
                try {
                    const res = await fetch(instance + path);
                    if (res.ok) return await res.json();
                } catch (e) {
                    console.warn(`Failed: ${instance}`);
                }
            }
            throw new Error("API接続エラー");
        }

        async function search() {
            const q = document.getElementById('searchInput').value.trim();
            if (!q) return;
            const resList = document.getElementById('results');
            resList.innerHTML = '<div class="status">検索中...</div>';

            try {
                const data = await fetchWithFallback(`/search?q=${encodeURIComponent(q)}&filter=music`);
                resList.innerHTML = '';
                const items = data.items || [];

                if (items.length === 0) {
                    resList.innerHTML = '<div class="status">曲が見つかりませんでした</div>';
                    return;
                }

                items.forEach(item => {
                    if (item.type !== 'video' && item.type !== 'stream') return;
                    
                    const div = document.createElement('div');
                    div.className = 'item';
                    
                    const videoId = item.url ? item.url.split('v=')[1] : (item.id || '');
                    const title = item.title || 'Unknown Title';
                    const uploader = item.uploaderName || item.uploader || 'Unknown Artist';
                    const thumbnail = item.thumbnail || `https://i.ytimg.com/vi/${videoId}/hqdefault.jpg`;

                    div.onclick = () => playSong(videoId, title, uploader, thumbnail);
                    div.innerHTML = `
                        <img src="${thumbnail}" loading="lazy">
                        <div class="item-info">
                            <div class="item-title">${title}</div>
                            <div class="item-artist">${uploader}</div>
                        </div>
                    `;
                    resList.appendChild(div);
                });
            } catch (e) {
                resList.innerHTML = '<div class="status" style="color:#f55;">検索失敗。もう一度お試しください。</div>';
            }
        }

        async function playSong(videoId, title, uploader, thumbnail) {
            const titleElem = document.getElementById('playerTitle');
            const artistElem = document.getElementById('playerArtist');
            const thumbElem = document.getElementById('playerThumb');
            const audio = document.getElementById('audioPlayer');

            titleElem.innerText = title;
            artistElem.innerText = "読み込み中...";
            thumbElem.src = thumbnail;

            try {
                const streamData = await fetchWithFallback(`/streams/${videoId}`);
                const audioStreams = streamData.audioStreams || [];

                if (audioStreams.length === 0) throw new Error("音声なし");

                const m4aStream = audioStreams.find(s => s.mimeType && s.mimeType.includes('audio/mp4')) || audioStreams[0];
                
                audio.src = m4aStream.url;
                artistElem.innerText = uploader;
                audio.play();

                if ('mediaSession' in navigator) {
                    navigator.mediaSession.metadata = new MediaMetadata({
                        title: title,
                        artist: uploader,
                        artwork: [{ src: thumbnail, sizes: '512x512', type: 'image/jpeg' }]
                    });
                }
            } catch (e) {
                artistElem.innerText = "再生エラー";
                alert("再生URLの取得に失敗しました。");
            }
        }

        document.getElementById('searchInput').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') search();
        });
    </script>
</body>
</html>
    """)