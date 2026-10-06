import DadBoxKit
import LocalAuthentication
import SwiftUI

/// Words first, numbers second. This screen exists so a flat battery in a school
/// bag surfaces as a fact rather than as a child who seems to have stopped talking.
struct BoxView: View {
    @Environment(AppModel.self) private var model
    @State private var showKey = false

    var body: some View {
        let h = model.health
        List {
            Section {
                HStack(spacing: 12) {
                    Circle().fill(h.level.color).frame(width: 14, height: 14)
                    VStack(alignment: .leading, spacing: 2) {
                        Text(h.headline).font(.title3.weight(.semibold))
                        if let last = model.status?.lastCheckinAt {
                            Text("Last heard from \(last.formatted(.relative(presentation: .named)))" + next(h))
                                .font(.footnote).foregroundStyle(.secondary)
                        }
                    }
                }
                ForEach(h.notes, id: \.self) { Label($0, systemImage: "exclamationmark.circle").foregroundStyle(.orange) }
            }

            if let t = model.status?.telemetry {
                if let fault = t.fault { FaultSection(fault: fault) }
                Section("Power") {
                    if let pct = t.batteryPct {
                        Row("Battery", "\(pct) %" + (t.charging == true ? " · charging" : ""))
                    } else {
                        Row("Battery", "None fitted")
                    }
                    Row("Mains", t.mains ? "Plugged in" : "On battery")
                }
                Section("Link") {
                    Row("Signal", t.rssi.map { "\(signalWord($0)) · \($0) dBm" } ?? "No reading from the modem")
                    Row("A message reaches it", BoxHealth.delivery(t))
                    if t.offlineS > 0 { Row("Was offline for", BoxHealth.span(Double(t.offlineS))) }
                }
                Section("Queue") {
                    Row("Waiting to be played", "\(t.inbox)")
                    Row("Recordings waiting to send", t.outbox == 0 ? "None" :
                        "\(t.outbox) · oldest \(BoxHealth.span(Double(t.outboxOldestS)))")
                    Row("Storage used", "\(t.storagePct) %")
                    if t.recording { Label("Recording right now", systemImage: "record.circle").foregroundStyle(.red) }
                    if t.locked { Label("Locked for travel — hold both buttons 3 s to unlock. It checks in only every \(BoxHealth.span(Double(t.nextCheckinS))) until then.", systemImage: "lock") }
                }
            } else {
                Section { Text("The box has not checked in yet.").foregroundStyle(.secondary) }
            }

            if let s = model.status?.settings { SettingsSections(settings: s) }

            Section {
                DisclosureGroup("What the lights mean") { LEDLegend() }
            }

            Section {
                Row("Key in use", "\(model.keyID)")
                Button("Show the key for a paper copy") { Task { await unlockKey() } }.disabled(model.isDemo)
            } header: { Text("Key") } footer: {
                Text("Every message is sealed with this key. It lives here, in iCloud Keychain and in the box — never on the server. Lose every copy and the archive can't be read.")
            }

            Section {
                if let t = model.status?.telemetry { Row("Box firmware", t.fw) }
                Row("App", Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "–")
                Button(model.isDemo ? "Leave the demo" : "Disconnect this phone", role: .destructive) { model.signOut() }
            }
        }
        .navigationTitle("Box")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar(.visible, for: .navigationBar)
        .refreshable { await model.refresh() }
        .sheet(isPresented: $showKey) {
            if let key = model.keychain.key(id: model.keyID) { KeySheet(key: key, keyID: model.keyID) }
        }
    }

    private func next(_ h: BoxHealth) -> String {
        guard let n = h.nextCheckin, n > model.now else { return "" }
        return " · next ~\(n.formatted(date: .omitted, time: .shortened))"
    }

    private func signalWord(_ rssi: Int) -> String {
        switch rssi {
        case (-75)...: "Strong"
        case (-95)...: "Fine"
        case (-105)...: "Weak"
        default: "Barely there"
        }
    }

    private func unlockKey() async {
        let ok = (try? await LAContext().evaluatePolicy(.deviceOwnerAuthentication, localizedReason: "Show the key")) ?? false
        if ok { showKey = true }
    }
}

private struct Row: View {
    let label: String, value: String
    init(_ label: String, _ value: String) { self.label = label; self.value = value }
    var body: some View { LabeledContent(label, value: value) }
}

private struct FaultSection: View {
    let fault: Fault
    var body: some View {
        Section("Fault") {
            VStack(alignment: .leading, spacing: 6) {
                Label(title, systemImage: "exclamationmark.triangle.fill").foregroundStyle(.red).font(.headline)
                Text(advice).font(.subheadline)
                Text("On the box, Record blinks blue instead of its blue–cyan glow. Recording still works — messages wait safely on the box.")
                    .font(.footnote).foregroundStyle(.secondary)
            }
        }
    }

    private var title: String {
        switch fault {
        case .storage: "Storage is filling up"
        case .modem: "The modem isn't responding"
        case .capture: "A recording failed"
        case .charger: "Charger problem"
        }
    }

    private var advice: String {
        switch fault {
        case .storage: "Unsent recordings are using most of the box's space. Nothing is lost — it needs a connection to send them. Move it somewhere with signal."
        case .modem: "The box can't reach its mobile modem. Unplug it, wait ten seconds, plug it back in. Recordings stay safe on the box."
        case .capture: "The microphone path failed during a recording. Try one recording; if the fault stays, the box needs a look."
        case .charger: "The battery isn't charging as expected. Check the cable and the power supply."
        }
    }
}

/// Edits are local until Save — one PATCH, and the server records who set what.
private struct SettingsSections: View {
    @Environment(AppModel.self) private var model
    let settings: BoxSettings
    @State private var draft: BoxSettings?

    var body: some View {
        let s = Binding(get: { draft ?? settings }, set: { draft = $0 })

        Section {
            DatePicker("From", selection: time(s.quietHours.start), displayedComponents: .hourAndMinute)
            DatePicker("Until", selection: time(s.quietHours.end), displayedComponents: .hourAndMinute)
            LabeledContent("Time zone", value: s.wrappedValue.quietHours.tz)
            if s.wrappedValue.quietHours.tz != TimeZone.current.identifier {
                Button("Use this phone's time zone") { s.wrappedValue.quietHours.tz = TimeZone.current.identifier }
            }
        } header: { Text("Quiet hours") } footer: {
            Text("The box glows but doesn't chime. Play still works. Enforced on the box, not by you.")
        }

        Section("Sound and light") {
            slider("Volume", "speaker.wave.2", s.volume)
            slider("Light", "sun.max", s.ledBrightness)
        }

        Section {
            if s.wrappedValue.poll.backstopMinutes != nil {
                Stepper("Plugged in: every \(s.wrappedValue.poll.backstopMinutes ?? 10) min",
                        value: Binding(get: { s.wrappedValue.poll.backstopMinutes ?? 10 },
                                       set: { s.wrappedValue.poll.backstopMinutes = $0 }), in: 5...30, step: 5)
            }
            Stepper("Locked or idle on battery: every \(s.wrappedValue.poll.idleMinutes) min", value: s.poll.idleMinutes, in: 5...60, step: 5)
        } header: { Text("Check-in") } footer: {
            Text("Plugged in, the doorbell brings a message at once; the check-in above only catches a missed ring. Without the doorbell it is every minute, and for 5 minutes after the child used the box every 15 s. Locked for travel, or idle on battery, it checks in at the second interval — shorter means faster delivery and, on battery, a shorter battery.")
        }

        if let d = draft, d != settings {
            Section {
                Button("Save changes") { Task { await save(d) } }.fontWeight(.semibold)
                Button("Revert", role: .cancel) { draft = nil }
            }
        }
    }

    private func save(_ d: BoxSettings) async {
        await model.patch { p in
            if d.quietHours != settings.quietHours { p.quietHours = d.quietHours }
            if d.volume != settings.volume { p.volume = d.volume }
            if d.ledBrightness != settings.ledBrightness { p.ledBrightness = d.ledBrightness }
            if d.poll != settings.poll {
                p.poll = .init(idleMinutes: d.poll.idleMinutes != settings.poll.idleMinutes ? d.poll.idleMinutes : nil,
                               backstopMinutes: d.poll.backstopMinutes != settings.poll.backstopMinutes ? d.poll.backstopMinutes : nil)
            }
        }
        draft = nil
    }

    private func slider(_ label: String, _ symbol: String, _ value: Binding<Int>) -> some View {
        HStack {
            Image(systemName: symbol).foregroundStyle(.secondary).frame(width: 28)
            Slider(value: Binding(get: { Double(value.wrappedValue) }, set: { value.wrappedValue = Int($0) }), in: 0...100, step: 5)
                .accessibilityLabel(label)
            Text("\(value.wrappedValue)").monospacedDigit().foregroundStyle(.secondary).frame(width: 34, alignment: .trailing)
        }
    }

    /// "20:00" ↔ a Date the picker can turn. Only hour and minute mean anything.
    private func time(_ hhmm: Binding<String>) -> Binding<Date> {
        Binding(get: {
            let p = hhmm.wrappedValue.split(separator: ":").compactMap { Int($0) }
            return Calendar.current.date(from: DateComponents(hour: p.first ?? 0, minute: p.last ?? 0)) ?? Date()
        }, set: {
            let c = Calendar.current.dateComponents([.hour, .minute], from: $0)
            hhmm.wrappedValue = String(format: "%02d:%02d", c.hour ?? 0, c.minute ?? 0)
        })
    }
}

/// ADR 0024 and box/DESIGN.md § Decisions — so the adult in the other house can be told what the lights mean.
private struct LEDLegend: View {
    private let record: [(String, String)] = [
        ("Blue–cyan glow, slowly flowing", "Ready. The server heard from the box within the last two check-ins, and nothing is wrong."),
        ("Slow blue blink, 1 s on / 2 s off", "Not ready: no network, no server, or a fault. Recording still works — messages wait on the box and go when it is back. This screen says why."),
        ("Steady red", "Recording, between a rising and a falling tone. The microphone is on only then."),
        ("One green pulse", "Got it: the recording is safe on the box. Not yet delivered — that is this screen's job."),
        ("Dark", "A message is waiting on Play, a message is playing, the box is locked for travel or still starting — or unplugged."),
    ]
    private let play: [(String, String)] = [
        ("Pulsing green", "A message is waiting. It chimes once when it arrives and once more 10 s later — never in quiet hours."),
        ("Steady green", "Playing."),
        ("Running through the colours", "Starting up. Then the box says it is ready to record — or, once, that it cannot connect to the server."),
    ]
    private let both: [(String, String)] = [
        ("Two cyan-white flashes and a falling tone", "Locked for travel (both buttons held 3 s). One flash and a rising tone: unlocked."),
        ("Three quick cyan-white flashes", "A button pressed while locked."),
    ]
    var body: some View {
        group("Record", record)
        group("Play", play)
        group("Both buttons", both)
        Text("Why the box is not ready — no connection, or a fault — is only on this screen.")
            .font(.footnote).foregroundStyle(.secondary)
    }

    @ViewBuilder private func group(_ title: String, _ rows: [(String, String)]) -> some View {
        Text(title).font(.headline).padding(.top, 4)
        ForEach(rows, id: \.0) { pattern, meaning in
            VStack(alignment: .leading, spacing: 2) {
                Text(pattern).font(.subheadline.weight(.medium))
                Text(meaning).font(.footnote).foregroundStyle(.secondary)
            }
        }
    }
}
