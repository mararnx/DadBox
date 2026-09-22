import CoreImage.CIFilterBuiltins
import CryptoKit
import DadBoxKit
import SwiftUI
import VisionKit

/// Runs once. Server and token come from the QR the server's token script prints;
/// the key is made here and carried to the box by hand (SERVER-CONCEPT § Encryption).
/// On a new phone iCloud Keychain brings both and this never shows.
struct SetupView: View {
    @Environment(AppModel.self) private var model
    @State private var setup: SetupCode?
    @State private var pasted = ""
    @State private var keyText = ""
    @State private var scanning: ScanTarget?
    @State private var newKey: SymmetricKey?
    @State private var problem: String?

    enum ScanTarget: Identifiable { case setup, key; var id: Self { self } }

    var body: some View {
        NavigationStack {
            Form {
                if setup == nil { connect } else { key }
                if let problem { Section { Text(problem).foregroundStyle(.red) } }
                Section {
                    Button("Look around with demo data") { Task { await model.enterDemo() } }
                } footer: { Text("A pretend box and three pretend messages. Nothing leaves the phone.") }
            }
            .navigationTitle("DadBox")
            .onAppear { setup = model.keychain.setup }
            .sheet(item: $scanning) { target in
                Scanner { text in
                    scanning = nil
                    switch target {
                    case .setup: pasted = text; connectTapped()
                    case .key: keyText = text; importKey()
                    }
                }
            }
            .sheet(item: Binding(get: { newKey.map(Wrapped.init) }, set: { if $0 == nil { newKey = nil } })) { w in
                KeySheet(key: w.key, keyID: model.keyID, firstTime: true) { Task { await finish() } }
            }
        }
    }

    private var connect: some View {
        Section {
            if Scanner.available { Button("Scan the setup code", systemImage: "qrcode.viewfinder") { scanning = .setup } }
            TextField("…or paste it here", text: $pasted, axis: .vertical).lineLimit(3)
                .textInputAutocapitalization(.never).autocorrectionDisabled().font(.footnote.monospaced())
            Button("Connect") { connectTapped() }.disabled(pasted.isEmpty)
        } header: { Text("1 · Connect to your server") } footer: {
            Text("The server's token script prints this code once: the address, who you are, and your token.")
        }
    }

    private var key: some View {
        Section {
            Button("Create the key", systemImage: "key") { newKey = SymmetricKey(size: .bits256) }
            if Scanner.available { Button("Scan a paper copy", systemImage: "qrcode.viewfinder") { scanning = .key } }
            TextField("…or type its 43 characters", text: $keyText).textInputAutocapitalization(.never)
                .autocorrectionDisabled().font(.footnote.monospaced()).onSubmit { importKey() }
        } header: { Text("2 · The key") } footer: {
            Text("Every message is sealed with a key only this phone and the box hold. The server never has it. Create it once; after that, scan the paper copy.")
        }
    }

    private func connectTapped() {
        guard let code = SetupCode(text: pasted) else { problem = "That isn't a DadBox setup code."; return }
        do {
            try model.keychain.store(setup: code)
            setup = code
            problem = nil
            if model.keychain.key(id: code.identity == .parentB ? 2 : 1) != nil { Task { await finish() } }
        } catch { problem = "The Keychain refused to store the token (\(error))." }
    }

    private func importKey() {
        guard let k = KeyText.decode(keyText) else { problem = "A key is exactly 43 letters, digits, - and _."; return }
        store(k)
        Task { await finish() }
    }

    private func store(_ k: SymmetricKey) {
        do { try model.keychain.store(key: k, id: setup?.identity == .parentB ? 2 : 1); problem = nil }
        catch { problem = "The Keychain refused to store the key (\(error))." }
    }

    private func finish() async {
        if let k = newKey { store(k); newKey = nil }
        guard problem == nil, let setup else { return }
        await AppDelegate.askForNotifications()
        await model.enter(setup)
    }

    private struct Wrapped: Identifiable { let key: SymmetricKey; var id: String { KeyText.encode(key) } }
}

/// The key as people handle it: a QR to print for the drawer, 43 characters for the box's `.env`.
struct KeySheet: View {
    @Environment(\.dismiss) private var dismiss
    let key: SymmetricKey
    let keyID: UInt8
    var firstTime = false
    var done: () -> Void = {}

    var body: some View {
        let text = KeyText.encode(key)
        NavigationStack {
            ScrollView {
                VStack(spacing: 18) {
                    if let qr = Self.qr(text) {
                        Image(uiImage: qr).interpolation(.none).resizable().scaledToFit().frame(width: 220, height: 220)
                            .padding(12).background(.white, in: .rect(cornerRadius: 12))
                    }
                    Text(text).font(.callout.monospaced()).textSelection(.enabled).multilineTextAlignment(.center)
                    Text("Key \(keyID)").font(.footnote).foregroundStyle(.secondary)
                    VStack(alignment: .leading, spacing: 10) {
                        Label("Put these 43 characters in the box's .env as DADBOX_KEY_\(keyID) before flashing.", systemImage: "shippingbox")
                        Label("Print this screen and keep it in a drawer. It is the only way back if iCloud Keychain is ever lost.", systemImage: "printer")
                        Label("Never send it by mail or chat. Anyone with this and your token can hear everything.", systemImage: "hand.raised")
                    }
                    .font(.subheadline)
                    ShareLink("Print or save", item: Image(uiImage: Self.qr(text) ?? UIImage()),
                              preview: SharePreview("DadBox key \(keyID)"))
                }
                .padding(24)
            }
            .navigationTitle(firstTime ? "Your new key" : "Key")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button(firstTime ? "I've kept it" : "Done") { dismiss(); done() }
                }
            }
            .interactiveDismissDisabled(firstTime)
        }
    }

    static func qr(_ text: String) -> UIImage? {
        let f = CIFilter.qrCodeGenerator()
        f.message = Data(text.utf8)
        f.correctionLevel = "Q"
        guard let out = f.outputImage?.transformed(by: .init(scaleX: 10, y: 10)),
              let cg = CIContext().createCGImage(out, from: out.extent) else { return nil }
        return UIImage(cgImage: cg)
    }
}

/// QR scanning with the system's data scanner. Not on the simulator — paste works everywhere.
struct Scanner: UIViewControllerRepresentable {
    static var available: Bool { DataScannerViewController.isSupported && DataScannerViewController.isAvailable }
    let found: (String) -> Void

    func makeUIViewController(context: Context) -> DataScannerViewController {
        let vc = DataScannerViewController(recognizedDataTypes: [.barcode(symbologies: [.qr])], isHighlightingEnabled: true)
        vc.delegate = context.coordinator
        try? vc.startScanning()
        return vc
    }

    func updateUIViewController(_ vc: DataScannerViewController, context: Context) {}
    func makeCoordinator() -> Coordinator { Coordinator(found: found) }

    final class Coordinator: NSObject, DataScannerViewControllerDelegate {
        let found: (String) -> Void
        init(found: @escaping (String) -> Void) { self.found = found }

        func dataScanner(_ scanner: DataScannerViewController, didAdd items: [RecognizedItem], allItems: [RecognizedItem]) {
            for case .barcode(let code) in items {
                if let s = code.payloadStringValue { scanner.stopScanning(); found(s); return }
            }
        }
    }
}
