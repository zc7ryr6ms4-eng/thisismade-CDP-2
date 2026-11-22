// Gerätefront des thisismade cdp-2 – CoreGraphics-Zeichnung und Klickflächen.
// Koordinaten: Geräteeinheiten, y nach unten (die View ist "flipped").
import AppKit

struct RGB {
    var r: CGFloat, g: CGFloat, b: CGFloat
    init(_ r: CGFloat, _ g: CGFloat, _ b: CGFloat) { self.r = r; self.g = g; self.b = b }
    func cg(_ a: CGFloat = 1) -> CGColor { CGColor(srgbRed: r, green: g, blue: b, alpha: a) }
    func scaled(_ f: CGFloat, add: CGFloat = 0) -> RGB {
        RGB(min(1, r * f + add), min(1, g * f + add), min(1, b * f + add))
    }
    var sum: CGFloat { r + g + b }
}

struct FaceState {
    var pressed: Set<String> = []
    var discLoaded = false
    var discAngle: CGFloat = 0
    var discColor = RGB(0.93, 0.91, 0.86)
    var discLines: [String] = []
    var cover: CGImage? = nil
    var mediaLED = false
    var powerOn = true
    var vu: [CGFloat] = [0, 0]
    var peaks: [CGFloat] = [0, 0]
    var mainText = "------------"
    var msgMode = false
    var vsText = "100"
    var lvText = "080"
    var keyLock = false
    var cueSet = [false, false, false]
    var varispeedNorm: CGFloat = 0.5
    var levelNorm: CGFloat = 0.8
    var jog: CGFloat = 0
    var repeatMode = 0
    var shuffle = false
    var paused = false
    var remain = false
}

enum Face {
    static let devW: CGFloat = 1200, devH: CGFloat = 660
    static let marginX: CGFloat = 28, marginTop: CGFloat = 24, marginBottom: CGFloat = 40
    static var canvasW: CGFloat { devW + 2 * marginX }
    static var canvasH: CGFloat { devH + marginTop + marginBottom }

    static let txt = RGB(0.22, 0.22, 0.24)
    static let txtDim = RGB(0.50, 0.50, 0.52)
    static let amber = RGB(1.0, 0.60, 0.14)
    static let segOn = RGB(1.0, 0.13, 0.08)
    static let segOff = RGB(0.20, 0.04, 0.035)
    static let ledOn = RGB(1.0, 0.18, 0.10)

    static let discC = CGPoint(x: 320, y: 360)
    static let wellR: CGFloat = 272, discR: CGFloat = 250, hubR: CGFloat = 62
    static let display = CGRect(x: 630, y: 70, width: 540, height: 170)
    static let topBtns: [(String, String, CGFloat)] = [
        ("data", "OPEN", 700), ("usb", "FILES", 772), ("cd", "CD", 844),
        ("output", "OUTPUT", 916), ("sync", "HELP", 988), ("power", "POWER", 1060)]
    static let topW: CGFloat = 64, topY: CGFloat = 18, topH: CGFloat = 26
    static let keys: [(String, CGFloat, CGFloat)] = [
        ("1", 630, 270), ("2", 690, 270), ("3", 750, 270), ("4", 810, 270), ("5", 870, 270),
        ("T", 930, 270), ("6", 630, 326), ("7", 690, 326), ("8", 750, 326), ("9", 810, 326),
        ("0", 870, 326), ("C", 930, 326)]
    static let keyW: CGFloat = 50, keyH: CGFloat = 44
    static let enter = CGRect(x: 990, y: 270, width: 70, height: 100)
    static let knobC = CGPoint(x: 1120, y: 318)
    static let knobR: CGFloat = 48
    static let mem: [(String, String, CGFloat)] = [("cue1", "A", 630), ("cue2", "B", 712), ("cue3", "C", 794)]
    static let memY: CGFloat = 412, memW: CGFloat = 72, memH: CGFloat = 44
    static let shuttle = CGRect(x: 890, y: 412, width: 170, height: 44)
    static let jogTravel: CGFloat = 55
    static let faderX: CGFloat = 1120, faderY0: CGFloat = 446, faderY1: CGFloat = 626
    static let transport: [(String, CGFloat, CGFloat)] = [
        ("prev", 630, 90), ("next", 730, 90), ("stop", 830, 90), ("play", 930, 130)]
    static let trY: CGFloat = 482, trH: CGFloat = 82
    static let small: [(String, String, CGFloat)] = [
        ("keylock", "KEY LOCK", 630), ("repeat", "REPEAT", 742), ("shuffle", "SHUFFLE", 854),
        ("eject", "EJECT", 966)]
    static let smallY: CGFloat = 590, smallW: CGFloat = 94, smallH: CGFloat = 34

    // ------------------------------------------------------------- Klickflächen
    enum Region { case rect(CGRect), circle(CGPoint, CGFloat) }

    static let regions: [(String, Region)] = {
        var r: [(String, Region)] = []
        for (id, _, x) in topBtns { r.append((id, .rect(CGRect(x: x - 2, y: topY - 4, width: topW + 4, height: topH + 8)))) }
        for (lab, x, y) in keys { r.append(("key_" + lab, .rect(CGRect(x: x - 3, y: y - 3, width: keyW + 6, height: keyH + 6)))) }
        r.append(("enter", .rect(enter)))
        r.append(("level", .circle(knobC, knobR + 8)))
        for (id, _, x) in mem { r.append((id, .rect(CGRect(x: x - 3, y: memY - 3, width: memW + 6, height: memH + 6)))) }
        r.append(("jog", .rect(CGRect(x: shuttle.minX - 4, y: shuttle.minY - 18, width: shuttle.width + 8, height: shuttle.height + 22))))
        r.append(("varispeed", .rect(CGRect(x: faderX - 40, y: faderY0 - 24, width: 80, height: faderY1 - faderY0 + 40))))
        for (id, x, w) in transport { r.append((id, .rect(CGRect(x: x - 3, y: trY - 3, width: w + 6, height: trH + 6)))) }
        for (id, _, x) in small { r.append((id, .rect(CGRect(x: x - 3, y: smallY - 3, width: smallW + 6, height: smallH + 6)))) }
        r.append(("main_display", .rect(display)))
        r.append(("disc", .circle(discC, discR)))
        return r
    }()

    static func hit(_ p: CGPoint) -> String? {
        for (id, reg) in regions {
            switch reg {
            case .rect(let rc): if rc.contains(p) { return id }
            case .circle(let c, let r): if hypot(p.x - c.x, p.y - c.y) <= r { return id }
            }
        }
        return nil
    }

    // ------------------------------------------------------------- Helfer
    static let cs = CGColorSpace(name: CGColorSpace.sRGB)!

    static func rrect(_ c: CGContext, _ x: CGFloat, _ y: CGFloat, _ w: CGFloat, _ h: CGFloat, _ r: CGFloat) {
        let rr = min(r, w / 2, h / 2)
        c.addPath(CGPath(roundedRect: CGRect(x: x, y: y, width: w, height: h), cornerWidth: rr, cornerHeight: rr, transform: nil))
    }

    static func circle(_ c: CGContext, _ x: CGFloat, _ y: CGFloat, _ r: CGFloat) {
        c.addEllipse(in: CGRect(x: x - r, y: y - r, width: 2 * r, height: 2 * r))
    }

    static func fill(_ c: CGContext, _ col: RGB, _ a: CGFloat = 1) {
        c.setFillColor(col.cg(a))
        c.fillPath()
    }

    static func gradient(_ stops: [(CGFloat, RGB)]) -> CGGradient {
        CGGradient(colorsSpace: cs, colors: stops.map { $0.1.cg() } as CFArray, locations: stops.map { $0.0 })!
    }

    static func fillLinear(_ c: CGContext, from p0: CGPoint, to p1: CGPoint, _ stops: [(CGFloat, RGB)]) {
        c.saveGState()
        c.clip()
        c.drawLinearGradient(gradient(stops), start: p0, end: p1, options: [.drawsBeforeStartLocation, .drawsAfterEndLocation])
        c.restoreGState()
    }

    static func fillV(_ c: CGContext, _ y0: CGFloat, _ y1: CGFloat, _ c0: RGB, _ c1: RGB) {
        fillLinear(c, from: CGPoint(x: 0, y: y0), to: CGPoint(x: 0, y: y1), [(0, c0), (1, c1)])
    }

    static func fillRadial(_ c: CGContext, _ p0: CGPoint, _ r0: CGFloat, _ p1: CGPoint, _ r1: CGFloat, _ stops: [(CGFloat, RGB)]) {
        c.saveGState()
        c.clip()
        c.drawRadialGradient(gradient(stops), startCenter: p0, startRadius: r0, endCenter: p1, endRadius: r1,
                             options: [.drawsBeforeStartLocation, .drawsAfterEndLocation])
        c.restoreGState()
    }

    enum Align { case left, center, right }

    static func text(_ c: CGContext, _ s: String, _ x: CGFloat, _ y: CGFloat, _ size: CGFloat,
                     _ col: RGB = txt, align: Align = .center, bold: Bool = false) {
        let font = NSFont.systemFont(ofSize: size, weight: bold ? .semibold : .regular)
        let attrs: [NSAttributedString.Key: Any] = [.font: font, .foregroundColor: NSColor(cgColor: col.cg()) ?? .black]
        let str = NSAttributedString(string: s, attributes: attrs)
        let w = str.size().width
        var px = x
        switch align {
        case .center: px -= w / 2
        case .right: px -= w
        case .left: break
        }
        NSGraphicsContext.saveGraphicsState()
        NSGraphicsContext.current = NSGraphicsContext(cgContext: c, flipped: true)
        str.draw(at: NSPoint(x: px, y: y - font.ascender))
        NSGraphicsContext.restoreGraphicsState()
    }

    // ------------------------------------------------------------- 7 Segmente
    static let seg: [Character: String] = [
        "0": "abcdef", "1": "bc", "2": "abged", "3": "abgcd", "4": "fgbc", "5": "afgcd",
        "6": "afgedc", "7": "abc", "8": "abcdefg", "9": "abcdfg", "-": "g", " ": "", "_": "d",
        "A": "abcefg", "b": "cdefg", "C": "adef", "c": "deg", "d": "bcdeg", "E": "adefg",
        "F": "aefg", "G": "acdef", "H": "bcefg", "h": "cefg", "I": "ef", "i": "e", "J": "bcde",
        "L": "def", "n": "ceg", "o": "cdeg", "O": "abcdef", "P": "abefg", "q": "abcfg", "r": "eg",
        "S": "afgcd", "t": "defg", "U": "bcdef", "V": "bcdef", "u": "cde", "y": "bcdfg", "Y": "bcdfg",
        "=": "dg"]

    static func segChar(_ ch: Character) -> String {
        if let s = seg[ch] { return s }
        if let u = ch.uppercased().first, let s = seg[u] { return s }
        if let l = ch.lowercased().first, let s = seg[l] { return s }
        return ""
    }

    static func digit(_ c: CGContext, _ x: CGFloat, _ y: CGFloat, _ w: CGFloat, _ h: CGFloat, _ ch: Character) {
        let t = max(2.0, w * 0.17), sk: CGFloat = 0.08, hh = h / 2, g: CGFloat = 1.0
        let lit = segChar(ch)
        func P(_ px: CGFloat, _ py: CGFloat) -> CGPoint { CGPoint(x: x + px + (h - py) * sk, y: y + py) }
        func hseg(_ px: CGFloat, _ py: CGFloat, _ L: CGFloat) -> [CGPoint] {
            [P(px, py), P(px + t / 2, py - t / 2), P(px + L - t / 2, py - t / 2),
             P(px + L, py), P(px + L - t / 2, py + t / 2), P(px + t / 2, py + t / 2)]
        }
        func vseg(_ px: CGFloat, _ py: CGFloat, _ L: CGFloat) -> [CGPoint] {
            [P(px, py), P(px + t / 2, py + t / 2), P(px + t / 2, py + L - t / 2),
             P(px, py + L), P(px - t / 2, py + L - t / 2), P(px - t / 2, py + t / 2)]
        }
        let segs: [(Character, [CGPoint])] = [
            ("a", hseg(t / 2 + g, t / 2, w - t - 2 * g)), ("g", hseg(t / 2 + g, hh, w - t - 2 * g)),
            ("d", hseg(t / 2 + g, h - t / 2, w - t - 2 * g)),
            ("f", vseg(t / 2, t / 2 + g, hh - t / 2 - 2 * g)), ("e", vseg(t / 2, hh + g, hh - t / 2 - 2 * g)),
            ("b", vseg(w - t / 2, t / 2 + g, hh - t / 2 - 2 * g)), ("c", vseg(w - t / 2, hh + g, hh - t / 2 - 2 * g))]
        for (name, pts) in segs {
            c.beginPath()
            c.addLines(between: pts)
            c.closePath()
            fill(c, lit.contains(name) ? segOn : segOff)
        }
    }

    static func digits(_ c: CGContext, _ text: String, _ x: CGFloat, _ y: CGFloat, _ w: CGFloat, _ h: CGFloat, _ pitch: CGFloat) {
        for (i, ch) in text.enumerated() { digit(c, x + CGFloat(i) * pitch, y, w, h, ch) }
    }

    // ------------------------------------------------------------- Bauteile
    enum Style { case key, small, amber }

    @discardableResult
    static func button(_ c: CGContext, _ x: CGFloat, _ y: CGFloat, _ w: CGFloat, _ h: CGFloat, _ pressed: Bool,
                       _ style: Style = .key, _ label: String? = nil, _ size: CGFloat = 13, led: Bool? = nil,
                       r: CGFloat = 7) -> CGFloat {
        let pal: (RGB, RGB, RGB, RGB)
        switch style {
        case .key: pal = (RGB(0.99, 0.99, 0.99), RGB(0.90, 0.90, 0.91), RGB(0.70, 0.70, 0.72), RGB(0.18, 0.18, 0.20))
        case .small: pal = (RGB(0.95, 0.95, 0.96), RGB(0.87, 0.87, 0.88), RGB(0.68, 0.68, 0.70), RGB(0.30, 0.30, 0.32))
        case .amber: pal = (RGB(1.0, 0.66, 0.24), RGB(0.95, 0.52, 0.08), RGB(0.55, 0.28, 0.03), RGB(0.16, 0.10, 0.04))
        }
        let (top, bot, side, fg) = pal
        let oy: CGFloat = pressed ? 2 : 0
        rrect(c, x, y + 3, w, h, r); fill(c, RGB(0, 0, 0), 0.16)
        rrect(c, x, y + oy, w, h - oy + 1, r); fill(c, side)
        rrect(c, x, y + oy, w, h - 3, r); fillV(c, y, y + h, top, bot)
        c.addRect(CGRect(x: x + r, y: y + oy + 0.6, width: w - 2 * r, height: 1)); fill(c, RGB(1, 1, 1), 0.6)
        if let label = label {
            text(c, label, x + w / 2, y + oy + (h - 3) / 2 + size * 0.36, size, fg)
        }
        if let led = led {
            circle(c, x + w - 10, y + oy + 10, 3.2)
            fill(c, led ? ledOn : RGB(0.80, 0.80, 0.81))
        }
        return oy
    }

    static func tri(_ c: CGContext, _ pts: [CGPoint]) {
        c.beginPath(); c.addLines(between: pts); c.closePath(); c.fillPath()
    }

    static func icon(_ c: CGContext, _ kind: String, _ cx: CGFloat, _ cy: CGFloat, _ col: RGB) {
        c.setFillColor(col.cg())
        switch kind {
        case "prev":
            c.fill(CGRect(x: cx - 12, y: cy - 9, width: 3, height: 18))
            for dx: CGFloat in [0, 11] {
                tri(c, [CGPoint(x: cx + 2 + dx, y: cy - 9), CGPoint(x: cx - 8 + dx, y: cy), CGPoint(x: cx + 2 + dx, y: cy + 9)])
            }
        case "next":
            for dx: CGFloat in [0, 11] {
                tri(c, [CGPoint(x: cx - 13 + dx, y: cy - 9), CGPoint(x: cx - 3 + dx, y: cy), CGPoint(x: cx - 13 + dx, y: cy + 9)])
            }
            c.fill(CGRect(x: cx + 9, y: cy - 9, width: 3, height: 18))
        case "stop":
            c.fill(CGRect(x: cx - 8, y: cy - 8, width: 16, height: 16))
        default:
            tri(c, [CGPoint(x: cx - 18, y: cy - 10), CGPoint(x: cx - 4, y: cy), CGPoint(x: cx - 18, y: cy + 10)])
            c.fill(CGRect(x: cx + 4, y: cy - 10, width: 4, height: 20))
            c.fill(CGRect(x: cx + 12, y: cy - 10, width: 4, height: 20))
        }
    }

    static func knob(_ c: CGContext, _ value: CGFloat) {
        let cx = knobC.x, cy = knobC.y
        for i in 0..<21 {
            let a = (225 - 13.5 * CGFloat(i)) * .pi / 180
            let r0 = knobR + 7, r1 = knobR + (i % 5 == 0 ? 13 : 10)
            let a2 = a + 0.015
            let p1 = CGPoint(x: cx + cos(a) * r0, y: cy - sin(a) * r0)
            let p2 = CGPoint(x: cx + cos(a) * r1, y: cy - sin(a) * r1)
            let p3 = CGPoint(x: cx + cos(a2) * r1, y: cy - sin(a2) * r1)
            let p4 = CGPoint(x: cx + cos(a2) * r0, y: cy - sin(a2) * r0)
            c.beginPath()
            c.addLines(between: [p1, p2, p3, p4])
            c.closePath()
            fill(c, txtDim)
        }
        circle(c, cx, cy + 4, knobR); fill(c, RGB(0, 0, 0), 0.2)
        circle(c, cx, cy, knobR); fillV(c, cy - knobR, cy + knobR, RGB(0.96, 0.96, 0.97), RGB(0.78, 0.78, 0.80))
        circle(c, cx, cy, knobR - 7)
        fillRadial(c, CGPoint(x: cx - 12, y: cy - 14), 4, CGPoint(x: cx, y: cy), knobR - 7,
                   [(0, RGB(1, 1, 1)), (1, RGB(0.90, 0.90, 0.91))])
        let a = (225 - 270 * max(0, min(1, value))) * .pi / 180
        let ca = cos(a), sa = sin(a), px = -sa, py = -ca
        let r0: CGFloat = 12, r1 = knobR - 10
        let q1 = CGPoint(x: cx + ca * r0 + px * 2, y: cy - sa * r0 + py * 2)
        let q2 = CGPoint(x: cx + ca * r1 + px * 2, y: cy - sa * r1 + py * 2)
        let q3 = CGPoint(x: cx + ca * r1 - px * 2, y: cy - sa * r1 - py * 2)
        let q4 = CGPoint(x: cx + ca * r0 - px * 2, y: cy - sa * r0 - py * 2)
        c.beginPath()
        c.addLines(between: [q1, q2, q3, q4])
        c.closePath()
        fill(c, amber)
    }

    static func fader(_ c: CGContext, _ value: CGFloat) {
        let x = faderX
        for i in 0..<9 {
            let y = faderY1 - CGFloat(i) * (faderY1 - faderY0) / 8
            c.addRect(CGRect(x: x - 30, y: y - 0.6, width: i == 4 ? 16 : 12, height: 1.2))
            fill(c, i == 4 ? amber : txtDim)
        }
        rrect(c, x - 4, faderY0 - 8, 8, faderY1 - faderY0 + 16, 4); fill(c, RGB(0.30, 0.30, 0.32))
        let cy = faderY1 - max(0, min(1, value)) * (faderY1 - faderY0)
        rrect(c, x - 22, cy - 11, 44, 26, 4); fill(c, RGB(0, 0, 0), 0.2)
        rrect(c, x - 22, cy - 14, 44, 28, 4); fillV(c, cy - 14, cy + 14, RGB(1, 1, 1), RGB(0.86, 0.86, 0.87))
        c.addRect(CGRect(x: x - 18, y: cy - 1, width: 36, height: 2)); fill(c, amber)
    }

    static func spindle(_ c: CGContext) {
        circle(c, 0, 0, 30); fillV(c, -30, 30, RGB(0.80, 0.80, 0.82), RGB(0.45, 0.45, 0.47))
        circle(c, 0, 0, 22); fillV(c, -22, 22, RGB(0.40, 0.40, 0.42), RGB(0.75, 0.75, 0.77))
        for i in 0..<3 {
            let a = CGFloat(i) * 2 * .pi / 3 + 0.3
            circle(c, cos(a) * 14, sin(a) * 14, 3.2); fill(c, RGB(0.95, 0.95, 0.96))
        }
        circle(c, 0, 0, 5); fill(c, RGB(0.15, 0.15, 0.16))
    }

    static func disc(_ c: CGContext, _ st: FaceState) {
        circle(c, discC.x + 3, discC.y + 8, discR); fill(c, RGB(0, 0, 0), 0.5)
        c.saveGState()
        c.translateBy(x: discC.x, y: discC.y)
        c.rotate(by: st.discAngle)
        circle(c, 0, 0, discR)
        fillRadial(c, CGPoint(x: -60, y: -80), 10, .zero, discR,
                   [(0, RGB(0.86, 0.87, 0.89)), (0.7, RGB(0.66, 0.67, 0.70)), (1, RGB(0.78, 0.79, 0.82))])
        let pr = discR - 4
        if let cover = st.cover {
            c.saveGState()
            circle(c, 0, 0, pr)
            c.clip()
            c.translateBy(x: -pr, y: pr)
            c.scaleBy(x: 1, y: -1)
            c.interpolationQuality = .high
            c.draw(cover, in: CGRect(x: 0, y: 0, width: 2 * pr, height: 2 * pr))
            c.restoreGState()
        } else {
            let col = st.discColor
            circle(c, 0, 0, pr); fill(c, col)
            let ink = col.sum > 1.8 ? RGB(0.12, 0.12, 0.13) : RGB(0.95, 0.94, 0.90)
            for rr in [discR - 22, discR - 27, hubR + 24] {
                circle(c, 0, 0, rr); fill(c, ink, 0.4)
                circle(c, 0, 0, rr - 1.2); fill(c, col)
            }
            let lines = st.discLines
            if let first = lines.first { text(c, String(first.prefix(22)), 0, -128, 22, ink, bold: true) }
            for (i, ln) in lines.dropFirst().prefix(4).enumerated() {
                text(c, String(ln.prefix(30)), 0, -100 + CGFloat(i) * 16, 12, ink)
            }
            text(c, "thisismade", 0, 150, 18, ink)
            text(c, "COMPACT DISC · DIGITAL AUDIO", 0, 170, 9, ink)
            circle(c, 150, 0, 6); fill(c, amber)
        }
        circle(c, 0, 0, hubR); fill(c, RGB(0.55, 0.57, 0.60))
        circle(c, 0, 0, hubR - 3); fill(c, RGB(0.30, 0.31, 0.33))
        spindle(c)
        c.restoreGState()
    }

    // ------------------------------------------------------------- Gesamtbild
    static func draw(_ c: CGContext, _ st: FaceState) {
        drawStatic(c)
        drawDynamic(c, st)
    }

    static func drawStatic(_ c: CGContext) {
        rrect(c, 0, 10, devW, devH, 18); fill(c, RGB(0, 0, 0), 0.22)
        rrect(c, 0, 0, devW, devH, 18); fillV(c, 0, devH, RGB(0.985, 0.985, 0.98), RGB(0.90, 0.90, 0.90))
        c.addRect(CGRect(x: 18, y: 1, width: devW - 36, height: 1.2)); fill(c, RGB(1, 1, 1), 0.9)

        text(c, "thisismade", 40, 42, 24, RGB(0.12, 0.12, 0.13), align: .left, bold: true)
        text(c, "CD PLAYER  ·  CDP-2", 184, 41, 12, txtDim, align: .left)

        let cx = discC.x, cy = discC.y
        circle(c, cx, cy, wellR + 3); fill(c, RGB(0.80, 0.80, 0.81))
        circle(c, cx, cy, wellR)
        fillRadial(c, CGPoint(x: cx, y: cy - 40), 40, discC, wellR, [(0, RGB(0.10, 0.10, 0.11)), (1, RGB(0.05, 0.05, 0.055))])
        c.saveGState()
        c.translateBy(x: cx, y: cy)
        c.rotate(by: 135 * .pi / 180)
        rrect(c, 60, -20, 190, 40, 8); fill(c, RGB(0.02, 0.02, 0.025))
        circle(c, 150, 0, 9); fill(c, RGB(0.20, 0.22, 0.30))
        circle(c, 150, 0, 4); fill(c, RGB(0.45, 0.50, 0.75))
        c.restoreGState()

        let d = display
        rrect(c, d.minX - 6, d.minY - 6, d.width + 12, d.height + 12, 12); fill(c, RGB(0.80, 0.80, 0.81))
        rrect(c, d.minX, d.minY, d.width, d.height, 7); fillV(c, d.minY, d.maxY, RGB(0.045, 0.025, 0.025), RGB(0.07, 0.035, 0.035))

        text(c, "VOLUME", knobC.x, knobC.y + knobR + 26, 11, txtDim)
        text(c, "MEMORY", 630, memY - 10, 11, txtDim, align: .left)
        text(c, "SHUTTLE", shuttle.minX, memY - 10, 11, txtDim, align: .left)
        text(c, "TEMPO", faderX, faderY0 - 30, 11, txtDim)
        text(c, "+", faderX + 26, faderY0 + 4, 12, txtDim)
        text(c, "−", faderX + 26, faderY1 + 4, 12, txtDim)
    }

    static func drawDynamic(_ c: CGContext, _ st: FaceState) {
        let P = st.pressed, on = st.powerOn

        for (id, t, x) in topBtns {
            button(c, x, topY, topW, topH, P.contains(id), .small, t, 10, r: 5)
            if id == "power" {
                circle(c, x + 9, topY + 13, 2.6); fill(c, on ? ledOn : RGB(0.80, 0.80, 0.81))
            }
        }
        circle(c, 1146, 31, 3.0); fill(c, (st.mediaLED && on) ? RGB(0.30, 0.65, 1.0) : RGB(0.80, 0.80, 0.81))
        text(c, "MEDIA", 1156, 35, 9, txtDim, align: .left)

        if st.discLoaded {
            disc(c, st)
        } else {
            c.saveGState()
            c.translateBy(x: discC.x, y: discC.y)
            c.rotate(by: st.discAngle)
            spindle(c)
            c.restoreGState()
            text(c, "NO DISC", discC.x, discC.y + 70, 14, RGB(0.85, 0.85, 0.86))
            text(c, "OPEN = Ordner · FILES = Dateien · oder hierher ziehen", discC.x, discC.y + 92, 11, txtDim)
        }

        drawDisplay(c, st)

        for (lab, x, y) in keys {
            let t = lab == "T" ? "TIME" : (lab == "C" ? "CLR" : lab)
            button(c, x, y, keyW, keyH, P.contains("key_" + lab), .key, t, t.count == 1 ? 17 : 11)
        }
        button(c, enter.minX, enter.minY, enter.width, enter.height, P.contains("enter"), .key, "ENTER", 12)

        knob(c, st.levelNorm)

        for (i, m) in mem.enumerated() {
            button(c, m.2, memY, memW, memH, P.contains(m.0), .key, m.1, 17, led: st.cueSet[i] && on)
        }

        let s = shuttle
        rrect(c, s.minX, s.minY + 12, s.width, s.height - 24, 10); fill(c, RGB(0.30, 0.30, 0.32))
        text(c, "REW", s.minX + 16, s.maxY + 14, 10, txtDim)
        text(c, "FF", s.maxX - 12, s.maxY + 14, 10, txtDim)
        let jx = s.midX + st.jog * jogTravel
        rrect(c, jx - 22, s.minY + 4, 44, s.height - 4, 6); fill(c, RGB(0, 0, 0), 0.2)
        rrect(c, jx - 22, s.minY, 44, s.height - 4, 6); fillV(c, s.minY, s.maxY, RGB(1, 1, 1), RGB(0.86, 0.86, 0.87))
        c.addRect(CGRect(x: jx - 1.5, y: s.minY + 6, width: 3, height: s.height - 16)); fill(c, amber)

        fader(c, st.varispeedNorm)

        for (id, x, w) in transport {
            let oy = button(c, x, trY, w, trH, P.contains(id), id == "play" ? .amber : .key)
            icon(c, id, x + w / 2, trY + oy + trH / 2 - 2, id == "play" ? RGB(0.16, 0.10, 0.04) : RGB(0.18, 0.18, 0.20))
        }

        let leds: [String: Bool?] = ["keylock": st.keyLock, "repeat": st.repeatMode > 0, "shuffle": st.shuffle, "eject": nil]
        for (id, t, x) in small {
            let l: Bool? = (leds[id] ?? nil).map { $0 && on }
            button(c, x, smallY, smallW, smallH, P.contains(id), .small, t, 10, led: l, r: 5)
        }

        if !on {
            rrect(c, 0, 0, devW, devH, 18); fill(c, RGB(0, 0, 0), 0.12)
        }
    }

    static func drawDisplay(_ c: CGContext, _ st: FaceState) {
        let d = display, x = d.minX, y = d.minY, w = d.width
        let on = st.powerOn
        func L(_ a: Bool) -> RGB { (a && on) ? segOn : segOff }
        let dw: CGFloat = 26, dh: CGFloat = 46, pitch: CGFloat = 34
        var main = Array((on ? st.mainText : "") + String(repeating: " ", count: 12)).prefix(12).map { $0 }
        if !on { main = Array(repeating: " ", count: 12) }
        func part(_ a: Int, _ b: Int) -> String { String(main[a..<b]) }
        if on && st.msgMode {
            digits(c, part(0, 12), x + 18, y + 38, dw, dh, pitch)
        } else {
            text(c, "TRACK", x + 18, y + 26, 10, L(true), align: .left)
            text(c, "TOTAL", x + 136, y + 26, 10, L(true), align: .left)
            text(c, "TIME", x + 254, y + 26, 10, L(true), align: .left)
            digits(c, part(0, 3), x + 18, y + 38, dw, dh, pitch)
            digits(c, part(3, 6), x + 136, y + 38, dw, dh, pitch)
            digits(c, part(6, 9), x + 254, y + 38, dw, dh, pitch)
            for dy: CGFloat in [14, 32] {
                circle(c, x + 362 + (46 - dy) * 0.08, y + 38 + dy, 3); fill(c, L(true))
            }
            digits(c, part(10, 12), x + 372, y + 38, dw, dh, pitch)
        }
        let ind: [(String, Bool)] = [(st.repeatMode == 2 ? "REPEAT 1" : "REPEAT", st.repeatMode > 0), ("SHUFFLE", st.shuffle),
                                     ("KEY LOCK", st.keyLock), ("PAUSE", st.paused), ("REMAIN", st.remain)]
        for (i, item) in ind.enumerated() {
            text(c, item.0, x + w - 14, y + 26 + CGFloat(i) * 15, 10, L(item.1), align: .right)
        }
        let by = y + 118
        text(c, "TEMPO", x + 18, by - 6, 10, L(true), align: .left)
        digits(c, on ? st.vsText : "   ", x + 18, by, 15, 26, 20)
        text(c, "%", x + 84, by + 25, 12, L(true), align: .left)
        text(c, "VOL", x + 110, by - 6, 10, L(true), align: .left)
        digits(c, on ? st.lvText : "   ", x + 110, by, 15, 26, 20)
        let mx = x + 200, n = 30
        for row in 0..<2 {
            let yy = by + 2 + CGFloat(row) * 15
            text(c, row == 0 ? "L" : "R", mx, yy + 9, 10, L(true), align: .left)
            let lit = Int((max(0, min(1, on ? st.vu[row] : 0)) * CGFloat(n)).rounded())
            let pk = Int((max(0, min(1, on ? st.peaks[row] : 0)) * CGFloat(n)).rounded())
            for i in 0..<n {
                c.addRect(CGRect(x: mx + 14 + CGFloat(i) * 10.5, y: yy, width: 8, height: 10))
                let hot = i >= n - 5
                let isOn = i < lit || (pk > 0 && i == pk - 1)
                fill(c, isOn ? (hot ? RGB(1.0, 0.62, 0.14) : segOn) : (hot ? RGB(0.20, 0.11, 0.03) : segOff))
            }
        }
    }
}
