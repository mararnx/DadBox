// Draws the DadBox app icon: the box itself, front-on — a brushed-aluminium
// face with its two lit buttons, record (red) and play (green), on the app's
// warm accent. Writes the light, dark and tinted 1024 px variants into the
// asset catalog.
//
//   DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer swift ios/Tools/make_app_icon.swift
import AppKit
import CoreGraphics

let S: CGFloat = 1024
let out = URL(fileURLWithPath: #filePath)
    .deletingLastPathComponent().deletingLastPathComponent()
    .appendingPathComponent("DadBox/Assets.xcassets/AppIcon.appiconset")

enum Variant: String, CaseIterable { case light, dark, tinted }

func rgb(_ r: CGFloat, _ g: CGFloat, _ b: CGFloat, _ a: CGFloat = 1) -> CGColor {
    CGColor(srgbRed: r, green: g, blue: b, alpha: a)
}

func gray(_ w: CGFloat, _ a: CGFloat = 1) -> CGColor { rgb(w, w, w, a) }

func linear(_ ctx: CGContext, _ colors: [CGColor], from: CGPoint, to: CGPoint) {
    let g = CGGradient(colorsSpace: CGColorSpace(name: CGColorSpace.sRGB), colors: colors as CFArray, locations: nil)!
    ctx.drawLinearGradient(g, start: from, end: to, options: [.drawsBeforeStartLocation, .drawsAfterEndLocation])
}

func radial(_ ctx: CGContext, _ colors: [CGColor], at c: CGPoint, r: CGFloat) {
    let g = CGGradient(colorsSpace: CGColorSpace(name: CGColorSpace.sRGB), colors: colors as CFArray, locations: nil)!
    ctx.drawRadialGradient(g, startCenter: c, startRadius: 0, endCenter: c, endRadius: r, options: [])
}

func draw(_ v: Variant) -> CGImage {
    let ctx = CGContext(data: nil, width: Int(S), height: Int(S), bitsPerComponent: 8, bytesPerRow: 0,
                        space: CGColorSpace(name: CGColorSpace.sRGB)!,
                        bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)!
    // CoreGraphics origin is bottom-left; y grows upward.

    // Background. Tinted is transparent: iOS supplies the tint from luminance.
    switch v {
    case .light:
        linear(ctx, [rgb(0.980, 0.690, 0.330), rgb(0.851, 0.467, 0.118), rgb(0.720, 0.330, 0.090)],
               from: CGPoint(x: 0, y: S), to: CGPoint(x: S * 0.4, y: 0))
    case .dark:
        linear(ctx, [rgb(0.170, 0.135, 0.110), rgb(0.070, 0.060, 0.055)],
               from: CGPoint(x: 0, y: S), to: CGPoint(x: S * 0.4, y: 0))
    case .tinted:
        break
    }

    // The box face: a wide rounded rectangle, slightly low of centre.
    let face = CGRect(x: 132, y: 262, width: 760, height: 470)
    let facePath = CGPath(roundedRect: face, cornerWidth: 118, cornerHeight: 118, transform: nil)

    if v != .tinted {
        ctx.saveGState()
        ctx.setShadow(offset: CGSize(width: 0, height: -34), blur: 70,
                      color: v == .dark ? gray(0, 0.7) : rgb(0.35, 0.13, 0.02, 0.45))
        ctx.addPath(facePath); ctx.setFillColor(gray(0.8)); ctx.fillPath()
        ctx.restoreGState()
    }

    // Aluminium: a cool vertical gradient with a faint horizontal brush.
    ctx.saveGState()
    ctx.addPath(facePath); ctx.clip()
    if v == .tinted {
        linear(ctx, [gray(0.80), gray(0.62)], from: CGPoint(x: 0, y: face.maxY), to: CGPoint(x: 0, y: face.minY))
    } else {
        linear(ctx, [rgb(0.955, 0.960, 0.968), rgb(0.835, 0.845, 0.860), rgb(0.700, 0.712, 0.730)],
               from: CGPoint(x: 0, y: face.maxY), to: CGPoint(x: 0, y: face.minY))
        var seed: UInt64 = 0xDAD_B0C5
        for y in stride(from: face.minY, to: face.maxY, by: 3) {
            seed = seed &* 6364136223846793005 &+ 1442695040888963407
            let n = CGFloat(seed >> 40) / CGFloat(1 << 24)
            ctx.setFillColor(gray(n > 0.5 ? 1 : 0, 0.035 * abs(n - 0.5) * 2))
            ctx.fill(CGRect(x: face.minX, y: y, width: face.width, height: 1.5))
        }
        // Top-edge sheen and bottom-edge shade give the face some thickness.
        linear(ctx, [gray(1, 0.55), gray(1, 0)], from: CGPoint(x: 0, y: face.maxY), to: CGPoint(x: 0, y: face.maxY - 70))
        linear(ctx, [gray(0, 0.14), gray(0, 0)], from: CGPoint(x: 0, y: face.minY), to: CGPoint(x: 0, y: face.minY + 60))
    }
    ctx.restoreGState()

    // Hairline edge.
    ctx.addPath(facePath)
    ctx.setStrokeColor(v == .tinted ? gray(1, 0.5) : gray(1, 0.7)); ctx.setLineWidth(3); ctx.strokePath()

    // The two buttons: record (red) left, play (green) right.
    let cy = face.midY
    let buttons: [(CGFloat, CGColor, CGColor)] = [
        (face.minX + face.width * 0.30, rgb(1.00, 0.26, 0.20), rgb(1.00, 0.55, 0.45)),
        (face.minX + face.width * 0.70, rgb(0.20, 0.86, 0.38), rgb(0.60, 1.00, 0.68)),
    ]
    for (cx, lit, core) in buttons {
        let c = CGPoint(x: cx, y: cy)
        let bezel: CGFloat = 118, ring: CGFloat = 96, cap: CGFloat = 78

        if v == .tinted {
            // Luminance only: bright rings on a darker well.
            ctx.setFillColor(gray(0.30)); ctx.fillEllipse(in: CGRect(x: cx - bezel, y: cy - bezel, width: bezel * 2, height: bezel * 2))
            ctx.setFillColor(gray(1.00)); ctx.fillEllipse(in: CGRect(x: cx - ring, y: cy - ring, width: ring * 2, height: ring * 2))
            ctx.setFillColor(gray(0.55)); ctx.fillEllipse(in: CGRect(x: cx - cap, y: cy - cap, width: cap * 2, height: cap * 2))
            continue
        }

        // Glow spilling onto the aluminium.
        ctx.saveGState(); ctx.addPath(facePath); ctx.clip()
        radial(ctx, [lit.copy(alpha: 0.55)!, lit.copy(alpha: 0)!], at: c, r: 200)
        ctx.restoreGState()

        // Recessed bezel.
        ctx.saveGState()
        ctx.addEllipse(in: CGRect(x: cx - bezel, y: cy - bezel, width: bezel * 2, height: bezel * 2)); ctx.clip()
        linear(ctx, [gray(0.50), gray(0.86)], from: CGPoint(x: 0, y: cy + bezel), to: CGPoint(x: 0, y: cy - bezel))
        ctx.restoreGState()

        // Lit ring.
        ctx.saveGState()
        ctx.setShadow(offset: .zero, blur: 40, color: lit)
        ctx.setFillColor(lit)
        ctx.fillEllipse(in: CGRect(x: cx - ring, y: cy - ring, width: ring * 2, height: ring * 2))
        ctx.restoreGState()
        ctx.saveGState()
        ctx.addEllipse(in: CGRect(x: cx - ring, y: cy - ring, width: ring * 2, height: ring * 2)); ctx.clip()
        radial(ctx, [core, lit], at: c, r: ring)
        ctx.restoreGState()

        // Steel cap with a soft highlight.
        ctx.saveGState()
        ctx.setShadow(offset: CGSize(width: 0, height: -6), blur: 14, color: gray(0, 0.35))
        ctx.addEllipse(in: CGRect(x: cx - cap, y: cy - cap, width: cap * 2, height: cap * 2))
        ctx.setFillColor(gray(0.8)); ctx.fillPath()
        ctx.restoreGState()
        ctx.saveGState()
        ctx.addEllipse(in: CGRect(x: cx - cap, y: cy - cap, width: cap * 2, height: cap * 2)); ctx.clip()
        linear(ctx, [gray(0.97), gray(0.80), gray(0.66)], from: CGPoint(x: cx - cap, y: cy + cap), to: CGPoint(x: cx + cap, y: cy - cap))
        radial(ctx, [gray(1, 0.8), gray(1, 0)], at: CGPoint(x: cx - 26, y: cy + 30), r: 50)
        ctx.restoreGState()
    }

    return ctx.makeImage()!
}

for v in Variant.allCases {
    let rep = NSBitmapImageRep(cgImage: draw(v))
    let url = out.appendingPathComponent("AppIcon-\(v.rawValue).png")
    try! rep.representation(using: .png, properties: [:])!.write(to: url)
    print("wrote \(url.lastPathComponent)")
}
