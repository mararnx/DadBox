import SwiftUI
import WidgetKit

/// The app's widget extension. It holds one thing: the lock screen's "message waiting" (ADR 0027).
@main
struct DadBoxLiveBundle: WidgetBundle {
    var body: some Widget {
        WaitingLiveActivity()
    }
}
