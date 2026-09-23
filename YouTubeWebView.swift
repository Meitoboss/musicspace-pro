import SwiftUI
import WebKit

struct YouTubeWebView: UIViewRepresentable {
    let videoId: String

    func makeUIView(context: Context) -> WKWebView {
        let configuration = WKWebViewConfiguration()
        configuration.allowsInlineMediaPlayback = true
        configuration.mediaTypesRequiringUserActionForPlayback = []

        let webView = WKWebView(frame: .zero, configuration: configuration)
        return webView
    }

    func updateUIView(_ uiView: WKWebView, context: Context) {
        // origin=https://www.youtube.com を追加して 152-4 エラーを防止
        let embedHTML = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="margin:0;padding:0;background-color:black;">
            <iframe id="player" type="text/html" width="100%" height="100%"
            src="https://www.youtube.com/embed/\(videoId)?enablejsapi=1&playsinline=1&autoplay=1&origin=https://www.youtube.com"
            frameborder="0"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowfullscreen></iframe>
        </body>
        </html>
        """
        
        // baseURL に https://www.youtube.com を指定
        uiView.loadHTMLString(embedHTML, baseURL: URL(string: "https://www.youtube.com"))
    }
}