import SwiftUI

@main
struct HabuFieldApp: App {
    @StateObject private var recorder = BackgroundTrackRecorder()

    var body: some Scene {
        WindowGroup {
            ContentView(recorder: recorder)
        }
    }
}
