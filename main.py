from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"status": "ok"}

# エラー153対策：正しいHTTPS Refererを保持し、操作イベントを中継するWebプレイヤー
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
            // アプリ側からの操作メッセージ（play, pause, seekToなど）をYouTube iframeにそのまま転送
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