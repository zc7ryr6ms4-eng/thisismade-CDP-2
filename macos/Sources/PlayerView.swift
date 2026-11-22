// Die Gerätefront als NSView: Zeichnen, Maus, Mausrad, Tastatur, Drag & Drop.
import AppKit

final class PlayerView: NSView {
    let player: Player
    private var timer: Timer?
    private var lastTick = Player.now()
    private var idleAcc: TimeInterval = 0

    private struct Action {
        let id: String
        let start: CGPoint          // Fensterkoordinaten der View
        let right: Bool
        let shift: Bool
        var startValue = 0
        var moved: CGFloat = 0
        var longDone = false
        var prevAngle: CGFloat = 0
        var wasPlaying = false
        var scrub: Double = 0
        var lastSeek: TimeInterval = 0
    }
    private var act: Action?
    private var longTimer: Timer?
    private var jogTimer: Timer?

    init(player: Player) {
        self.player = player
        super.init(frame: NSRect(x: 0, y: 0, width: Face.canvasW * 0.6, height: Face.canvasH * 0.6))
        registerForDraggedTypes([.fileURL])
        player.onChange = { [weak self] in self?.needsDisplay = true }
        timer = Timer.scheduledTimer(withTimeInterval: 1.0 / 60, repeats: true) { [weak self] _ in self?.tick() }
        RunLoop.main.add(timer!, forMode: .eventTracking)
    }

    required init?(coder: NSCoder) { fatalError("init(coder:) not used") }

    override var isFlipped: Bool { true }
    override var acceptsFirstResponder: Bool { true }
    override func acceptsFirstMouse(for event: NSEvent?) -> Bool { true }
    override var mouseDownCanMoveWindow: Bool { false }

    // ------------------------------------------------------------ Zeichnen
    private var fit: (s: CGFloat, ox: CGFloat, oy: CGFloat) {
        let s = min(bounds.width / Face.canvasW, bounds.height / Face.canvasH)
        return (s, (bounds.width - Face.canvasW * s) / 2, (bounds.height - Face.canvasH * s) / 2)
    }

    private func toDev(_ p: CGPoint) -> CGPoint {
        let f = fit
        return CGPoint(x: (p.x - f.ox) / f.s - Face.marginX, y: (p.y - f.oy) / f.s - Face.marginTop)
    }

    override func draw(_ dirtyRect: NSRect) {
        guard let c = NSGraphicsContext.current?.cgContext else { return }
        c.clear(bounds)
        let f = fit
        c.saveGState()
        c.translateBy(x: f.ox, y: f.oy)
        c.scaleBy(x: f.s, y: f.s)
        c.translateBy(x: Face.marginX, y: Face.marginTop)
        Face.draw(c, player.faceState())
        c.restoreGState()
    }

    private func tick() {
        let now = Player.now()
        let dt = min(0.1, now - lastTick)
        lastTick = now
        if player.animate(dt) || act != nil {
            needsDisplay = true
            idleAcc = 0
        } else {
            idleAcc += dt
            if idleAcc > 0.25 { idleAcc = 0; needsDisplay = true }
        }
    }

    // ------------------------------------------------------------ Cursor
    override func updateTrackingAreas() {
        super.updateTrackingAreas()
        trackingAreas.forEach(removeTrackingArea)
        addTrackingArea(NSTrackingArea(rect: bounds, options: [.mouseMoved, .activeAlways, .inVisibleRect], owner: self))
    }

    override func mouseMoved(with event: NSEvent) {
        let id = Face.hit(toDev(convert(event.locationInWindow, from: nil)))
        switch id {
        case nil: NSCursor.arrow.set()
        case "disc"?: NSCursor.openHand.set()
        case "jog"?: NSCursor.resizeLeftRight.set()
        case "varispeed"?, "level"?: NSCursor.resizeUpDown.set()
        default: NSCursor.pointingHand.set()
        }
    }

    // ------------------------------------------------------------ Maus
    override func mouseDown(with event: NSEvent) { begin(event, right: false) }
    override func rightMouseDown(with event: NSEvent) { begin(event, right: true) }
    override func mouseDragged(with event: NSEvent) { update(event) }
    override func rightMouseDragged(with event: NSEvent) { update(event) }
    override func mouseUp(with event: NSEvent) { end(event) }
    override func rightMouseUp(with event: NSEvent) { end(event) }

    private func begin(_ event: NSEvent, right: Bool) {
        window?.makeFirstResponder(self)
        let p = convert(event.locationInWindow, from: nil)
        let d = toDev(p)
        let id = Face.hit(d)
        let pl = player

        if right && (id == nil || id == "disc") {
            if let menu = NSApp.mainMenu?.item(withTitle: "Ablage")?.submenu {
                NSMenu.popUpContextMenu(menu, with: event, for: self)
            }
            return
        }
        guard let rid = id, !(rid == "disc" && !pl.powerOn) else {
            window?.performDrag(with: event)
            return
        }
        if !pl.powerOn && rid != "power" { return }

        var a = Action(id: rid, start: p, right: right, shift: event.modifierFlags.contains(.shift))
        switch rid {
        case "varispeed", "level":
            if event.clickCount == 2 && rid == "varispeed" {
                pl.setVarispeed(100)
                pl.flash("tEnPo 100", 0.6)
            }
            a.startValue = rid == "varispeed" ? pl.varispeed : pl.level
        case "jog":
            pl.jogHeld = true
            pl.pressed.insert("jog")
            jogTimer = Timer.scheduledTimer(withTimeInterval: 0.05, repeats: true) { [weak self] _ in self?.jogStep() }
            RunLoop.main.add(jogTimer!, forMode: .eventTracking)
        case "disc":
            a.prevAngle = atan2(d.y - Face.discC.y, d.x - Face.discC.x)
            a.wasPlaying = pl.engine.state == .playing
            a.scrub = pl.engine.position
        case "main_display":
            break
        default:
            pl.pressed.insert(rid)
            let longIds: Set<String> = ["power", "key_C", "key_T", "cue1", "cue2", "cue3"]
            if !right && longIds.contains(rid) && !(rid.hasPrefix("cue") && a.shift) {
                longTimer = Timer.scheduledTimer(withTimeInterval: 0.65, repeats: false) { [weak self] _ in self?.longPress() }
                RunLoop.main.add(longTimer!, forMode: .eventTracking)
            }
        }
        act = a
        needsDisplay = true
    }

    private func longPress() {
        guard var a = act else { return }
        a.longDone = true
        act = a
        switch a.id {
        case "power": player.quitApp?()
        case "key_C": player.keypadLong("C")
        case "key_T": player.keypadLong("T")
        case "cue1", "cue2", "cue3": player.cueSet(Int(String(a.id.last!))! - 1)
        default: break
        }
    }

    private func update(_ event: NSEvent) {
        guard var a = act else { return }
        let pl = player
        let p = convert(event.locationInWindow, from: nil)
        let s = fit.s
        let ox = p.x - a.start.x, oy = p.y - a.start.y
        a.moved = max(a.moved, hypot(ox, oy) / s)
        switch a.id {
        case "varispeed", "level":
            let k: CGFloat = event.modifierFlags.contains(.shift) ? 0.2 : 1
            let delta = (-oy + ox * 0.5) / s
            if a.id == "varispeed" {
                pl.setVarispeed(a.startValue + Int((delta * k * 100 / 180).rounded()))
            } else {
                pl.setLevel(a.startValue + Int((delta * k * 100 / 220).rounded()))
            }
        case "jog":
            pl.jog = max(-1, min(1, ox / s / (Face.jogTravel * 1.6)))
        case "disc":
            let d = toDev(p)
            let ang = atan2(d.y - Face.discC.y, d.x - Face.discC.x)
            var da = ang - a.prevAngle
            da = (da + .pi).truncatingRemainder(dividingBy: 2 * .pi)
            if da < 0 { da += 2 * .pi }
            da -= .pi
            a.prevAngle = ang
            if a.moved > 4 && !pl.scrubbing {
                pl.scrubbing = true
                if a.wasPlaying { pl.pause() }
            }
            if pl.scrubbing {
                pl.discAngle += da
                a.scrub = max(0, a.scrub + Double(da / (2 * .pi)) * 1.8)
                let now = Player.now()
                if now - a.lastSeek > 0.06 {
                    a.lastSeek = now
                    pl.seek(to: a.scrub)
                }
                needsDisplay = true
            }
        default:
            break
        }
        act = a
    }

    private func end(_ event: NSEvent) {
        guard let a = act else { return }
        act = nil
        longTimer?.invalidate(); longTimer = nil
        let pl = player
        pl.pressed.remove(a.id)
        let inside = Face.hit(toDev(convert(event.locationInWindow, from: nil))) == a.id
        switch a.id {
        case "jog":
            pl.jogHeld = false
            pl.pressed.remove("jog")
            jogTimer?.invalidate(); jogTimer = nil
        case "disc":
            if pl.scrubbing {
                pl.seek(to: a.scrub)
                pl.scrubbing = false
                if a.wasPlaying { pl.play() }
            } else if a.moved < 4 {
                pl.playPause()
            }
        case "varispeed", "level":
            break
        case "main_display":
            if inside { pl.toggleTimeMode() }
        default:
            if inside && !a.longDone { activate(a.id, right: a.right, shift: a.shift) }
        }
        needsDisplay = true
    }

    private func activate(_ id: String, right: Bool, shift: Bool) {
        let pl = player
        if id == "power" { pl.togglePower(); return }
        guard pl.powerOn else { return }
        switch id {
        case _ where id.hasPrefix("key_"): pl.keypad(String(id.dropFirst(4)))
        case "enter": pl.enter()
        case "cue1", "cue2", "cue3":
            let i = Int(String(id.last!))! - 1
            if right || shift { pl.cueClear(i) } else { pl.cuePress(i) }
        case "play": pl.playPause()
        case "stop": pl.stop()
        case "prev": pl.prevTrack()
        case "next": pl.nextTrack()
        case "data": pl.openFolderDialog?()
        case "usb": pl.openFilesDialog?()
        case "cd": pl.openCD()
        case "output":
            if let u = URL(string: "x-apple.systempreferences:com.apple.Sound-Settings.extension") {
                NSWorkspace.shared.open(u)
            }
        case "sync": pl.showHelp?()
        case "keylock": pl.toggleKeyLock()
        case "repeat": pl.cycleRepeat()
        case "shuffle": pl.setShuffle(!pl.shuffle)
        case "eject": pl.eject()
        default: break
        }
    }

    private func jogStep() {
        let j = player.jog
        if abs(j) > 0.08 && player.hasTracks {
            let speed = Double(j * abs(j)) * 16
            player.seekRelative(speed * 0.05)
        }
    }

    // ------------------------------------------------------------ Mausrad
    override func scrollWheel(with event: NSEvent) {
        let pl = player
        guard pl.powerOn else { return }
        let id = Face.hit(toDev(convert(event.locationInWindow, from: nil)))
        var step = abs(event.scrollingDeltaY) >= abs(event.scrollingDeltaX) ? event.scrollingDeltaY : -event.scrollingDeltaX
        if event.hasPreciseScrollingDeltas { step /= 10 }
        if step == 0 { return }
        let unit = Int(step.rounded()) != 0 ? Int(step.rounded()) : (step > 0 ? 1 : -1)
        switch id {
        case "varispeed"?: pl.setVarispeed(pl.varispeed + unit)
        case "disc"?, "jog"?:
            if pl.hasTracks {
                pl.discAngle += step * 0.15
                pl.seekRelative(Double(step) * 2)
            }
        default: pl.setLevel(pl.level + unit * 2)
        }
    }

    // ------------------------------------------------------------ Tastatur
    private func flashKey(_ id: String) {
        player.pressed.insert(id)
        needsDisplay = true
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.12) { [weak self] in
            self?.player.pressed.remove(id)
            self?.needsDisplay = true
        }
    }

    override func keyDown(with event: NSEvent) {
        let pl = player
        let shift = event.modifierFlags.contains(.shift)
        if event.modifierFlags.contains(.command) { super.keyDown(with: event); return }
        let chars = event.charactersIgnoringModifiers ?? ""
        if !pl.powerOn && chars.lowercased() != "p" { return }
        switch event.keyCode {
        case 49: flashKey("play"); pl.playPause(); return              // Leertaste
        case 36, 76: flashKey("enter"); pl.enter(); return               // Return / Enter
        case 53: flashKey("stop"); pl.stop(); return                     // Esc
        case 123: pl.seekRelative(shift ? -30 : -5); return             // ←
        case 124: pl.seekRelative(shift ? 30 : 5); return               // →
        case 126: pl.setLevel(pl.level + 2); return                      // ↑
        case 125: pl.setLevel(pl.level - 2); return                      // ↓
        case 121: flashKey("next"); pl.nextTrack(); return               // Bild ↓
        case 116: flashKey("prev"); pl.prevTrack(); return               // Bild ↑
        case 51, 117: flashKey("key_C"); pl.clearEntry(); return         // Löschen
        default: break
        }
        guard let ch = chars.first else { return }
        switch ch {
        case "0"..."9": flashKey("key_\(ch)"); pl.keypad(String(ch))
        case "+", "]": pl.setVarispeed(pl.varispeed + 1)
        case "-", "[": pl.setVarispeed(pl.varispeed - 1)
        case "#", "\\": pl.setVarispeed(100)
        case "t", "T": flashKey("key_T"); pl.toggleTimeMode()
        case "c", "C": flashKey("key_C"); pl.clearEntry()
        case "m", "M": flashKey("keylock"); pl.toggleKeyLock()
        case "r", "R": flashKey("repeat"); pl.cycleRepeat()
        case "s", "S": flashKey("shuffle"); pl.setShuffle(!pl.shuffle)
        case "q", "Q", "w", "W", "e", "E":
            let i = ["q": 0, "w": 1, "e": 2][String(ch).lowercased()]!
            flashKey("cue\(i + 1)")
            if shift { pl.cueSet(i) } else { pl.cuePress(i) }
        case "n", "N": flashKey("next"); pl.nextTrack()
        case "b", "B": flashKey("prev"); pl.prevTrack()
        case "o", "O": pl.openFolderDialog?()
        case "d", "D": pl.openCD()
        case "j", "J": pl.eject()
        case "p", "P": flashKey("power"); pl.togglePower()
        case "h", "H", "?": pl.showHelp?()
        case ".": flashKey("stop"); pl.stop()
        default: super.keyDown(with: event)
        }
    }

    // ------------------------------------------------------------ Drag & Drop
    override func draggingEntered(_ sender: NSDraggingInfo) -> NSDragOperation { .copy }

    override func performDragOperation(_ sender: NSDraggingInfo) -> Bool {
        let urls = sender.draggingPasteboard.readObjects(forClasses: [NSURL.self],
                                                         options: [.urlReadingFileURLsOnly: true]) as? [URL] ?? []
        guard !urls.isEmpty else { return false }
        player.open(urls)
        return true
    }
}
