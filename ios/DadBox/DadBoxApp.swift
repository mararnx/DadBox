import DadBoxKit
import SwiftUI
import UserNotifications

@main
struct DadBoxApp: App {
    @UIApplicationDelegateAdaptor(AppDelegate.self) private var delegate
    @State private var model = AppModel()
    @Environment(\.scenePhase) private var scenePhase

    var body: some Scene {
        WindowGroup {
            Group {
                switch model.phase {
                case .loading: ProgressView()
                case .setup: SetupView()
                case .ready: ConversationView()
                }
            }
            .environment(model)
            .task {
                delegate.model = model
                await model.start()
            }
            .task { await model.watchLiveActivityToken() }
            .onOpenURL { url in Task { await model.open(url) } }
            .onChange(of: scenePhase) { _, phase in
                if phase == .active { Task { await model.refresh() } }
            }
        }
    }
}

/// APNs plumbing. Payloads carry a kind and ids — never content (PROTOCOL.md § Push).
final class AppDelegate: NSObject, UIApplicationDelegate, UNUserNotificationCenterDelegate {
    var model: AppModel?

    func application(_ application: UIApplication,
                     didFinishLaunchingWithOptions options: [UIApplication.LaunchOptionsKey: Any]? = nil) -> Bool {
        UNUserNotificationCenter.current().delegate = self
        return true
    }

    func application(_ application: UIApplication, didRegisterForRemoteNotificationsWithDeviceToken token: Data) {
        let hex = token.map { String(format: "%02x", $0) }.joined()
        Task { await model?.register(pushToken: hex) }
    }

    func application(_ application: UIApplication, didReceiveRemoteNotification userInfo: [AnyHashable: Any]) async
        -> UIBackgroundFetchResult {
        guard let push = PushPayload(userInfo: userInfo) else { return .noData }
        await model?.handle(push: push, tapped: false)
        return .newData
    }

    func userNotificationCenter(_ center: UNUserNotificationCenter, willPresent notification: UNNotification) async
        -> UNNotificationPresentationOptions {
        if let push = PushPayload(userInfo: notification.request.content.userInfo) {
            await model?.handle(push: push, tapped: false)
        }
        return [.banner, .sound, .list]
    }

    func userNotificationCenter(_ center: UNUserNotificationCenter, didReceive response: UNNotificationResponse) async {
        guard let push = PushPayload(userInfo: response.notification.request.content.userInfo) else { return }
        await model?.handle(push: push, tapped: true)      // opens at the message; nothing autoplays
    }

    static func askForNotifications() async {
        let ok = (try? await UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .sound, .badge])) ?? false
        if ok { UIApplication.shared.registerForRemoteNotifications() }
    }
}
