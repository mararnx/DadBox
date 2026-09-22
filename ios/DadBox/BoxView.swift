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
                    Row("Signal", "\(signalWord(t.rssi)) · \(t.rssi) dBm")
                    Row("Checks in", "every \(BoxHealth.span(Double(t.nextCheckinS)))")
                    if t.offlineS > 0 { Row("Was offline for", BoxHealth.span(Double(t.offlineS))) }
                }
                Section("Queue") {
                    Row("Waiting to be played", "\(t.inbox)")
                    Row("Recordings waiting to send", t.outbox == 0 ? "None" :
                        "\(t.outbox) · oldest \(BoxHealth.span(Double(t.outboxOldestS)))")
                    Row("Storage used", "\(t.storagePct) %")
                    if t.recording { Label("Recording right now", systemImage: "record.circle").foregroundStyle(.red) }
                    if t.locked { Label("Locked for travel — hold both buttons 3 s to unlock", systemImage: "lock") }
                }
            } else {
                Section { Text("The box has not checked in yet.").foregroundStyle(.secondary) }
            }

            if let s = model.status?.settings { SettingsSections(settings: s) }

            Section {
                DisclosureGroup("What the two small lights mean") { LEDLegend() }
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
                Text("On the box, the two small lights blink alternately. The buttons look normal — the child sees nothing.")
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
        let mine = model.me.house ?? "a", other = mine == "a" ? "b" : "a"

        Section {
            Toggle("Mute the box", isOn: Binding(
                get: { mine == "a" ? settings.mute.a : settings.mute.b },
                set: { v in Task { await model.patch { $0.mute = [mine: v] } } }))
            if let m = model.status?.settingsMeta["mute.\(mine)"], mine == "a" ? settings.mute.a : settings.mute.b {
                Text("Muted \(m.at.formatted(.relative(presentation: .named)))").font(.footnote).foregroundStyle(.secondary)
            }
            if other == "a" ? settings.mute.a : settings.mute.b {
                let m = model.status?.settingsMeta["mute.\(other)"]
                Label("Muted by the other household" + (m.map { " · \($0.at.formatted(date: .abbreviated, time: .shortened))" } ?? ""),
                      systemImage: "speaker.slash")
            }
        } header: { Text("Mute") } footer: {
            Text("Muted: no sound at all, the play button still glows. Both households can mute; both can see it.")
        }

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
            Stepper("Every \(s.wrappedValue.poll.idleMinutes) min", value: s.poll.idleMinutes, in: 5...60, step: 5)
        } header: { Text("Check-in on battery, when idle") } footer: {
            Text("Plugged in, or for 90 minutes after the child used it, the box checks in every minute. Shorter here means faster delivery and a shorter battery.")
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
            if d.poll.idleMinutes != settings.poll.idleMinutes { p.poll = .init(idleMinutes: d.poll.idleMinutes) }
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

/// ARCHITECTURE.md § Status LEDs — so the adult in the other house can be told what the blinking means.
private struct LEDLegend: View {
    private let rows: [(String, String, String)] = [
        ("LINK", "off", "Connected. Nothing to see."),
        ("LINK", "1 blink / 3 s", "No connection; nothing waiting."),
        ("LINK", "2 blinks / 3 s", "No connection, and recordings waiting to go — safe on the box."),
        ("POWER", "off", "Fine: on battery above 20 %, or plugged in and full."),
        ("POWER", "steady", "Charging."),
        ("POWER", "1 blink / 3 s", "Below 20 %, on battery."),
        ("both", "alternating", "Fault — an adult needs to act. This screen says which."),
    ]
    var body: some View {
        ForEach(rows, id: \.2) { led, pattern, meaning in
            VStack(alignment: .leading, spacing: 2) {
                Text("\(led) · \(pattern)").font(.subheadline.weight(.medium))
                Text(meaning).font(.footnote).foregroundStyle(.secondary)
            }
        }
        Text("The buttons' own lights never show any of this. They speak only to the child.")
            .font(.footnote).foregroundStyle(.secondary)
    }
}
