import Foundation
import AVAudioSession
import AVFoundation
import MediaPlayer

class AudioSessionManager {
    static let shared = AudioSessionManager()

    func setupAudioSession() {
        do {
            // バックグラウンドでも音声再生を継続させる宣言
            let session = AVAudioSession.sharedInstance()
            try session.setCategory(.playback, mode: .default, options: [])
            try session.setActive(true)
        } catch {
            print("AudioSession設定エラー: \(error)")
        }
    }

    // コントロールセンターやロック画面に曲情報を表示・操作可能にする
    func setupRemoteCommandCenter() {
        let commandCenter = MPRemoteCommandCenter.shared()
        commandCenter.playCommand.addTarget { event in
            // 再生処理
            return .success
        }
        commandCenter.pauseCommand.addTarget { event in
            // 一時停止処理
            return .success
        }
    }
}