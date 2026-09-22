#if DEBUG
import Foundation

/// Launch arguments for driving the app from `simctl` without touching the screen:
///
///     xcrun simctl launch booted ma.arnold.dadbox.app -demo -play 2 -send-draft -screen box
///
/// Debug builds only. Nothing here exists in a release build.
extension AppModel {
    func runDebugHooks() async {
        let args = ProcessInfo.processInfo.arguments
        func value(_ flag: String) -> String? {
            args.firstIndex(of: flag).flatMap { args.indices.contains($0 + 1) ? args[$0 + 1] : nil }
        }
        if let n = value("-play").flatMap(Int.init), thread.indices.contains(n) {
            await toggle(thread[n])
            print("debug: play \(n) → playing=\(player.playingID ?? "nil") notice=\(notice ?? "nil")")
        }
        if args.contains("-send-draft") {
            print("debug: draft=\(String(describing: recorder.draft))")
            await sendDraft()
            print("debug: sent → \(thread.last.map { "\($0.from.rawValue) seq \($0.seq) \($0.state.rawValue) \($0.bytes) B" } ?? "nil") notice=\(notice ?? "nil")")
        }
        if value("-screen") == "box" { openBox = true }
    }
}
#endif
