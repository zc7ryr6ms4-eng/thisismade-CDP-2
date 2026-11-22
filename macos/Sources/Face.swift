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
    var title = ""
    var resolution = ""
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

    // ------------------------------------------------------------- Minimal-Design
    static let body = RGB(0.955, 0.955, 0.95)
    static let line = RGB(0.74, 0.74, 0.75)
    static let dot = RGB(0.80, 0.80, 0.81)
    static let ink = RGB(0.12, 0.12, 0.13)
    static let keyCol = RGB(0.985, 0.985, 0.98)
    static let keyHi = RGB(0.90, 0.90, 0.90)
    static let orange = RGB(1.0, 0.40, 0.0)
    static let orangeDim = RGB(0.86, 0.80, 0.75)

    static func mono(_ c: CGContext, _ s: String, _ x: CGFloat, _ y: CGFloat, _ size: CGFloat,
                     _ col: RGB = txtDim, align: Align = .left) {
        let font = NSFont.monospacedSystemFont(ofSize: size, weight: .regular)
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

    static func stroke(_ c: CGContext, _ col: RGB, _ w: CGFloat = 1) {
        c.setStrokeColor(col.cg())
        c.setLineWidth(w)
        c.strokePath()
    }

    /// Füllt und umrandet den Pfad, den `shape` anlegt.
    static func fillStroke(_ c: CGContext, _ fillCol: RGB, _ edge: RGB, _ w: CGFloat = 1, _ shape: () -> Void) {
        shape(); fill(c, fillCol)
        shape(); stroke(c, edge, w)
    }

    static func ln(_ c: CGContext, _ x0: CGFloat, _ y0: CGFloat, _ x1: CGFloat, _ y1: CGFloat,
                   _ col: RGB = line, _ w: CGFloat = 1) {
        c.beginPath()
        c.move(to: CGPoint(x: x0, y: y0))
        c.addLine(to: CGPoint(x: x1, y: y1))
        stroke(c, col, w)
    }

    static func led(_ c: CGContext, _ x: CGFloat, _ y: CGFloat, _ on: Bool) {
        c.addRect(CGRect(x: x - 3, y: y - 3, width: 6, height: 6))
        fill(c, on ? orange : orangeDim)
    }

    static func roundKey(_ c: CGContext, _ cx: CGFloat, _ cy: CGFloat, _ r: CGFloat, _ pressed: Bool, _ col: RGB) {
        fillStroke(c, pressed ? orange : col, pressed ? orange : line) { circle(c, cx, cy, r) }
    }

    static func squareKey(_ c: CGContext, _ x: CGFloat, _ y: CGFloat, _ w: CGFloat, _ h: CGFloat,
                          _ pressed: Bool, _ col: RGB, _ r: CGFloat = 6) {
        fillStroke(c, pressed ? orange : col, pressed ? orange : line) { rrect(c, x, y, w, h, r) }
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


    // ------------------------------------------------------------- Gesamtbild
    static func draw(_ c: CGContext, _ st: FaceState) {
        drawStatic(c)
        drawDynamic(c, st)
    }

    static func drawStatic(_ c: CGContext) {
        rrect(c, 0, 6, devW, devH, 14); fill(c, RGB(0, 0, 0), 0.18)
        fillStroke(c, body, RGB(0.80, 0.80, 0.81), 1.2) { rrect(c, 0, 0, devW, devH, 14) }

        for j in stride(from: CGFloat(13), to: devH - 8, by: 16) {
            for i in stride(from: CGFloat(13), to: 600, by: 16) {
                if hypot(i - discC.x, j - discC.y) < wellR + 10 { continue }
                circle(c, i, j, 1.1)
            }
        }
        fill(c, dot)

        ln(c, 610, 14, 610, devH - 14)
        ln(c, 620, 255, devW - 14, 255)
        ln(c, 620, 392, devW - 14, 392)
        ln(c, 620, 578, 1075, 578)
        ln(c, 1075, 255, 1075, devH - 14)

        text(c, "thisismade", 30, 44, 24, ink, align: .left, bold: true)
        mono(c, "CDP-2 / COMPACT DISC PLAYER", 31, 62, 10)
        rrect(c, 520, 34, 54, 14, 7); stroke(c, orange)
        mono(c, "AUDIO", 547, 45, 9, orange, align: .center)

        let cx = discC.x, cy = discC.y
        fillStroke(c, RGB(0.90, 0.90, 0.895), line) { circle(c, cx, cy, wellR) }
        for rr in stride(from: CGFloat(80), to: wellR - 6, by: 18) {
            circle(c, cx, cy, rr); stroke(c, RGB(0.84, 0.84, 0.84))
        }
        for k in 0..<12 {
            let a = 2 * CGFloat.pi * CGFloat(k) / 12
            ln(c, cx + cos(a) * (wellR - 10), cy + sin(a) * (wellR - 10),
               cx + cos(a) * (wellR - 2), cy + sin(a) * (wellR - 2), txtDim)
        }

        let d = display
        fillStroke(c, RGB(0.06, 0.05, 0.045), RGB(0.55, 0.55, 0.56)) {
            rrect(c, d.minX - 4, d.minY - 4, d.width + 8, d.height + 8, 8)
        }

        let labels: [(String, CGFloat, CGFloat)] = [
            ("01  NUMBER", 630, 266), ("02  VOLUME", 1086, 268), ("03  MEMORY", 630, 406),
            ("04  SHUTTLE", 890, 406), ("05  TRANSPORT", 630, 476), ("06  TEMPO", 1086, 406),
            ("07  MODE", 630, 588)]
        for (t, tx, ty) in labels { mono(c, t, tx, ty, 9) }
    }

    static func drawDynamic(_ c: CGContext, _ st: FaceState) {
        let P = st.pressed, on = st.powerOn

        for (id, t, x) in topBtns {
            let pr = P.contains(id)
            fillStroke(c, pr ? orange : body, (pr || id == "power") ? orange : line) {
                rrect(c, x, topY, topW, topH - 2, 12)
            }
            mono(c, t.lowercased(), x + topW / 2, topY + 16, 10,
                 pr ? body : (id == "power" ? orange : ink), align: .center)
        }
        led(c, 1146, 31, st.mediaLED && on)
        mono(c, "media", 1155, 35, 8)

        if st.discLoaded {
            disc(c, st)
        } else {
            c.saveGState()
            c.translateBy(x: discC.x, y: discC.y)
            c.rotate(by: st.discAngle)
            spindle(c)
            c.restoreGState()
            mono(c, "no disc", discC.x, discC.y + 70, 13, ink, align: .center)
            mono(c, "open / files / drop", discC.x, discC.y + 90, 10, align: .center)
        }

        drawDisplay(c, st)

        for (lab, x, y) in keys {
            let cx = x + keyW / 2, cy = y + keyH / 2 + 6
            let pr = P.contains("key_" + lab)
            roundKey(c, cx, cy, 19, pr, (lab == "T" || lab == "C") ? keyHi : keyCol)
            let t = lab == "T" ? "time" : (lab == "C" ? "clr" : lab)
            mono(c, t, cx, cy + (t.count == 1 ? 5 : 3.5), t.count == 1 ? 15 : 10, pr ? body : ink, align: .center)
        }
        let pe = P.contains("enter")
        squareKey(c, enter.minX, enter.minY + 12, enter.width, enter.height - 14, pe, keyHi, 10)
        mono(c, "enter", enter.midX, enter.minY + 12 + (enter.height - 14) / 2 + 4, 11, pe ? body : orange, align: .center)

        knob(c, st.levelNorm)

        for (i, m) in mem.enumerated() {
            let pr = P.contains(m.0)
            squareKey(c, m.2, memY + 2, memW, memH - 6, pr, keyCol, 8)
            mono(c, m.1.lowercased(), m.2 + 16, memY + 28, 15, pr ? body : ink)
            led(c, m.2 + memW - 14, memY + 19, st.cueSet[i] && on)
        }

        let s = shuttle
        let scy = s.minY + s.height / 2 + 2
        ln(c, s.minX, scy, s.maxX, scy, line, 2)
        for k in -3...3 {
            let tx = s.midX + CGFloat(k) * s.width / 7
            ln(c, tx, scy - 6, tx, scy + 6, k == 0 ? orange : txtDim)
        }
        mono(c, "rew", s.minX, s.maxY + 12, 9)
        mono(c, "ff", s.maxX, s.maxY + 12, 9, align: .right)
        let jx = s.midX + st.jog * jogTravel
        c.addRect(CGRect(x: jx - 10, y: scy - 12, width: 20, height: 24)); fill(c, orange)

        fader(c, st.varispeedNorm)

        for (id, x, w) in transport {
            let pr = P.contains(id), play = id == "play"
            squareKey(c, x, trY + 6, w, trH - 12, pr, play ? orange : keyCol, 12)
            icon(c, id, x + w / 2, trY + trH / 2, (pr || play) ? body : ink)
        }

        for (id, t, x) in small {
            let pr = P.contains(id)
            let ledState: Bool?
            switch id {
            case "keylock": ledState = st.keyLock
            case "repeat": ledState = st.repeatMode > 0
            case "shuffle": ledState = st.shuffle
            default: ledState = nil
            }
            fillStroke(c, pr ? orange : body, pr ? orange : line) { rrect(c, x, smallY + 12, smallW, smallH - 8, 13) }
            mono(c, t.lowercased(), x + smallW / 2 - (ledState != nil ? 6 : 0), smallY + 29, 9,
                 pr ? body : ink, align: .center)
            if let l = ledState { led(c, x + smallW - 12, smallY + 25, l && on) }
        }

        if !on {
            rrect(c, 0, 0, devW, devH, 14); fill(c, RGB(0, 0, 0), 0.12)
        }
    }

    static func spindle(_ c: CGContext) {
        fillStroke(c, RGB(0.86, 0.86, 0.86), line) { circle(c, 0, 0, 26) }
        circle(c, 0, 0, 7); fill(c, orange)
    }

    static func disc(_ c: CGContext, _ st: FaceState) {
        c.saveGState()
        c.translateBy(x: discC.x, y: discC.y)
        c.rotate(by: st.discAngle)
        circle(c, 0, 2, discR); fill(c, RGB(0, 0, 0), 0.10)
        fillStroke(c, RGB(0.995, 0.995, 0.99), line) { circle(c, 0, 0, discR) }
        let pr = discR - 2
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
            let inkD = RGB(0.10, 0.10, 0.11)
            circle(c, 0, 0, discR - 14); stroke(c, RGB(0.80, 0.80, 0.81))
            circle(c, 0, 0, hubR + 30); stroke(c, RGB(0.80, 0.80, 0.81))
            let lines = st.discLines
            if let first = lines.first { text(c, String(first.prefix(22)).lowercased(), -150, -120, 22, inkD, align: .left, bold: true) }
            for (i, l) in lines.dropFirst().prefix(4).enumerated() {
                mono(c, String(l.prefix(30)).lowercased(), -150, -96 + CGFloat(i) * 15, 10, RGB(0.30, 0.30, 0.32))
            }
            mono(c, "thisismade / cdp-2", -150, 170, 10, inkD)
            c.addRect(CGRect(x: discR - 40, y: -5, width: 24, height: 10)); fill(c, orange)
        }
        fillStroke(c, RGB(0.93, 0.93, 0.93), line) { circle(c, 0, 0, hubR) }
        spindle(c)
        c.restoreGState()
    }

    static func knob(_ c: CGContext, _ value: CGFloat) {
        // mittig im Kasten "02 VOLUME" (x 1075…1186, y 255…392), samt Skala
        let cx: CGFloat = 1131, cy: CGFloat = 331, r: CGFloat = 33
        for i in 0..<31 {
            let a = (225 - 9 * CGFloat(i)) * .pi / 180
            let r0 = r + 5, r1 = r + (i % 5 == 0 ? 12 : 8)
            let lit = CGFloat(i) / 30 <= value + 1e-6
            ln(c, cx + cos(a) * r0, cy - sin(a) * r0, cx + cos(a) * r1, cy - sin(a) * r1,
               lit ? orange : line, i % 5 == 0 ? 1.4 : 1)
        }
        fillStroke(c, keyCol, line) { circle(c, cx, cy, r) }
        let a = (225 - 270 * max(0, min(1, value))) * .pi / 180
        c.setLineCap(.round)
        ln(c, cx + cos(a) * 10, cy - sin(a) * 10, cx + cos(a) * (r - 6), cy - sin(a) * (r - 6), orange, 3)
        c.setLineCap(.butt)
    }

    static func fader(_ c: CGContext, _ value: CGFloat) {
        let x = faderX, y0 = faderY0 + 4, y1 = faderY1 - 10
        ln(c, x, y0, x, y1, line, 2)
        for i in 0..<11 {
            let y = y1 - CGFloat(i) * (y1 - y0) / 10
            ln(c, x + 18, y, x + (i % 5 == 0 ? 30 : 24), y, i == 5 ? orange : txtDim)
        }
        mono(c, "+", x - 26, y0 + 8, 11)
        mono(c, "-", x - 26, y1 + 2, 11)
        let cy = y1 - max(0, min(1, value)) * (y1 - y0)
        c.addRect(CGRect(x: x - 16, y: cy - 9, width: 32, height: 18)); fill(c, RGB(0.16, 0.16, 0.17))
        c.addRect(CGRect(x: x - 16, y: cy - 1, width: 32, height: 2)); fill(c, orange)
    }

    static func drawDisplay(_ c: CGContext, _ st: FaceState) {
        let d = display, x = d.minX, y = d.minY, w = d.width
        let on = st.powerOn
        func L(_ a: Bool) -> RGB { (a && on) ? segOn : segOff }
        let dw: CGFloat = 26, dh: CGFloat = 46, pitch: CGFloat = 34
        var main: [Character] = Array(((on ? st.mainText : "") + String(repeating: " ", count: 12)).prefix(12))
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
            if on { titleLine(c, st, x, y, w, L(true)) }
        }
        let ind: [(String, Bool)] = [(st.repeatMode == 2 ? "REPEAT 1" : "REPEAT", st.repeatMode > 0), ("SHUFFLE", st.shuffle),
                                     ("KEY LOCK", st.keyLock), ("PAUSE", st.paused), ("REMAIN", st.remain)]
        for (i, item) in ind.enumerated() {
            text(c, item.0, x + w - 14, y + 26 + CGFloat(i) * 15, 10, L(item.1), align: .right)
        }
        let by = y + 126
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
                let col: RGB = isOn ? (hot ? RGB(1.0, 0.62, 0.14) : segOn) : (hot ? RGB(0.20, 0.11, 0.03) : segOff)
                fill(c, col)
            }
        }
    }

    /// Titel (Laufschrift bei langen Namen) und Auflösung, innerhalb des Displays.
    static func titleLine(_ c: CGContext, _ st: FaceState, _ x: CGFloat, _ y: CGFloat, _ w: CGFloat, _ col: RGB) {
        let ty = y + 101
        let font = NSFont.systemFont(ofSize: 11, weight: .semibold)
        let attrs: [NSAttributedString.Key: Any] = [.font: font, .foregroundColor: NSColor(cgColor: col.cg()) ?? .red]
        let res = NSAttributedString(string: st.resolution, attributes: attrs)
        let rw = st.resolution.isEmpty ? 0 : res.size().width
        NSGraphicsContext.saveGraphicsState()
        NSGraphicsContext.current = NSGraphicsContext(cgContext: c, flipped: true)
        if !st.resolution.isEmpty { res.draw(at: NSPoint(x: x + w - 14 - rw, y: ty - font.ascender)) }
        if !st.title.isEmpty {
            let title = NSAttributedString(string: st.title, attributes: attrs)
            let boxX = x + 18, boxW = w - 32 - rw - (st.resolution.isEmpty ? 0 : 16)
            let tw = title.size().width
            c.saveGState()
            c.clip(to: CGRect(x: boxX, y: ty - 13, width: boxW, height: 17))
            if tw <= boxW {
                title.draw(at: NSPoint(x: boxX, y: ty - font.ascender))
            } else {
                let gap: CGFloat = 50
                let off = CGFloat(ProcessInfo.processInfo.systemUptime * 28).truncatingRemainder(dividingBy: tw + gap)
                for k in 0..<2 {
                    title.draw(at: NSPoint(x: boxX - off + CGFloat(k) * (tw + gap), y: ty - font.ascender))
                }
            }
            c.restoreGState()
        }
        NSGraphicsContext.restoreGraphicsState()
    }
}
