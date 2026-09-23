import SwiftUI
import WebKit

struct YouTubeWebView: UIViewRepresentable {
    let videoId: String

    func makeUIView(context: Context) -> WKWebView {
        let configuration = WKWebViewConfiguration()
        // インライン再生（全画面化しない）とバックグラウンド再生を許可
        configuration.allowsInlineMediaPlayback = true
        configuration.mediaTypesRequiringUserActionForPlayback = []

        let webView = WKWebView(frame: .zero, configuration: configuration)
        return webView
    }

    func updateUIView(_ uiView: WKWebView, context: Context) {
        // YouTubeの埋め込みプレイヤーURLを読み込む
        let embedHTML = """
        <!DOCTYPE html>
        <html>
        <body style="margin:0;padding:0;background-color:black;">
            <iframe id="player" type="text/html" width="100%" height="100%"
            src="https://www.youtube.com/embed/\(videoId)?enablejsapi=1&playsinline=1&autoplay=1"
            frameborder="0"></iframe>
        </body>
        </html>
        """
        uiView.loadHTMLString(embedHTML, baseURL: URL(string: "https://www.youtube.com"))
    }
}