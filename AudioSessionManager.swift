import Foundation
import AVFoundation // ← import AVAudioSession ではなく AVFoundation
import MediaPlayer

class AudioSessionManager {
    static let shared = AudioSessionManager()

    func setupAudioSession() {
        do {
            let session = AVAudioSession.sharedInstance()
            try session.setCategory(.playback, mode: .default, options: [])
            try session.setActive(true)
        } catch {
            print("AudioSession設定エラー: \(error)")
        }
    }

    func setupRemoteCommandCenter() {
        let commandCenter = MPRemoteCommandCenter.shared()
        commandCenter.playCommand.addTarget { event in
            return .success
        }
        commandCenter.pauseCommand.addTarget { event in
            return .success
        }
    }
}