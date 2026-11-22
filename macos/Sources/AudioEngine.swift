// Wiedergabe mit AVAudioEngine.
// Varispeed: AVAudioUnitVarispeed (Tempo + Tonhöhe), Key Lock: AVAudioUnitTimePitch (nur Tempo).
import AVFoundation

final class AudioEngine {
    enum State { case stopped, playing, paused }

    private let engine = AVAudioEngine()
    private let player = AVAudioPlayerNode()
    private let vari = AVAudioUnitVarispeed()
    private let timePitch = AVAudioUnitTimePitch()
    private var format: AVAudioFormat?
    private var file: AVAudioFile?
    private var startFrame: AVAudioFramePosition = 0
    private var generation = 0

    private(set) var url: URL?
    private(set) var state: State = .stopped {
        didSet { if oldValue != state { onState?() } }
    }
    private(set) var rate: Float = 1
    private(set) var keyLock = false
    var volume: Float = 0.5 { didSet { player.volume = volume } }

    var onState: (() -> Void)?
    var onEOS: (() -> Void)?
    var onLevel: ((Float, Float) -> Void)?
    var onError: ((String) -> Void)?

    init() {
        engine.attach(player)
        engine.attach(vari)
        engine.attach(timePitch)
        engine.connect(player, to: vari, format: nil)
        engine.connect(vari, to: timePitch, format: nil)
        engine.connect(timePitch, to: engine.mainMixerNode, format: nil)
        engine.mainMixerNode.installTap(onBus: 0, bufferSize: 1024, format: nil) { [weak self] buf, _ in
            self?.measure(buf)
        }
        NotificationCenter.default.addObserver(forName: .AVAudioEngineConfigurationChange, object: engine,
                                               queue: .main) { [weak self] _ in self?.configChanged() }
    }

    // ------------------------------------------------------------ Laden & Steuerung
    @discardableResult
    func load(_ url: URL, play: Bool, start: Double = 0) -> Bool {
        generation += 1
        player.stop()
        let f: AVAudioFile
        do {
            f = try AVAudioFile(forReading: url)
        } catch {
            state = .stopped
            onError?("\(url.lastPathComponent): \(error.localizedDescription)")
            return false
        }
        file = f
        self.url = url
        let fmt = f.processingFormat
        if format == nil || format!.sampleRate != fmt.sampleRate || format!.channelCount != fmt.channelCount {
            engine.stop()
            engine.connect(player, to: vari, format: fmt)
            engine.connect(vari, to: timePitch, format: fmt)
            engine.connect(timePitch, to: engine.mainMixerNode, format: fmt)
            format = fmt
        }
        guard startEngine() else { return false }
        schedule(from: frame(for: start))
        if play {
            player.play()
            state = .playing
        } else {
            state = .paused
        }
        return true
    }

    private func startEngine() -> Bool {
        if engine.isRunning { return true }
        do {
            engine.prepare()
            try engine.start()
            return true
        } catch {
            state = .stopped
            onError?("Audioausgabe: \(error.localizedDescription)")
            return false
        }
    }

    private func frame(for seconds: Double) -> AVAudioFramePosition {
        guard let f = file else { return 0 }
        return AVAudioFramePosition(max(0, seconds) * f.processingFormat.sampleRate)
    }

    private func schedule(from frame: AVAudioFramePosition) {
        guard let f = file else { return }
        generation += 1
        let gen = generation
        player.stop()
        let fr = max(0, min(frame, f.length - 1))
        startFrame = fr
        let count = AVAudioFrameCount(max(0, f.length - fr))
        guard count > 0 else { return }
        player.scheduleSegment(f, startingFrame: fr, frameCount: count, at: nil,
                               completionCallbackType: .dataPlayedBack) { [weak self] _ in
            DispatchQueue.main.async {
                guard let self = self, self.generation == gen, self.state == .playing else { return }
                self.onEOS?()
            }
        }
    }

    func play() {
        guard url != nil else { return }
        switch state {
        case .playing: return
        case .stopped:
            guard startEngine() else { return }
            schedule(from: 0)
        case .paused:
            guard startEngine() else { return }
        }
        player.play()
        state = .playing
    }

    func pause() {
        guard state == .playing else { return }
        let pos = position
        player.pause()
        // Beim nächsten Play exakt hier weiter (playerTime ist nach pause unzuverlässig)
        schedule(from: frame(for: pos))
        state = .paused
    }

    func toggle() { state == .playing ? pause() : play() }

    func stop() {
        generation += 1
        player.stop()
        startFrame = 0
        state = .stopped
    }

    func unload() {
        stop()
        file = nil
        url = nil
    }

    var duration: Double {
        guard let f = file else { return 0 }
        return Double(f.length) / f.processingFormat.sampleRate
    }

    var position: Double {
        guard let f = file, state != .stopped else { return 0 }
        var frames = startFrame
        if state == .playing, let nt = player.lastRenderTime, let pt = player.playerTime(forNodeTime: nt) {
            frames += max(0, pt.sampleTime)
        }
        return Double(min(frames, f.length)) / f.processingFormat.sampleRate
    }

    func seek(_ seconds: Double) {
        guard file != nil else { return }
        let wasPlaying = state == .playing
        schedule(from: frame(for: min(seconds, max(0, duration - 0.05))))
        if wasPlaying {
            player.play()
        } else if state == .stopped {
            state = .paused
        }
    }

    // ------------------------------------------------------------ Tempo
    func setRate(_ r: Float) {
        rate = max(0.25, min(4, r))
        apply()
    }

    func setKeyLock(_ on: Bool) {
        keyLock = on
        apply()
    }

    private func apply() {
        if keyLock {
            vari.rate = 1
            timePitch.rate = rate
            timePitch.pitch = 0
        } else {
            timePitch.rate = 1
            timePitch.pitch = 0
            vari.rate = rate
        }
    }

    // ------------------------------------------------------------ Pegel
    private func measure(_ buf: AVAudioPCMBuffer) {
        guard let data = buf.floatChannelData else { return }
        let n = Int(buf.frameLength)
        let chans = Int(buf.format.channelCount)
        var peaks: [Float] = [0, 0]
        for ch in 0..<min(2, chans) {
            var p: Float = 0
            let ptr = data[ch]
            for i in 0..<n { p = max(p, abs(ptr[i])) }
            peaks[ch] = p
        }
        if chans == 1 { peaks[1] = peaks[0] }
        func norm(_ v: Float) -> Float {
            let db = 20 * log10(max(v, 1e-6))
            return max(0, min(1, (db + 48) / 48))
        }
        let l = norm(peaks[0]), r = norm(peaks[1])
        DispatchQueue.main.async { [weak self] in self?.onLevel?(l, r) }
    }

    // Ausgabegerät gewechselt (z. B. Kopfhörer, AirPods)
    private func configChanged() {
        guard file != nil, let u = url else { return }
        let pos = position
        let was = state
        format = nil
        load(u, play: was == .playing, start: pos)
        if was == .stopped { stop() }
    }
}
