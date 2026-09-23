import SwiftUI

struct ContentView: View {
    @State private var videoId: String = "dQw4w9WgXcQ" // テスト用Video ID
    @State private var inputUrl: String = ""

    var body: some View {
        VStack(spacing: 20) {
            Text("My Music Player")
                .font(.largeTitle)
                .bold()

            // プレイヤーエリア（非表示にして裏で鳴らすことも可能）
            YouTubeWebView(videoId: videoId)
                .frame(height: 220)
                .cornerRadius(12)
                .padding()

            TextField("YouTube URLまたはIDを入力", text: $inputUrl)
                .textFieldStyle(RoundedBorderTextFieldStyle())
                .padding(.horizontal)

            Button(action: {
                if !inputUrl.isEmpty {
                    self.videoId = extractVideoId(from: inputUrl)
                }
            }) {
                Text("再生")
                    .bold()
                    .frame(maxWidth: .infinity)
                    .padding()
                    .background(Color.blue)
                    .foregroundColor(.white)
                    .cornerRadius(10)
            }
            .padding(.horizontal)

            Spacer()
        }
        .onAppear {
            // バックグラウンド再生の初期化
            AudioSessionManager.shared.setupAudioSession()
            AudioSessionManager.shared.setupRemoteCommandCenter()
        }
    }

    // URLからVideoID（11桁）を抜き出すヘルパー
    private func extractVideoId(from url: String) -> String {
        if url.count == 11 { return url }
        if let range = url.range(of: "v=") {
            let id = url[range.upperBound...].prefix(11)
            return String(id)
        }
        return url
    }
}