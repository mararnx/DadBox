// swift-tools-version: 6.2
import PackageDescription

// Protocol logic for the DadBox iOS app. No UIKit, no SwiftUI: everything here
// runs under `swift test` on the Mac. docs/PROTOCOL.md is the contract.
let package = Package(
    name: "DadBoxKit",
    platforms: [.iOS(.v26), .macOS(.v15)],
    products: [.library(name: "DadBoxKit", targets: ["DadBoxKit"])],
    targets: [
        .target(name: "DadBoxKit"),
        .testTarget(name: "DadBoxKitTests", dependencies: ["DadBoxKit"], resources: [.copy("Fixtures")]),
    ]
)
