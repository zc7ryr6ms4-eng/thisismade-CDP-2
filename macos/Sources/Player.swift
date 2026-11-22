// Bedienlogik des thisismade cdp-2 (entspricht tmplayer/app.py der Linux-Version).
import AppKit
import AVFoundation
import MediaPlayer

struct Track {
    let url: URL
    var title: String
    var artist: String?
    var album: String?
}

final class Player {
    static let vsMin = 50, vsMax = 150
    static let audioExt: Set<String> = ["mp3", "m4a", "m4b", "mp4", "aac", "wav", "wave", "aif", "aiff",
                                         "aifc", "caf", "flac", "alac", "ac3", "ec3", "mp2", "amr"]
    static let discColors = [RGB(0.93, 0.91, 0.86), RGB(0.96, 0.96, 0.95), RGB(0.13, 0.13, 0.14),
                             RGB(1.0, 0.60, 0.14), RGB(0.20, 0.42, 0.40), RGB(0.78, 0.80, 0.83)]

    let engine = AudioEngine()
    var onChange: (() -> Void)?
    var showHelp: (() -> Void)?
    var openFolderDialog: (() -> Void)?
    var openFilesDialog: (() -> Void)?
    var quitApp: (() -> Void)?

    private(set) var tracks: [Track] = []
    private var order: [Int] = []
    private var opos = 0
    private(set) var index = -1
    private var cues: [String: [Double]] = [:]   // -1 = leer
    private(set) var repeatMode = 0             // 0 aus, 1 alle, 2 einer
    private(set) var shuffle = false
    private(set) var timeMode = 0
    private(set) var varispeed = 100
    private(set) var level = 80
    private var entry = ""
    private var entryTime: TimeInterval = 0
    private var msg = ""
    private var msgUntil: TimeInterval = 0
    private(set) var powerOn = true
    var pressed: Set<String> = []
    var jog: CGFloat = 0
    var jogHeld = false
    var discAngle: CGFloat = 0
    var scrubbing = false
    private var vu: [CGFloat] = [0, 0], vuTarget: [CGFloat] = [0, 0]
    private var peaks: [CGFloat] = [0, 0], peakT: [TimeInterval] = [0, 0]
    private var cover: CGImage?
    private var coverImage: NSImage?
    private var discLines: [String] = []
    private var discColor = Player.discColors[0]
    private var mediaReady = false
    private var activity: NSObjectProtocol?
    private var errors = 0
    private var metaToken = 0

    private let defaults = UserDefaults.standard

    init() {
        engine.onState = { [weak self] in self?.stateChanged() }
        engine.onEOS = { [weak self] in self?.eos() }
        engine.onLevel = { [weak self] l, r in self?.vuTarget = [CGFloat(l), CGFloat(r)] }
        engine.onError = { [weak self] m in self?.playError(m) }
        loadSettings()
        engine.volume = pow(Float(level) / 100, 3)
        engine.setRate(Float(varispeed) / 100)
        setupRemoteCommands()
    }

    static func now() -> TimeInterval { ProcessInfo.processInfo.systemUptime }

    // ------------------------------------------------------------ Einstellungen
    private func loadSettings() {
        if defaults.object(forKey: "level") != nil { level = defaults.integer(forKey: "level") }
        if defaults.object(forKey: "varispeed") != nil { varispeed = defaults.integer(forKey: "varispeed") }
        repeatMode = defaults.integer(forKey: "repeat")
        shuffle = defaults.bool(forKey: "shuffle")
        timeMode = defaults.integer(forKey: "timeMode")
        engine.setKeyLock(defaults.bool(forKey: "keyLock"))
        cues = (defaults.dictionary(forKey: "cues") as? [String: [Double]]) ?? [:]
    }

    func saveSettings() {
        defaults.set(level, forKey: "level")
        defaults.set(varispeed, forKey: "varispeed")
        defaults.set(repeatMode, forKey: "repeat")
        defaults.set(shuffle, forKey: "shuffle")
        defaults.set(timeMode, forKey: "timeMode")
        defaults.set(engine.keyLock, forKey: "keyLock")
        defaults.set(cues.filter { $0.value.contains { $0 >= 0 } }, forKey: "cues")
        defaults.set(tracks.prefix(5000).map { $0.url.path }, forKey: "paths")
        defaults.set(index, forKey: "index")
        defaults.set(engine.position, forKey: "position")
    }

    func restoreSession() {
        let paths = (defaults.stringArray(forKey: "paths") ?? []).filter { FileManager.default.fileExists(atPath: $0) }
        guard !paths.isEmpty else { return }
        setTracks(paths.map { makeTrack(URL(fileURLWithPath: $0)) }, autoplay: false)
        let idx = defaults.integer(forKey: "index")
        if idx >= 0 && idx < tracks.count {
            playIndex(idx, play: false, start: defaults.double(forKey: "position"))
        }
    }

    // ------------------------------------------------------------ Laden
    private func makeTrack(_ url: URL) -> Track {
        Track(url: url, title: url.deletingPathExtension().lastPathComponent)
    }

    private func scan(_ url: URL, into out: inout [URL]) {
        var isDir: ObjCBool = false
        guard FileManager.default.fileExists(atPath: url.path, isDirectory: &isDir) else { return }
        if isDir.boolValue {
            let items = (try? FileManager.default.contentsOfDirectory(at: url, includingPropertiesForKeys: [.isDirectoryKey],
                                                                      options: [.skipsHiddenFiles])) ?? []
            let sorted = items.sorted { $0.lastPathComponent.localizedStandardCompare($1.lastPathComponent) == .orderedAscending }
            var dirs: [URL] = []
            for u in sorted {
                if (try? u.resourceValues(forKeys: [.isDirectoryKey]).isDirectory) == true {
                    dirs.append(u)
                } else if Player.audioExt.contains(u.pathExtension.lowercased()) {
                    out.append(u)
                }
            }
            for d in dirs { scan(d, into: &out) }
        } else {
            let ext = url.pathExtension.lowercased()
            if Player.audioExt.contains(ext) {
                out.append(url)
            } else if ext == "m3u" || ext == "m3u8" {
                guard let text = try? String(contentsOf: url, encoding: .utf8) else { return }
                let base = url.deletingLastPathComponent()
                for raw in text.components(separatedBy: .newlines) {
                    let ln = raw.trimmingCharacters(in: .whitespaces)
                    if ln.isEmpty || ln.hasPrefix("#") { continue }
                    let u: URL
                    if ln.hasPrefix("file://"), let fu = URL(string: ln) { u = fu }
                    else if ln.hasPrefix("/") { u = URL(fileURLWithPath: ln) }
                    else { u = base.appendingPathComponent(ln) }
                    if FileManager.default.fileExists(atPath: u.path) { out.append(u) }
                }
            }
        }
    }

    func open(_ urls: [URL]) {
        var found: [URL] = []
        for u in urls { scan(u, into: &found) }
        if found.isEmpty {
            flash("no AUdio")
            return
        }
        setTracks(found.map(makeTrack), autoplay: true)
    }

    private func setTracks(_ t: [Track], autoplay: Bool) {
        engine.stop()
        tracks = t
        entry = ""
        makeOrder(keep: nil)
        flash(String(format: "LoAd %3d", t.count), 1.0)
        if autoplay, let first = order.first { playIndex(first, play: true) }
        updateNowPlaying()
    }

    func eject() {
        engine.unload()
        tracks = []; order = []; index = -1
        cover = nil; coverImage = nil; discLines = []
        flash("EJECt")
        updateNowPlaying()
    }

    /// Audio-CDs erscheinen unter macOS als Laufwerk mit AIFF-Dateien in /Volumes.
    func openCD() {
        let vols = FileManager.default.mountedVolumeURLs(includingResourceValuesForKeys: nil, options: [.skipHiddenVolumes]) ?? []
        for v in vols {
            let items = (try? FileManager.default.contentsOfDirectory(atPath: v.path)) ?? []
            let aiffs = items.filter { $0.lowercased().hasSuffix(".aiff") }
            if !aiffs.isEmpty && aiffs.count == items.filter({ !$0.hasPrefix(".") }).count {
                open([v])
                flash(String(format: "cd   %3d tr", tracks.count), 1.5)
                return
            }
        }
        flash("no  cd", 1.5)
    }

    private func makeOrder(keep: Int?) {
        order = Array(0..<tracks.count)
        if shuffle && tracks.count > 1 {
            order.shuffle()
            if let k = keep, let i = order.firstIndex(of: k) {
                order.remove(at: i)
                order.insert(k, at: 0)
            }
        }
        if let k = keep, let i = order.firstIndex(of: k) { opos = i } else { opos = 0 }
    }

    var hasTracks: Bool { !tracks.isEmpty && index >= 0 }

    // ------------------------------------------------------------ Laufwerk
    func playIndex(_ i: Int, play: Bool = true, start: Double = 0) {
        guard i >= 0 && i < tracks.count else { return }
        index = i
        if let p = order.firstIndex(of: i) { opos = p }
        engine.load(tracks[i].url, play: play, start: start)
        updateDisc()
        loadMetadata(for: i)
        updateNowPlaying()
    }

    private func nextInOrder(wrap: Bool) -> Int? {
        guard !order.isEmpty else { return nil }
        var p = opos + 1
        if p >= order.count {
            guard wrap else { return nil }
            p = 0
        }
        return order[p]
    }

    private func prevInOrder() -> Int? {
        guard !order.isEmpty else { return nil }
        var p = opos - 1
        if p < 0 { p = order.count - 1 }
        return order[p]
    }

    func play() {
        guard powerOn else { return }
        if !hasTracks {
            if let f = order.first { playIndex(f) } else { flash("no  dISC") }
            return
        }
        engine.play()
    }

    func pause() { engine.pause() }
    func playPause() { engine.state == .playing ? pause() : play() }
    func stop() { engine.stop(); changed() }

    func nextTrack() {
        guard !tracks.isEmpty, let n = nextInOrder(wrap: true) else { return }
        playIndex(n)
    }

    func prevTrack(force: Bool = false) {
        guard !tracks.isEmpty else { return }
        if !force && engine.position > 3 {
            seek(to: 0)
            return
        }
        if let p = prevInOrder() { playIndex(p) }
    }

    func seek(to s: Double) { engine.seek(s); updateNowPlaying() }
    func seekRelative(_ d: Double) { engine.seek(engine.position + d) }

    func jumpTo(_ n: Int) {
        if n >= 1 && n <= tracks.count { playIndex(n - 1) } else { flash(String(format: "Err  %3d", n)) }
    }

    // ------------------------------------------------------------ Modi
    func setRepeat(_ r: Int) {
        repeatMode = ((r % 3) + 3) % 3
        flash(["rEP  oFF", "rEP  ALL", "rEP  onE"][repeatMode])
    }

    func cycleRepeat() { setRepeat(repeatMode + 1) }

    func setShuffle(_ on: Bool) {
        shuffle = on
        makeOrder(keep: index >= 0 ? index : nil)
        flash(on ? "SHUF  on" : "SHUF  oFF")
        MPRemoteCommandCenter.shared().changeShuffleModeCommand.currentShuffleType = on ? .items : .off
    }

    func toggleTimeMode() {
        timeMode = 1 - timeMode
        flash(timeMode == 0 ? "ELAPSEd" : "rEnAIn", 0.8)
    }

    func toggleKeyLock() {
        engine.setKeyLock(!engine.keyLock)
        flash(engine.keyLock ? "LoCK  on" : "LoCK  oFF", 1.0)
    }

    func setVarispeed(_ v: Int) {
        let nv = max(Player.vsMin, min(Player.vsMax, v))
        guard nv != varispeed else { return }
        varispeed = nv
        engine.setRate(Float(nv) / 100)   // AVAudioEngine ändert das Tempo ohne Aussetzer
        updateNowPlaying()
        changed()
    }

    func setLevel(_ v: Int) {
        let nv = max(0, min(100, v))
        guard nv != level else { return }
        level = nv
        engine.volume = pow(Float(nv) / 100, 3)
        changed()
    }

    func togglePower() {
        powerOn.toggle()
        if !powerOn { engine.pause() } else { flash("HELLo", 0.6) }
        changed()
    }

    // ------------------------------------------------------------ Memory (Cue)
    private func cueList() -> [Double] {
        guard hasTracks else { return [-1, -1, -1] }
        return cues[tracks[index].url.path] ?? [-1, -1, -1]
    }

    private func setCue(_ i: Int, _ v: Double) {
        guard hasTracks else { return }
        var l = cueList()
        l[i] = v
        cues[tracks[index].url.path] = l
    }

    func cuePress(_ i: Int) {
        guard hasTracks else { flash("no  dISC"); return }
        let c = cueList()[i]
        if c < 0 {
            cueSet(i)
        } else {
            seek(to: c)
            if engine.state != .playing { play() }
            flash("CUE \(i + 1)", 0.6)
        }
    }

    func cueSet(_ i: Int) {
        guard hasTracks else { return }
        setCue(i, engine.position)
        flash("CUE \(i + 1)  SEt", 0.8)
    }

    func cueClear(_ i: Int) {
        guard hasTracks else { return }
        setCue(i, -1)
        flash("CUE \(i + 1)  CLr", 0.8)
    }

    // ------------------------------------------------------------ Ziffernblock
    func keypad(_ k: String) {
        let now = Player.now()
        if let _ = Int(k) {
            if now - entryTime > 4 { entry = "" }
            entry = String((entry + k).suffix(3))
            entryTime = now
        } else if k == "T" {
            toggleTimeMode()
        } else if k == "C" {
            if !entry.isEmpty { entry = "" } else { cycleRepeat() }
        }
        changed()
    }

    func keypadLong(_ k: String) {
        if k == "C" { setShuffle(!shuffle) } else if k == "T" { toggleKeyLock() }
    }

    func enter() {
        if !entry.isEmpty && Player.now() - entryTime < 4, let n = Int(entry) {
            entry = ""
            jumpTo(n)
        } else {
            entry = ""
            playPause()
        }
        changed()
    }

    func clearEntry() { entry = ""; changed() }

    // ------------------------------------------------------------ Engine-Ereignisse
    private func stateChanged() {
        let playing = engine.state == .playing
        if playing && activity == nil {
            activity = ProcessInfo.processInfo.beginActivity(options: [.idleSystemSleepDisabled, .userInitiated],
                                                             reason: "Musikwiedergabe")
        } else if !playing, let a = activity {
            ProcessInfo.processInfo.endActivity(a)
            activity = nil
        }
        if playing { errors = 0 }
        updateNowPlaying()
        changed()
    }

    private func eos() {
        if repeatMode == 2 {
            engine.seek(0)
            return
        }
        if let n = nextInOrder(wrap: repeatMode == 1) {
            playIndex(n)
        } else {
            engine.stop()
            if let f = order.first {
                playIndex(f, play: false)
                engine.stop()
            }
            flash("End", 1.2)
        }
    }

    private func playError(_ m: String) {
        NSLog("Wiedergabefehler: %@", m)
        flash("Err", 1.2)
        errors += 1
        if errors < tracks.count, let n = nextInOrder(wrap: repeatMode == 1) {
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.4) { [weak self] in self?.playIndex(n) }
        }
    }

    // ------------------------------------------------------------ Metadaten & Disc-Aufdruck
    private func loadMetadata(for i: Int) {
        metaToken += 1
        let token = metaToken
        let url = tracks[i].url
        Task { [weak self] in
            let asset = AVURLAsset(url: url)
            var title: String?, artist: String?, album: String?, art: Data?
            if let items = try? await asset.load(.commonMetadata) {
                for item in items {
                    switch item.commonKey {
                    case .commonKeyTitle?: title = try? await item.load(.stringValue)
                    case .commonKeyArtist?: artist = try? await item.load(.stringValue)
                    case .commonKeyAlbumName?: album = try? await item.load(.stringValue)
                    case .commonKeyArtwork?: art = try? await item.load(.dataValue)
                    default: break
                    }
                }
            }
            await MainActor.run {
                guard let self = self, token == self.metaToken, i < self.tracks.count else { return }
                if let t = title, !t.isEmpty { self.tracks[i].title = t }
                self.tracks[i].artist = artist
                self.tracks[i].album = album
                self.setCover(art ?? self.folderCover(url))
                self.updateDisc()
                self.updateNowPlaying()
            }
        }
    }

    private func folderCover(_ url: URL) -> Data? {
        let dir = url.deletingLastPathComponent()
        let names = ["cover", "folder", "front", "album", "albumart", "artwork"]
        let items = (try? FileManager.default.contentsOfDirectory(atPath: dir.path)) ?? []
        for it in items.sorted() {
            let base = (it as NSString).deletingPathExtension.lowercased()
            let ext = (it as NSString).pathExtension.lowercased()
            if names.contains(base) && ["jpg", "jpeg", "png", "webp", "heic"].contains(ext) {
                return try? Data(contentsOf: dir.appendingPathComponent(it))
            }
        }
        return nil
    }

    private func setCover(_ data: Data?) {
        guard let d = data, let img = NSImage(data: d),
              let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
            cover = nil; coverImage = nil
            return
        }
        let s = min(cg.width, cg.height)
        let crop = cg.cropping(to: CGRect(x: (cg.width - s) / 2, y: (cg.height - s) / 2, width: s, height: s))
        cover = crop ?? cg
        coverImage = img
    }

    private func updateDisc() {
        guard hasTracks else { return }
        let t = tracks[index]
        var lines = [t.title]
        if let a = t.artist, !a.isEmpty { lines.append(a) }
        if let a = t.album, !a.isEmpty { lines.append(a) }
        lines.append(String(format: "TRACK %02d / %02d", index + 1, tracks.count))
        lines.append(t.url.pathExtension.uppercased())
        discLines = lines.map { String($0.uppercased().prefix(30)) }
        let key = t.album ?? t.url.deletingLastPathComponent().path
        var h: UInt64 = 1469598103934665603
        for b in key.utf8 { h = (h ^ UInt64(b)) &* 1099511628211 }
        discColor = Player.discColors[Int(h % UInt64(Player.discColors.count))]
        changed()
    }

    // ------------------------------------------------------------ Now Playing / Medientasten
    private func setupRemoteCommands() {
        let cc = MPRemoteCommandCenter.shared()
        cc.playCommand.addTarget { [weak self] _ in self?.play(); return .success }
        cc.pauseCommand.addTarget { [weak self] _ in self?.pause(); return .success }
        cc.togglePlayPauseCommand.addTarget { [weak self] _ in self?.playPause(); return .success }
        cc.stopCommand.addTarget { [weak self] _ in self?.stop(); return .success }
        cc.nextTrackCommand.addTarget { [weak self] _ in self?.nextTrack(); return .success }
        cc.previousTrackCommand.addTarget { [weak self] _ in self?.prevTrack(force: true); return .success }
        cc.changePlaybackPositionCommand.addTarget { [weak self] ev in
            guard let e = ev as? MPChangePlaybackPositionCommandEvent else { return .commandFailed }
            self?.seek(to: e.positionTime)
            return .success
        }
        cc.changeShuffleModeCommand.addTarget { [weak self] ev in
            guard let e = ev as? MPChangeShuffleModeCommandEvent else { return .commandFailed }
            self?.setShuffle(e.shuffleType != .off)
            return .success
        }
        cc.changeRepeatModeCommand.addTarget { [weak self] ev in
            guard let e = ev as? MPChangeRepeatModeCommandEvent else { return .commandFailed }
            switch e.repeatType {
            case .off: self?.setRepeat(0)
            case .one: self?.setRepeat(2)
            default: self?.setRepeat(1)
            }
            return .success
        }
        mediaReady = true
    }

    private func updateNowPlaying() {
        let center = MPNowPlayingInfoCenter.default()
        guard hasTracks else {
            center.nowPlayingInfo = nil
            center.playbackState = .stopped
            return
        }
        let t = tracks[index]
        var info: [String: Any] = [
            MPMediaItemPropertyTitle: t.title,
            MPMediaItemPropertyPlaybackDuration: engine.duration,
            MPNowPlayingInfoPropertyElapsedPlaybackTime: engine.position,
            MPNowPlayingInfoPropertyPlaybackRate: engine.state == .playing ? Double(varispeed) / 100 : 0.0,
            MPMediaItemPropertyAlbumTrackNumber: index + 1,
        ]
        if let a = t.artist { info[MPMediaItemPropertyArtist] = a }
        if let a = t.album { info[MPMediaItemPropertyAlbumTitle] = a }
        if let img = coverImage {
            info[MPMediaItemPropertyArtwork] = MPMediaItemArtwork(boundsSize: img.size) { _ in img }
        }
        center.nowPlayingInfo = info
        switch engine.state {
        case .playing: center.playbackState = .playing
        case .paused: center.playbackState = .paused
        case .stopped: center.playbackState = .stopped
        }
    }

    // ------------------------------------------------------------ Anzeige
    func flash(_ text: String, _ secs: TimeInterval = 1.0) {
        msg = text
        msgUntil = Player.now() + secs
        changed()
    }

    func changed() { onChange?() }

    private func displayText() -> (String, Bool) {
        let now = Player.now()
        let blink = Int(now * 2) % 2 == 0
        if !msg.isEmpty && now < msgUntil { return (msg, true) }
        if tracks.isEmpty { return ("------------", false) }
        var tr = String(format: "%03d", index >= 0 ? index + 1 : 0)
        if !entry.isEmpty && now - entryTime < 4 {
            tr = blink ? String(repeating: "-", count: 3 - entry.count) + entry : "   "
        }
        let idx = String(format: "%03d", min(999, tracks.count))
        let pos = engine.position, dur = engine.duration
        var tm: String, sec: String
        if timeMode == 1 && dur > 0 {
            let rem = Int((max(0, dur - pos)).rounded(.up))
            tm = String(format: "-%02d", min(99, rem / 60))
            sec = String(format: "%03d", rem % 60)
        } else {
            let p = Int(pos)
            tm = String(format: "%03d", min(999, p / 60))
            sec = String(format: "%03d", p % 60)
        }
        if engine.state == .paused && !blink { tm = "   "; sec = "   " }
        return (tr + idx + tm + sec, false)
    }

    func faceState() -> FaceState {
        var s = FaceState()
        let (txt, msgMode) = displayText()
        let c = cueList()
        s.pressed = pressed
        s.discLoaded = !tracks.isEmpty
        s.discAngle = discAngle
        s.discColor = discColor
        s.discLines = discLines
        s.cover = cover
        s.mediaLED = mediaReady
        s.powerOn = powerOn
        s.vu = vu
        s.peaks = peaks
        s.mainText = txt
        s.msgMode = msgMode
        s.vsText = String(format: "%03d", varispeed)
        s.lvText = String(format: "%03d", level)
        s.keyLock = engine.keyLock
        s.cueSet = c.map { $0 >= 0 }
        s.varispeedNorm = CGFloat(varispeed - Player.vsMin) / CGFloat(Player.vsMax - Player.vsMin)
        s.levelNorm = CGFloat(level) / 100
        s.jog = jog
        s.repeatMode = repeatMode
        s.shuffle = shuffle
        s.paused = engine.state == .paused
        s.remain = timeMode == 1
        return s
    }

    /// Pro Frame. true = neu zeichnen.
    func animate(_ dt: TimeInterval) -> Bool {
        var busy = false
        let now = Player.now()
        let playing = engine.state == .playing && powerOn
        if playing && !scrubbing {
            discAngle += CGFloat(dt) * 2 * .pi * 0.55 * CGFloat(varispeed) / 100
            busy = true
        }
        for i in 0..<2 {
            let tgt = playing ? vuTarget[i] : 0
            if tgt >= vu[i] { vu[i] = tgt } else { vu[i] = max(tgt, vu[i] - CGFloat(dt) * 1.6) }
            if vu[i] >= peaks[i] { peaks[i] = vu[i]; peakT[i] = now }
            else if now - peakT[i] > 0.8 { peaks[i] = max(0, peaks[i] - CGFloat(dt) * 0.7) }
            if vu[i] > 0.001 || peaks[i] > 0.001 { busy = true }
        }
        if !playing { vuTarget = [0, 0] }
        if !jogHeld && abs(jog) > 0.001 {
            jog *= max(0, 1 - CGFloat(dt) * 14)
            if abs(jog) < 0.01 { jog = 0 }
            busy = true
        }
        return busy
    }
}
