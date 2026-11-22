// thisismade cdp-2 für macOS – Programmstart, Fenster und Menüs.
import AppKit
import UniformTypeIdentifiers

let appName = "thisismade cdp-2"
let appVersion = "1.0.0"

final class AppDelegate: NSObject, NSApplicationDelegate, NSWindowDelegate {
    let player = Player()
    var window: NSWindow!
    var view: PlayerView!
    var helpWindow: NSWindow?
    private var pendingOpen: [URL] = []
    private var launched = false

    func applicationDidFinishLaunching(_ note: Notification) {
        buildMenu()
        view = PlayerView(player: player)
        player.showHelp = { [weak self] in self?.showHelp() }
        player.openFolderDialog = { [weak self] in self?.openFolder() }
        player.openFilesDialog = { [weak self] in self?.openFiles() }
        player.quitApp = {
            NSApp.terminate(nil)
        }

        let w = NSWindow(contentRect: NSRect(x: 0, y: 0, width: Face.canvasW * 0.62, height: Face.canvasH * 0.62),
                         styleMask: [.titled, .closable, .miniaturizable, .resizable, .fullSizeContentView],
                         backing: .buffered, defer: false)
        w.title = appName
        w.titleVisibility = .hidden
        w.titlebarAppearsTransparent = true
        w.isOpaque = false
        w.backgroundColor = .clear
        w.hasShadow = false
        w.isMovableByWindowBackground = false
        w.contentAspectRatio = NSSize(width: Face.canvasW, height: Face.canvasH)
        w.minSize = NSSize(width: Face.canvasW * 0.35, height: Face.canvasH * 0.35)
        for b: NSWindow.ButtonType in [.closeButton, .miniaturizeButton, .zoomButton] {
            w.standardWindowButton(b)?.isHidden = true
        }
        w.contentView = view
        w.delegate = self
        w.center()
        w.setFrameAutosaveName("MainWindow")
        w.makeKeyAndOrderFront(nil)
        w.makeFirstResponder(view)
        window = w
        NSApp.activate(ignoringOtherApps: true)

        launched = true
        if pendingOpen.isEmpty {
            player.restoreSession()
        } else {
            player.open(pendingOpen)
            pendingOpen = []
        }
    }

    func application(_ application: NSApplication, open urls: [URL]) {
        if launched { player.open(urls) } else { pendingOpen += urls }
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool { true }

    func applicationWillTerminate(_ note: Notification) {
        player.saveSettings()
        player.engine.stop()
    }

    // ------------------------------------------------------------ Dialoge
    @objc func openFolder() {
        let p = NSOpenPanel()
        p.title = "Ordner laden"
        p.canChooseDirectories = true
        p.canChooseFiles = false
        p.allowsMultipleSelection = true
        p.directoryURL = FileManager.default.urls(for: .musicDirectory, in: .userDomainMask).first
        p.beginSheetModal(for: window) { [weak self] r in
            if r == .OK { self?.player.open(p.urls) }
        }
    }

    @objc func openFiles() {
        let p = NSOpenPanel()
        p.title = "Dateien laden"
        p.canChooseDirectories = false
        p.canChooseFiles = true
        p.allowsMultipleSelection = true
        var types: [UTType] = [.audio]
        if let m3u = UTType(filenameExtension: "m3u") { types.append(m3u) }
        if let m3u8 = UTType(filenameExtension: "m3u8") { types.append(m3u8) }
        p.allowedContentTypes = types
        p.beginSheetModal(for: window) { [weak self] r in
            if r == .OK { self?.player.open(p.urls) }
        }
    }

    @objc func openCD() { player.openCD() }
    @objc func eject() { player.eject() }
    @objc func playPause() { player.playPause() }
    @objc func stopPlayback() { player.stop() }
    @objc func nextTrack() { player.nextTrack() }
    @objc func prevTrack() { player.prevTrack(force: true) }
    @objc func toggleRepeat() { player.cycleRepeat() }
    @objc func toggleShuffle() { player.setShuffle(!player.shuffle) }
    @objc func toggleKeyLock() { player.toggleKeyLock() }

    @objc func zoomIn() { zoom(1.1) }
    @objc func zoomOut() { zoom(1 / 1.1) }
    @objc func zoomReset() {
        let screenH = window.screen?.visibleFrame.height ?? 900
        let h = min(screenH * 0.8, Face.canvasH)
        setSize(h / Face.canvasH)
    }

    private func zoom(_ f: CGFloat) { setSize(window.frame.width / Face.canvasW * f) }

    private func setSize(_ z: CGFloat) {
        let z2 = max(0.3, min(2.0, z))
        var fr = window.frame
        let nw = Face.canvasW * z2, nh = Face.canvasH * z2
        fr.origin.y += fr.height - nh
        fr.size = NSSize(width: nw, height: nh)
        window.setFrame(fr, display: true, animate: true)
    }

    @objc func showAbout() {
        NSApp.orderFrontStandardAboutPanel(options: [
            .applicationName: appName,
            .applicationVersion: appVersion,
            .credits: NSAttributedString(string: "CD-Player-Software mit Tempo, Key Lock, Memory-Cues und Shuttle.\nhttps://github.com/zc7ryr6ms4-eng/thisismade-CDP-2"),
        ])
    }

    @objc func showHelp() {
        if let w = helpWindow { w.makeKeyAndOrderFront(nil); return }
        let w = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 600, height: 640),
                         styleMask: [.titled, .closable, .resizable], backing: .buffered, defer: false)
        w.title = appName + " – Bedienung"
        w.isReleasedWhenClosed = false
        let scroll = NSScrollView(frame: w.contentView!.bounds)
        scroll.autoresizingMask = [.width, .height]
        scroll.hasVerticalScroller = true
        let tv = NSTextView(frame: scroll.bounds)
        tv.autoresizingMask = [.width]
        tv.isEditable = false
        tv.textContainerInset = NSSize(width: 18, height: 18)
        tv.font = NSFont.systemFont(ofSize: 13)
        tv.string = helpText
        scroll.documentView = tv
        w.contentView = scroll
        w.center()
        w.makeKeyAndOrderFront(nil)
        helpWindow = w
    }

    // ------------------------------------------------------------ Menüs
    private func item(_ title: String, _ sel: Selector?, _ key: String = "", _ mods: NSEvent.ModifierFlags = [.command]) -> NSMenuItem {
        let it = NSMenuItem(title: title, action: sel, keyEquivalent: key)
        it.keyEquivalentModifierMask = mods
        it.target = (sel != nil && responds(to: sel!)) ? self : nil
        return it
    }

    private func buildMenu() {
        let main = NSMenu()

        let appMenu = NSMenu(title: appName)
        appMenu.addItem(item("Über \(appName)", #selector(showAbout)))
        appMenu.addItem(.separator())
        let hide = NSMenuItem(title: "\(appName) ausblenden", action: #selector(NSApplication.hide(_:)), keyEquivalent: "h")
        appMenu.addItem(hide)
        let others = NSMenuItem(title: "Andere ausblenden", action: #selector(NSApplication.hideOtherApplications(_:)), keyEquivalent: "h")
        others.keyEquivalentModifierMask = [.command, .option]
        appMenu.addItem(others)
        appMenu.addItem(.separator())
        appMenu.addItem(NSMenuItem(title: "\(appName) beenden", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q"))
        let appItem = NSMenuItem()
        appItem.submenu = appMenu
        main.addItem(appItem)

        let file = NSMenu(title: "Ablage")
        file.addItem(item("Ordner laden …", #selector(openFolder), "o", [.command, .shift]))
        file.addItem(item("Dateien laden …", #selector(openFiles), "o"))
        file.addItem(item("Audio-CD lesen", #selector(openCD), "d", [.command, .shift]))
        file.addItem(item("Auswerfen", #selector(eject), "e"))
        file.addItem(.separator())
        file.addItem(NSMenuItem(title: "Fenster schließen", action: #selector(NSWindow.performClose(_:)), keyEquivalent: "w"))
        let fileItem = NSMenuItem(title: "Ablage", action: nil, keyEquivalent: "")
        fileItem.submenu = file
        main.addItem(fileItem)

        let play = NSMenu(title: "Wiedergabe")
        play.addItem(item("Play / Pause", #selector(playPause), "p"))
        play.addItem(item("Stopp", #selector(stopPlayback), "."))
        play.addItem(item("Nächster Titel", #selector(nextTrack), String(Character(UnicodeScalar(NSRightArrowFunctionKey)!))))
        play.addItem(item("Vorheriger Titel", #selector(prevTrack), String(Character(UnicodeScalar(NSLeftArrowFunctionKey)!))))
        play.addItem(.separator())
        play.addItem(item("Wiederholen umschalten", #selector(toggleRepeat), "r"))
        play.addItem(item("Zufall umschalten", #selector(toggleShuffle), "s", [.command, .option]))
        play.addItem(item("Key Lock umschalten", #selector(toggleKeyLock), "k"))
        let playItem = NSMenuItem(title: "Wiedergabe", action: nil, keyEquivalent: "")
        playItem.submenu = play
        main.addItem(playItem)

        let viewM = NSMenu(title: "Darstellung")
        viewM.addItem(item("Größer", #selector(zoomIn), "+"))
        viewM.addItem(item("Kleiner", #selector(zoomOut), "-"))
        viewM.addItem(item("Originalgröße", #selector(zoomReset), "0"))
        let viewItem = NSMenuItem(title: "Darstellung", action: nil, keyEquivalent: "")
        viewItem.submenu = viewM
        main.addItem(viewItem)

        let win = NSMenu(title: "Fenster")
        win.addItem(NSMenuItem(title: "Im Dock ablegen", action: #selector(NSWindow.performMiniaturize(_:)), keyEquivalent: "m"))
        let winItem = NSMenuItem(title: "Fenster", action: nil, keyEquivalent: "")
        winItem.submenu = win
        main.addItem(winItem)
        NSApp.windowsMenu = win

        let help = NSMenu(title: "Hilfe")
        help.addItem(item("\(appName) – Bedienung", #selector(showHelp), "?"))
        let helpItem = NSMenuItem(title: "Hilfe", action: nil, keyEquivalent: "")
        helpItem.submenu = help
        main.addItem(helpItem)
        NSApp.helpMenu = help

        NSApp.mainMenu = main
    }
}

let helpText = """
THISISMADE CD PLAYER – BEDIENUNG

LADEN
• OPEN: Ordner laden (Unterordner werden mitgelesen)
• FILES: einzelne Dateien oder Playlists (.m3u) laden
• CD: eingelegte Audio-CD abspielen
• Dateien oder Ordner auf den Player oder das Dock-Symbol ziehen
• EJECT: Disc auswerfen · Rechtsklick auf freie Fläche: Menü

LAUFWERK
• ▶❚❚ Play/Pause · ■ Stopp · ⏮ ⏭ Titel zurück/vor (⏮ nach 3 s: Titelanfang)
• Klick auf die Disc: Play/Pause · Disc mit der Maus drehen: scratchen/spulen
• Mausrad/Trackpad über der Disc: ±2 s

ZIFFERNBLOCK
• Titelnummer tippen, dann ENTER → springt zum Titel
• TIME: vergangene Zeit ↔ Restzeit · gedrückt halten: Key Lock
• CLR: Eingabe löschen; ohne Eingabe: Wiederholen umschalten · gedrückt halten: Zufall

MEMORY A · B · C
• Leere Taste: Merkpunkt setzen (LED leuchtet) · belegte Taste: dorthin springen
• Gedrückt halten: neu setzen · Rechtsklick oder ⇧-Klick: löschen
• Merkpunkte werden pro Titel gespeichert

SHUTTLE: Schieber ziehen = Rück-/Vorlauf bis 16-fach

TEMPO: Fader ziehen (hoch = schneller), ⇧ = fein, Doppelklick = 100 %, Bereich 50–150 %.
KEY LOCK aus = Tempo und Tonhöhe gemeinsam (Varispeed), an = nur Tempo (Time Stretch).

VOLUME: Drehregler ziehen oder Mausrad auf freier Fläche · REPEAT aus/alle/einer · SHUFFLE

DISPLAY: TRACK = Titel · TOTAL = Anzahl · TIME = Min:Sek. Rechts: REPEAT, SHUFFLE,
KEY LOCK, PAUSE, REMAIN. Klick aufs Display: Zeitmodus.

OBEN: OUTPUT = Ton-Einstellungen · HELP = diese Hilfe · POWER = Standby, halten = Beenden.
MEDIA-LED: verbunden mit Kontrollzentrum und Medientasten.

TASTATUR
Leertaste Play/Pause · Esc Stopp · N/B Titel · ←/→ ±5 s (⇧ ±30 s) · ↑/↓ Lautstärke
0–9 + Return Titelwahl · +/- Tempo ±1 · # Tempo 100 · M Key Lock
Q W E Memory A–C (⇧ = setzen) · T Zeitmodus · R Wiederholen · S Zufall
O Ordner · ⌘O Dateien · D Audio-CD · J Auswerfen · P Power · H Hilfe
⌘+ / ⌘- / ⌘0 Größe · ⌘Q Beenden
Fenster verschieben: freie Fläche ziehen · Größe: Fensterrand ziehen

Formate: MP3, AAC/M4A, ALAC, FLAC, WAV, AIFF, CAF u. a. (alles, was macOS abspielt).
"""

let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.setActivationPolicy(.regular)
app.run()
