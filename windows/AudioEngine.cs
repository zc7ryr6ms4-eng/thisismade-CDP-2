// Wiedergabe: Media Foundation (MP3, AAC/M4A, FLAC, WAV, WMA, ALAC …) bzw. Audio-CD,
// eigener Tempo-Prozessor (Varispeed oder Key Lock/WSOLA), Pegelmessung, WaveOut.
using NAudio.Wave;
using NAudio.Wave.SampleProviders;

namespace Thisismade;

public enum PlayState { Stopped, Playing, Paused }

public sealed class AudioEngine : ISampleProvider, IDisposable
{
    public const int Rate = 44100;
    public WaveFormat WaveFormat { get; } = WaveFormat.CreateIeeeFloatWaveFormat(Rate, 2);

    readonly object sync = new();
    readonly SynchronizationContext ui;
    WaveOutEvent output;
    Thread nullThread;
    volatile bool running = true;
    public bool HasAudioDevice { get; private set; } = true;
    WaveStream reader;
    ISampleProvider chain;
    readonly TempoProcessor tempo = new();
    double seekBase;              // Sekunden am Anfang des aktuellen Abschnitts
    bool sourceEnded;

    public string Source { get; private set; }
    public PlayState State { get; private set; } = PlayState.Stopped;
    public float Volume = 0.5f;
    public float PeakL, PeakR;    // 0…1 (linear)
    public bool KeyLock => tempo.KeyLock;
    public double Speed => tempo.Speed;

    public event Action StateChanged;
    public event Action Ended;
    public event Action<string> Error;

    public AudioEngine(bool silent = false)
    {
        ui = SynchronizationContext.Current ?? new SynchronizationContext();
        if (!silent)
        {
            try
            {
                output = new WaveOutEvent { DesiredLatency = 120, NumberOfBuffers = 3 };
                output.Init(this);
                output.Play();    // läuft dauerhaft; ohne Wiedergabe wird Stille geliefert
                return;
            }
            catch
            {
                output?.Dispose();
                output = null;
                HasAudioDevice = false;
            }
        }
        // Kein Ausgabegerät (oder Selbsttest): in Echtzeit "abspielen", ohne Ton
        nullThread = new Thread(() =>
        {
            var buf = new float[882 * 2];
            var sw = System.Diagnostics.Stopwatch.StartNew();
            long frames = 0;
            while (running)
            {
                Read(buf, 0, buf.Length);
                frames += 882;
                int wait = (int)(frames * 1000 / Rate - sw.ElapsedMilliseconds);
                if (wait > 0) Thread.Sleep(wait);
            }
        }) { IsBackground = true, Name = "NullAudio" };
        nullThread.Start();
    }

    // ------------------------------------------------------------ Laden & Steuerung
    public bool Load(string source, bool play, double start = 0)
    {
        WaveStream r;
        try
        {
            var ext = Path.GetExtension(source).ToLowerInvariant();
            r = source.StartsWith("cdda://") ? CdAudio.OpenTrack(source)
              : ext is ".wav" or ".wave" ? TryNative(() => new WaveFileReader(source), source)
              : ext is ".aif" or ".aiff" ? TryNative(() => new AiffFileReader(source), source)
              : new MediaFoundationReader(source);
        }
        catch (Exception ex)
        {
            SetState(PlayState.Stopped);
            Error?.Invoke($"{Path.GetFileName(source)}: {ex.Message}");
            return false;
        }
        lock (sync)
        {
            reader?.Dispose();
            reader = r;
            Source = source;
            SeekLocked(start);
        }
        SetState(play ? PlayState.Playing : PlayState.Paused);
        return true;
    }

    static WaveStream TryNative(Func<WaveStream> open, string source)
    {
        try { return open(); }
        catch { return new MediaFoundationReader(source); }   // z. B. komprimierte WAV-Varianten
    }

    ISampleProvider BuildChain(WaveStream r)
    {
        ISampleProvider s = r.ToSampleProvider();
        if (s.WaveFormat.Channels == 1) s = new MonoToStereoSampleProvider(s);
        else if (s.WaveFormat.Channels > 2) s = new FirstTwoChannels(s);
        if (s.WaveFormat.SampleRate != Rate) s = new WdlResamplingSampleProvider(s, Rate);
        return s;
    }

    void SeekLocked(double seconds)
    {
        if (reader == null) return;
        var total = reader.TotalTime.TotalSeconds;
        seconds = Math.Max(0, Math.Min(seconds, Math.Max(0, total - 0.05)));
        reader.CurrentTime = TimeSpan.FromSeconds(seconds);
        chain = BuildChain(reader);
        tempo.Reset(chain);
        seekBase = seconds;
        sourceEnded = false;
    }

    public void Play()
    {
        if (Source == null) return;
        if (State == PlayState.Stopped) lock (sync) SeekLocked(0);
        SetState(PlayState.Playing);
    }

    public void Pause()
    {
        if (State == PlayState.Playing) SetState(PlayState.Paused);
    }

    public void Stop()
    {
        lock (sync) { if (reader != null) SeekLocked(0); }
        SetState(PlayState.Stopped);
    }

    public void Unload()
    {
        lock (sync)
        {
            reader?.Dispose();
            reader = null;
            chain = null;
            Source = null;
        }
        SetState(PlayState.Stopped);
    }

    public void Seek(double seconds)
    {
        lock (sync) SeekLocked(seconds);
        if (State == PlayState.Stopped) SetState(PlayState.Paused);
    }

    public double Position
    {
        get
        {
            if (State == PlayState.Stopped) return 0;
            lock (sync) return reader == null ? 0 : seekBase + tempo.SourceFramesConsumed / (double)Rate;
        }
    }

    public double Duration
    {
        get { lock (sync) return reader?.TotalTime.TotalSeconds ?? 0; }
    }

    public void SetSpeed(double s) { lock (sync) tempo.Speed = Math.Clamp(s, 0.25, 4); }
    public void SetKeyLock(bool on) { lock (sync) tempo.KeyLock = on; }

    void SetState(PlayState s)
    {
        if (s == State) return;
        State = s;
        ui.Post(_ => StateChanged?.Invoke(), null);
    }

    // ------------------------------------------------------------ Audio-Thread
    public int Read(float[] buffer, int offset, int count)
    {
        int n = 0;
        lock (sync)
        {
            if (State == PlayState.Playing && chain != null && !sourceEnded)
            {
                n = tempo.Read(buffer, offset, count);
                if (n < count)
                {
                    sourceEnded = true;
                    ui.Post(_ => { if (State == PlayState.Playing) Ended?.Invoke(); }, null);
                }
            }
        }
        if (n < count) Array.Clear(buffer, offset + n, count - n);
        float v = Volume, pl = 0, pr = 0;
        for (int i = 0; i < n; i += 2)
        {
            float l = buffer[offset + i] * v, r = buffer[offset + i + 1] * v;
            buffer[offset + i] = l;
            buffer[offset + i + 1] = r;
            pl = Math.Max(pl, Math.Abs(l));
            pr = Math.Max(pr, Math.Abs(r));
        }
        PeakL = pl;
        PeakR = pr;
        return count;
    }

    public void Dispose()
    {
        running = false;
        output?.Stop();
        output?.Dispose();
        reader?.Dispose();
    }

    sealed class FirstTwoChannels : ISampleProvider
    {
        readonly ISampleProvider src;
        readonly int ch;
        float[] buf = Array.Empty<float>();
        public FirstTwoChannels(ISampleProvider s)
        {
            src = s;
            ch = s.WaveFormat.Channels;
            WaveFormat = WaveFormat.CreateIeeeFloatWaveFormat(s.WaveFormat.SampleRate, 2);
        }
        public WaveFormat WaveFormat { get; }
        public int Read(float[] buffer, int offset, int count)
        {
            int frames = count / 2;
            if (buf.Length < frames * ch) buf = new float[frames * ch];
            int got = src.Read(buf, 0, frames * ch) / ch;
            for (int i = 0; i < got; i++)
            {
                buffer[offset + 2 * i] = buf[i * ch];
                buffer[offset + 2 * i + 1] = buf[i * ch + 1];
            }
            return got * 2;
        }
    }
}

/// <summary>
/// Tempo-Prozessor für Stereo-Float bei 44,1 kHz.
/// Varispeed: Resampling (Tempo und Tonhöhe ändern sich gemeinsam).
/// Key Lock: WSOLA-Zeitdehnung (nur das Tempo ändert sich).
/// </summary>
public sealed class TempoProcessor
{
    const int N = 1536;             // Segmentlänge (Frames)
    const int Hs = N / 2;           // Synthese-Schritt
    const int Search = 384;         // Suchbereich ±
    const int CorrLen = 512;

    ISampleProvider src;
    float[] inBuf = new float[1 << 16];   // interleaved Stereo
    int inFrames;                          // gültige Frames im Puffer
    long inBase;                           // Quell-Frame-Index von inBuf[0]
    bool srcDone;

    double vPos;                           // Varispeed: Lesekopf relativ zu inBase
    double aPos;                           // WSOLA: Analyse-Position (absolut)
    long prevBest = -1;
    readonly float[] overlap = new float[Hs * 2];
    readonly float[] outBuf = new float[Hs * 2];
    int outAvail, outPos;
    static readonly float[] Window = MakeWindow();

    public double Speed = 1.0;
    bool keyLock;
    public bool KeyLock
    {
        get => keyLock;
        set { if (value != keyLock) { keyLock = value; Resync(); } }
    }

    public long SourceFramesConsumed { get; private set; }

    static float[] MakeWindow()
    {
        var w = new float[N];
        for (int i = 0; i < N; i++) w[i] = 0.5f - 0.5f * MathF.Cos(2 * MathF.PI * i / N);
        return w;
    }

    public void Reset(ISampleProvider s)
    {
        src = s;
        inFrames = 0;
        inBase = 0;
        srcDone = false;
        SourceFramesConsumed = 0;
        Resync();
    }

    void Resync()
    {
        long cur = SourceFramesConsumed;
        vPos = cur - inBase;
        aPos = cur;
        prevBest = -1;
        Array.Clear(overlap);
        outAvail = outPos = 0;
    }

    bool Ensure(long absFrameEnd)
    {
        while (inBase + inFrames < absFrameEnd && !srcDone)
        {
            // Platz schaffen: bereits verbrauchte Frames vorne verwerfen
            long keepFrom = (long)Math.Floor(KeyLock ? aPos - 2 * N - Search : inBase + vPos - 4);
            if (prevBest >= 0) keepFrom = Math.Min(keepFrom, prevBest);
            keepFrom = Math.Min(keepFrom, inBase + inFrames);
            int drop = (int)Math.Max(0, keepFrom - inBase);
            if (drop > 0)
            {
                Array.Copy(inBuf, drop * 2, inBuf, 0, (inFrames - drop) * 2);
                inFrames -= drop;
                inBase += drop;
                vPos -= drop;
            }
            if ((inFrames + 4096) * 2 > inBuf.Length) Array.Resize(ref inBuf, inBuf.Length * 2);
            int got = src.Read(inBuf, inFrames * 2, 4096 * 2) / 2;
            if (got <= 0) srcDone = true;
            inFrames += Math.Max(0, got);
        }
        return inBase + inFrames >= absFrameEnd;
    }

    float In(long abs, int ch)
    {
        long i = abs - inBase;
        if (i < 0 || i >= inFrames) return 0;
        return inBuf[i * 2 + ch];
    }

    public int Read(float[] buffer, int offset, int count)
    {
        if (src == null) return 0;
        int frames = count / 2, done = 0;
        if (Math.Abs(Speed - 1.0) < 1e-4 && outAvail == outPos)
        {
            // Originaltempo: direkt durchreichen
            while (done < frames)
            {
                long abs = SourceFramesConsumed;
                int want = frames - done;
                if (!Ensure(abs + want) && inBase + inFrames <= abs) break;
                int avail = (int)Math.Min(want, inBase + inFrames - abs);
                Array.Copy(inBuf, (abs - inBase) * 2, buffer, offset + done * 2, avail * 2);
                done += avail;
                SourceFramesConsumed += avail;
            }
            vPos = SourceFramesConsumed - inBase;
            aPos = SourceFramesConsumed;
            prevBest = -1;
            return done * 2;
        }
        if (!KeyLock)
        {
            while (done < frames)
            {
                long i0 = inBase + (long)Math.Floor(vPos);
                if (!Ensure(i0 + 2) && inBase + inFrames < i0 + 2) break;
                float f = (float)(vPos - Math.Floor(vPos));
                int k = (int)(i0 - inBase);
                for (int c = 0; c < 2; c++)
                    buffer[offset + done * 2 + c] = inBuf[k * 2 + c] * (1 - f) + inBuf[(k + 1) * 2 + c] * f;
                done++;
                vPos += Speed;
                SourceFramesConsumed = inBase + (long)vPos;
            }
            return done * 2;
        }
        // Key Lock (WSOLA)
        while (done < frames)
        {
            if (outPos >= outAvail && !WsolaStep()) break;
            int take = Math.Min(frames - done, outAvail - outPos);
            Array.Copy(outBuf, outPos * 2, buffer, offset + done * 2, take * 2);
            outPos += take;
            done += take;
        }
        return done * 2;
    }

    bool WsolaStep()
    {
        long center = (long)Math.Round(aPos);
        if (!Ensure(center + Search + N + 1) && inBase + inFrames < center + N) return false;
        long best = center;
        if (prevBest >= 0)
        {
            long natural = prevBest + Hs;
            double bestScore = double.NegativeInfinity;
            long lo = Math.Max(inBase, center - Search), hi = center + Search;
            for (long k = lo; k <= hi; k += 2)
            {
                double s = 0;
                for (int j = 0; j < CorrLen; j += 4)
                    s += (In(k + j, 0) + In(k + j, 1)) * (In(natural + j, 0) + In(natural + j, 1));
                if (s > bestScore) { bestScore = s; best = k; }
            }
        }
        for (int i = 0; i < Hs; i++)
        {
            for (int c = 0; c < 2; c++)
            {
                outBuf[i * 2 + c] = overlap[i * 2 + c] + In(best + i, c) * Window[i];
                overlap[i * 2 + c] = In(best + Hs + i, c) * Window[Hs + i];
            }
        }
        outAvail = Hs;
        outPos = 0;
        prevBest = best;
        aPos += Hs * Speed;
        SourceFramesConsumed = (long)aPos;
        return true;
    }
}
