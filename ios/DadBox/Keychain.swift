import CryptoKit
import DadBoxKit
import Foundation
import Security

/// The bearer token and the family keys. Synchronizable, so iCloud Keychain
/// carries them to a new phone (ADR 0018: lose every copy, lose the archive);
/// `AfterFirstUnlock`, so a notification extension can decrypt while locked.
/// Keys are never deleted: old ones read old messages.
nonisolated struct Keychain: KeyProvider {
    enum Failure: Error { case status(OSStatus) }
    private let service = "ch.dadbox"

    func key(id: UInt8) -> SymmetricKey? {
        read("key-\(id)").map { SymmetricKey(data: $0) }
    }

    func store(key: SymmetricKey, id: UInt8) throws {
        try write(key.withUnsafeBytes { Data($0) }, account: "key-\(id)")
    }

    var setup: SetupCode? {
        read("setup").flatMap { SetupCode(text: String(decoding: $0, as: UTF8.self)) }
    }

    func store(setup: SetupCode) throws {
        try write(JSONEncoder().encode(setup), account: "setup")
    }

    /// Forgets the server and token. The keys stay: they belong to the archive, not to the login.
    func forgetSetup() {
        SecItemDelete(query("setup") as CFDictionary)
    }

    private func query(_ account: String) -> [String: Any] {
        [kSecClass as String: kSecClassGenericPassword,
         kSecAttrService as String: service,
         kSecAttrAccount as String: account,
         kSecAttrSynchronizable as String: kSecAttrSynchronizableAny]
    }

    private func read(_ account: String) -> Data? {
        var q = query(account)
        q[kSecReturnData as String] = true
        q[kSecMatchLimit as String] = kSecMatchLimitOne
        var out: CFTypeRef?
        return SecItemCopyMatching(q as CFDictionary, &out) == errSecSuccess ? out as? Data : nil
    }

    private func write(_ data: Data, account: String) throws {
        SecItemDelete(query(account) as CFDictionary)
        var q = query(account)
        q[kSecAttrSynchronizable as String] = true
        q[kSecAttrAccessible as String] = kSecAttrAccessibleAfterFirstUnlock
        q[kSecValueData as String] = data
        let status = SecItemAdd(q as CFDictionary, nil)
        guard status == errSecSuccess else { throw Failure.status(status) }
    }
}
