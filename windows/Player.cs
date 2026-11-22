// Bedienlogik des thisismade cdp-2 (entspricht tmplayer/app.py bzw. macos/Sources/Player.swift).
using System.Diagnostics;
using System.Drawing;
using System.Text.Json;

namespace Thisismade;

public sealed class Track
{
    public string Source;          // Dateipfad oder cdda://D/3
    public string Title;
    public string Artist;
    public string Album;
}

public sealed class Settings
{
    public int Level { get; set; } = 80;
    public int Varispeed { get; set; } = 100;
    public int Repeat { get; set; }
    public bool Shuffle { get; set; }
    public int TimeMode { get; set; }
    public bool KeyLock { get; set; }
    public Dictionary<string, double[]> Cues { get; set; } = new();
    public List<string> Paths { get; set; } = new();
    public int Index { get; set; } = -1;
    public double Position { get; set; }
    public Rectangle? Window { get; set; }
}

public sealed class Player : IDisposable
{
    public const int VsMin = 50, VsMax = 150;
    static readonly HashSet<string> AudioExt = new(StringComparer.OrdinalIgnoreCase)
    {
        ".mp3", ".m4a", ".m4b", ".mp4", ".aac", ".wav", ".wave", ".aif", ".aiff", ".flac", ".wma", ".alac",
        ".ac3", ".ec3", ".mp2", ".3gp", ".amr", ".adts",
    };
    static readonly Color[] DiscColors =
    {
        Color.FromArgb(237, 232, 219), Color.FromArgb(245, 245, 242), Color.FromArgb(33, 33, 36),
        Color.FromArgb(255, 153, 36), Color.FromArgb(51, 107, 102), Color.FromArgb(199, 204, 212),
    };

    public readonly AudioEngine Engine = new(Environment.GetEnvironmentVariable("TMPLAYER_SELFTEST") != null);
    public event Action Changed;
    public Action ShowHelp, OpenFolderDialog, OpenFilesDialog, QuitApp;
    public Action<Track, Image, bool> NowPlaying;   // für Windows-Mediensteuerung

    public List<Track> Tracks { get; private set; } = new();
    List<int> order = new();
    int opos;
    public int Index { get; private set; } = -1;
    Dictionary<string, double[]> cues = new();
    public int RepeatMode { get; private set; }
    public bool Shuffle { get; private set; }
    public int TimeMode { get; private set; }
    public int Varispeed { get; private set; } = 100;
    public int Level { get; private set; } = 80;
    string entry = "";
    double entryTime;
    string msg = "";
    double msgUntil;
    public bool PowerOn { get; private set; } = true;
    public readonly HashSet<string> Pressed = new();
    public float Jog;
    public bool JogHeld;
    public float DiscAngle;
    public bool Scrubbing;
    readonly float[] vu = { 0, 0 }, peaks = { 0, 0 };
    readonly double[] peakT = { 0, 0 };
    Image cover;
    List<string> discLines = new();
    Color discColor = DiscColors[0];
    public bool MediaLed;
    int errors;
    int metaToken;
    readonly Random rng = new();
    readonly Stopwatch clock = Stopwatch.StartNew();
    public Settings Settings { get; private set; }

    static string SettingsPath => System.IO.Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), "thisismade cdp-2", "settings.json");

    public Player()
    {
        Engine.StateChanged += OnState;
        Engine.Ended += OnEnded;
        Engine.Error += OnError;
        LoadSettings();
        Engine.Volume = MathF.Pow(Level / 100f, 3);
        Engine.SetSpeed(Varispeed / 100.0);
    }

    public double Now => clock.Elapsed.TotalSeconds;

    // ------------------------------------------------------------ Einstellungen
    void LoadSettings()
    {
        try
        {
            var oldPath = System.IO.Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
                                                 "Thisismade CD Player", "settings.json");
            if (!File.Exists(SettingsPath) && File.Exists(oldPath))
            {
                Directory.CreateDirectory(System.IO.Path.GetDirectoryName(SettingsPath)!);
                File.Copy(oldPath, SettingsPath);
            }
        }
        catch { }
        try { Settings = JsonSerializer.Deserialize<Settings>(File.ReadAllText(SettingsPath)) ?? new Settings(); }
        catch { Settings = new Settings(); }
        Level = Settings.Level;
        Varispeed = Settings.Varispeed;
        RepeatMode = Settings.Repeat;
        Shuffle = Settings.Shuffle;
        TimeMode = Settings.TimeMode;
        Engine.SetKeyLock(Settings.KeyLock);
        cues = Settings.Cues ?? new();
    }

    public void SaveSettings(Rectangle? window)
    {
        var s = new Settings
        {
            Level = Level, Varispeed = Varispeed, Repeat = RepeatMode, Shuffle = Shuffle, TimeMode = TimeMode,
            KeyLock = Engine.KeyLock,
            Cues = cues.Where(kv => kv.Value.Any(v => v >= 0)).ToDictionary(kv => kv.Key, kv => kv.Value),
            Paths = Tracks.Where(t => !t.Source.StartsWith("cdda://")).Take(5000).Select(t => t.Source).ToList(),
            Index = Index, Position = Engine.Position, Window = window,
        };
        try
        {
            Directory.CreateDirectory(System.IO.Path.GetDirectoryName(SettingsPath)!);
            File.WriteAllText(SettingsPath, JsonSerializer.Serialize(s));
        }
        catch (Exception ex) { Debug.WriteLine(ex); }
    }

    public void RestoreSession()
    {
        var paths = (Settings.Paths ?? new()).Where(File.Exists).ToList();
        if (paths.Count == 0) return;
        SetTracks(paths.Select(MakeTrack).ToList(), false);
        if (Settings.Index >= 0 && Settings.Index < Tracks.Count) PlayIndex(Settings.Index, false, Settings.Position);
    }

    // ------------------------------------------------------------ Laden
    static Track MakeTrack(string path) => new() { Source = path, Title = System.IO.Path.GetFileNameWithoutExtension(path) };

    static int NatCmp(string a, string b) => NaturalComparer.Compare(a, b);

    void Scan(string path, List<string> outList)
    {
        if (Directory.Exists(path))
        {
            string[] files, dirs;
            try
            {
                files = Directory.GetFiles(path);
                dirs = Directory.GetDirectories(path);
            }
            catch { return; }
            Array.Sort(files, NatCmp);
            Array.Sort(dirs, NatCmp);
            foreach (var f in files)
                if (AudioExt.Contains(System.IO.Path.GetExtension(f)) && !System.IO.Path.GetFileName(f).StartsWith('.')) outList.Add(f);
            foreach (var d in dirs)
                if ((new DirectoryInfo(d).Attributes & FileAttributes.Hidden) == 0) Scan(d, outList);
        }
        else if (File.Exists(path))
        {
            var ext = System.IO.Path.GetExtension(path).ToLowerInvariant();
            if (AudioExt.Contains(ext)) outList.Add(path);
            else if (ext is ".m3u" or ".m3u8")
            {
                var dir = System.IO.Path.GetDirectoryName(path)!;
                foreach (var raw in File.ReadAllLines(path))
                {
                    var ln = raw.Trim();
                    if (ln.Length == 0 || ln.StartsWith('#')) continue;
                    if (ln.StartsWith("file:///")) ln = new Uri(ln).LocalPath;
                    var full = System.IO.Path.IsPathRooted(ln) ? ln : System.IO.Path.Combine(dir, ln);
                    if (File.Exists(full)) outList.Add(full);
                }
            }
        }
    }

    public void Open(IEnumerable<string> paths)
    {
        var found = new List<string>();
        foreach (var p in paths) Scan(p, found);
        if (found.Count == 0) { Flash("no AUdio"); return; }
        SetTracks(found.Select(MakeTrack).ToList(), true);
    }

    void SetTracks(List<Track> t, bool autoplay)
    {
        Engine.Stop();
        Tracks = t;
        entry = "";
        MakeOrder(null);
        Flash($"LoAd {t.Count,3}", 1.0);
        if (autoplay && order.Count > 0) PlayIndex(order[0], true);
        UpdateNowPlaying();
    }

    public void Eject()
    {
        Engine.Unload();
        Tracks = new(); order = new(); Index = -1;
        cover = null; discLines = new();
        Flash("EJECt");
        UpdateNowPlaying();
    }

    public void OpenCd()
    {
        Flash("rEAd  cd", 10);
        Task.Run(() =>
        {
            try
            {
                var letter = CdAudio.FindAudioCd();
                if (letter == null) return (List<Track>)null;
                return CdAudio.ReadToc(letter.Value).Select(t => new Track
                {
                    Source = $"cdda://{letter}/{t.Number}", Title = $"TRACK {t.Number:00}", Album = "AUDIO CD",
                }).ToList();
            }
            catch { return null; }
        }).ContinueWith(task =>
        {
            var list = task.Result;
            if (list == null || list.Count == 0) { Flash("no  cd", 1.5); return; }
            SetTracks(list, true);
            Flash($"cd   {list.Count,3} tr", 1.5);
        }, TaskScheduler.FromCurrentSynchronizationContext());
    }

    void MakeOrder(int? keep)
    {
        order = Enumerable.Range(0, Tracks.Count).ToList();
        if (Shuffle && Tracks.Count > 1)
        {
            order = order.OrderBy(_ => rng.Next()).ToList();
            if (keep is int k && order.Remove(k)) order.Insert(0, k);
        }
        opos = keep is int kk && order.IndexOf(kk) >= 0 ? order.IndexOf(kk) : 0;
    }

    public bool HasTracks => Tracks.Count > 0 && Index >= 0;

    // ------------------------------------------------------------ Laufwerk
    public void PlayIndex(int i, bool play = true, double start = 0)
    {
        if (i < 0 || i >= Tracks.Count) return;
        Index = i;
        int p = order.IndexOf(i);
        if (p >= 0) opos = p;
        Engine.Load(Tracks[i].Source, play, start);
        cover = null;
        UpdateDisc();
        LoadMetadata(i);
        UpdateNowPlaying();
    }

    int? NextInOrder(bool wrap)
    {
        if (order.Count == 0) return null;
        int p = opos + 1;
        if (p >= order.Count) { if (!wrap) return null; p = 0; }
        return order[p];
    }

    int? PrevInOrder()
    {
        if (order.Count == 0) return null;
        int p = opos - 1;
        if (p < 0) p = order.Count - 1;
        return order[p];
    }

    public void Play()
    {
        if (!PowerOn) return;
        if (!HasTracks)
        {
            if (order.Count > 0) PlayIndex(order[0]); else Flash("no  dISC");
            return;
        }
        Engine.Play();
    }

    public void Pause() => Engine.Pause();
    public void PlayPause() { if (Engine.State == PlayState.Playing) Pause(); else Play(); }
    public void Stop() { Engine.Stop(); Notify(); }

    public void NextTrack()
    {
        if (Tracks.Count == 0) return;
        if (NextInOrder(true) is int n) PlayIndex(n);
    }

    public void PrevTrack(bool force = false)
    {
        if (Tracks.Count == 0) return;
        if (!force && Engine.Position > 3) { SeekTo(0); return; }
        if (PrevInOrder() is int p) PlayIndex(p);
    }

    public void SeekTo(double s) { Engine.Seek(s); UpdateNowPlaying(); }
    public void SeekRelative(double d) => Engine.Seek(Engine.Position + d);

    public void JumpTo(int n)
    {
        if (n >= 1 && n <= Tracks.Count) PlayIndex(n - 1); else Flash($"Err  {n,3}");
    }

    // ------------------------------------------------------------ Modi
    public void SetRepeat(int r)
    {
        RepeatMode = ((r % 3) + 3) % 3;
        Flash(new[] { "rEP  oFF", "rEP  ALL", "rEP  onE" }[RepeatMode]);
    }

    public void CycleRepeat() => SetRepeat(RepeatMode + 1);

    public void SetShuffle(bool on)
    {
        Shuffle = on;
        MakeOrder(Index >= 0 ? Index : null);
        Flash(on ? "SHUF  on" : "SHUF  oFF");
    }

    public void ToggleTimeMode()
    {
        TimeMode = 1 - TimeMode;
        Flash(TimeMode == 0 ? "ELAPSEd" : "rEnAIn", 0.8);
    }

    public void ToggleKeyLock()
    {
        Engine.SetKeyLock(!Engine.KeyLock);
        Flash(Engine.KeyLock ? "LoCK  on" : "LoCK  oFF", 1.0);
    }

    public void SetVarispeed(int v)
    {
        v = Math.Clamp(v, VsMin, VsMax);
        if (v == Varispeed) return;
        Varispeed = v;
        Engine.SetSpeed(v / 100.0);
        Notify();
    }

    public void SetLevel(int v)
    {
        v = Math.Clamp(v, 0, 100);
        if (v == Level) return;
        Level = v;
        Engine.Volume = MathF.Pow(v / 100f, 3);
        Notify();
    }

    public void TogglePower()
    {
        PowerOn = !PowerOn;
        if (!PowerOn) Engine.Pause(); else Flash("HELLo", 0.6);
        Notify();
    }

    // ------------------------------------------------------------ Memory (Cue)
    double[] CueList()
    {
        if (!HasTracks) return new double[] { -1, -1, -1 };
        return cues.TryGetValue(Tracks[Index].Source, out var c) && c.Length == 3 ? c : new double[] { -1, -1, -1 };
    }

    void SetCue(int i, double v)
    {
        if (!HasTracks) return;
        var l = (double[])CueList().Clone();
        l[i] = v;
        cues[Tracks[Index].Source] = l;
    }

    public void CuePress(int i)
    {
        if (!HasTracks) { Flash("no  dISC"); return; }
        double c = CueList()[i];
        if (c < 0) CueSet(i);
        else
        {
            SeekTo(c);
            if (Engine.State != PlayState.Playing) Play();
            Flash($"CUE {i + 1}", 0.6);
        }
    }

    public void CueSet(int i)
    {
        if (!HasTracks) return;
        SetCue(i, Engine.Position);
        Flash($"CUE {i + 1}  SEt", 0.8);
    }

    public void CueClear(int i)
    {
        if (!HasTracks) return;
        SetCue(i, -1);
        Flash($"CUE {i + 1}  CLr", 0.8);
    }

    // ------------------------------------------------------------ Ziffernblock
    public void Keypad(string k)
    {
        if (k.Length == 1 && char.IsDigit(k[0]))
        {
            if (Now - entryTime > 4) entry = "";
            entry = (entry + k);
            if (entry.Length > 3) entry = entry[^3..];
            entryTime = Now;
        }
        else if (k == "T") ToggleTimeMode();
        else if (k == "C") { if (entry.Length > 0) entry = ""; else CycleRepeat(); }
        Notify();
    }

    public void KeypadLong(string k)
    {
        if (k == "C") SetShuffle(!Shuffle);
        else if (k == "T") ToggleKeyLock();
    }

    public void Enter()
    {
        if (entry.Length > 0 && Now - entryTime < 4 && int.TryParse(entry, out int n)) { entry = ""; JumpTo(n); }
        else { entry = ""; PlayPause(); }
        Notify();
    }

    public void ClearEntry() { entry = ""; Notify(); }

    // ------------------------------------------------------------ Ereignisse
    void OnState()
    {
        bool playing = Engine.State == PlayState.Playing;
        Native.KeepAwake(playing);
        if (playing) errors = 0;
        UpdateNowPlaying();
        Notify();
    }

    void OnEnded()
    {
        if (RepeatMode == 2) { Engine.Seek(0); return; }
        if (NextInOrder(RepeatMode == 1) is int n) PlayIndex(n);
        else
        {
            Engine.Stop();
            if (order.Count > 0) { PlayIndex(order[0], false); Engine.Stop(); }
            Flash("End", 1.2);
        }
    }

    void OnError(string m)
    {
        Debug.WriteLine("Wiedergabefehler: " + m);
        Flash("Err", 1.2);
        errors++;
        if (errors < Tracks.Count && NextInOrder(RepeatMode == 1) is int n)
        {
            var t = new System.Windows.Forms.Timer { Interval = 400 };
            t.Tick += (_, _) => { t.Stop(); t.Dispose(); PlayIndex(n); };
            t.Start();
        }
    }

    // ------------------------------------------------------------ Metadaten
    void LoadMetadata(int i)
    {
        int token = ++metaToken;
        var src = Tracks[i].Source;
        if (src.StartsWith("cdda://")) return;
        Task.Run(() =>
        {
            string title = null, artist = null, album = null;
            byte[] art = null;
            try
            {
                using var f = TagLib.File.Create(src);
                title = f.Tag.Title;
                artist = f.Tag.FirstPerformer ?? f.Tag.FirstAlbumArtist;
                album = f.Tag.Album;
                if (f.Tag.Pictures?.Length > 0) art = f.Tag.Pictures[0].Data.Data;
            }
            catch { }
            art ??= FolderCover(src);
            Image img = null;
            if (art != null)
            {
                try { img = SquareCrop(Image.FromStream(new MemoryStream(art))); } catch { }
            }
            return (title, artist, album, img);
        }).ContinueWith(task =>
        {
            if (token != metaToken || i >= Tracks.Count) return;
            var (title, artist, album, img) = task.Result;
            if (!string.IsNullOrWhiteSpace(title)) Tracks[i].Title = title;
            Tracks[i].Artist = artist;
            Tracks[i].Album = album;
            cover = img;
            UpdateDisc();
            UpdateNowPlaying();
        }, TaskScheduler.FromCurrentSynchronizationContext());
    }

    static byte[] FolderCover(string path)
    {
        try
        {
            var dir = System.IO.Path.GetDirectoryName(path)!;
            string[] names = { "cover", "folder", "front", "album", "albumart", "artwork" };
            foreach (var f in Directory.GetFiles(dir).OrderBy(x => x))
            {
                var b = System.IO.Path.GetFileNameWithoutExtension(f).ToLowerInvariant();
                var e = System.IO.Path.GetExtension(f).ToLowerInvariant();
                if (names.Contains(b) && e is ".jpg" or ".jpeg" or ".png" or ".bmp") return File.ReadAllBytes(f);
            }
        }
        catch { }
        return null;
    }

    static Image SquareCrop(Image src)
    {
        int s = Math.Min(src.Width, src.Height), size = Math.Min(s, 640);
        var bmp = new Bitmap(size, size);
        using var g = Graphics.FromImage(bmp);
        g.InterpolationMode = System.Drawing.Drawing2D.InterpolationMode.HighQualityBicubic;
        g.DrawImage(src, new Rectangle(0, 0, size, size), new Rectangle((src.Width - s) / 2, (src.Height - s) / 2, s, s), GraphicsUnit.Pixel);
        src.Dispose();
        return bmp;
    }

    void UpdateDisc()
    {
        if (!HasTracks) return;
        var t = Tracks[Index];
        var lines = new List<string> { t.Title };
        if (!string.IsNullOrEmpty(t.Artist)) lines.Add(t.Artist);
        if (!string.IsNullOrEmpty(t.Album)) lines.Add(t.Album);
        lines.Add($"TRACK {Index + 1:00} / {Tracks.Count:00}");
        if (!t.Source.StartsWith("cdda://")) lines.Add(System.IO.Path.GetExtension(t.Source).TrimStart('.').ToUpperInvariant());
        discLines = lines.Select(l => l.ToUpperInvariant()).Select(l => l.Length > 30 ? l[..30] : l).ToList();
        var key = t.Album ?? System.IO.Path.GetDirectoryName(t.Source) ?? t.Source;
        uint h = 2166136261;
        foreach (char c in key) h = unchecked((h ^ (uint)c) * 16777619u);
        discColor = DiscColors[h % DiscColors.Length];
        Notify();
    }

    void UpdateNowPlaying()
    {
        NowPlaying?.Invoke(HasTracks ? Tracks[Index] : null, cover, Engine.State == PlayState.Playing);
    }

    // ------------------------------------------------------------ Anzeige
    public void Flash(string text, double secs = 1.0)
    {
        msg = text;
        msgUntil = Now + secs;
        Notify();
    }

    void Notify() => Changed?.Invoke();

    (string, bool) DisplayText()
    {
        double now = Now;
        bool blink = ((int)(now * 2)) % 2 == 0;
        if (msg.Length > 0 && now < msgUntil) return (msg, true);
        if (Tracks.Count == 0) return ("------------", false);
        string tr = $"{(Index >= 0 ? Index + 1 : 0):000}";
        if (entry.Length > 0 && now - entryTime < 4) tr = blink ? new string('-', 3 - entry.Length) + entry : "   ";
        string idx = $"{Math.Min(999, Tracks.Count):000}";
        double pos = Engine.Position, dur = Engine.Duration;
        string tm, sec;
        if (TimeMode == 1 && dur > 0)
        {
            int rem = (int)Math.Ceiling(Math.Max(0, dur - pos));
            tm = $"-{Math.Min(99, rem / 60):00}";
            sec = $"{rem % 60:000}";
        }
        else
        {
            int p = (int)pos;
            tm = $"{Math.Min(999, p / 60):000}";
            sec = $"{p % 60:000}";
        }
        if (Engine.State == PlayState.Paused && !blink) { tm = "   "; sec = "   "; }
        return (tr + idx + tm + sec, false);
    }

    public FaceState State()
    {
        var (txt, msgMode) = DisplayText();
        return new FaceState
        {
            Pressed = Pressed, DiscLoaded = Tracks.Count > 0, DiscAngle = DiscAngle, DiscColor = discColor,
            DiscLines = discLines, Cover = cover, MediaLed = MediaLed, PowerOn = PowerOn,
            Vu = (float[])vu.Clone(), Peaks = (float[])peaks.Clone(), MainText = txt, MsgMode = msgMode,
            VsText = $"{Varispeed:000}", LvText = $"{Level:000}", KeyLock = Engine.KeyLock,
            CueSet = CueList().Select(c => c >= 0).ToArray(),
            VarispeedNorm = (Varispeed - VsMin) / (float)(VsMax - VsMin), LevelNorm = Level / 100f, Jog = Jog,
            RepeatMode = RepeatMode, Shuffle = Shuffle, Paused = Engine.State == PlayState.Paused, Remain = TimeMode == 1,
        };
    }

    static float Norm(float peak)
    {
        float db = 20 * MathF.Log10(Math.Max(peak, 1e-6f));
        return Math.Clamp((db + 48) / 48, 0, 1);
    }

    /// <summary>Pro Frame; true = neu zeichnen.</summary>
    public bool Animate(double dt)
    {
        bool busy = false;
        double now = Now;
        bool playing = Engine.State == PlayState.Playing && PowerOn;
        if (playing && !Scrubbing)
        {
            DiscAngle += (float)(dt * 2 * Math.PI * 0.55 * Varispeed / 100);
            busy = true;
        }
        float[] target = playing ? new[] { Norm(Engine.PeakL), Norm(Engine.PeakR) } : new[] { 0f, 0f };
        for (int i = 0; i < 2; i++)
        {
            if (target[i] >= vu[i]) vu[i] = target[i];
            else vu[i] = Math.Max(target[i], vu[i] - (float)dt * 1.6f);
            if (vu[i] >= peaks[i]) { peaks[i] = vu[i]; peakT[i] = now; }
            else if (now - peakT[i] > 0.8) peaks[i] = Math.Max(0, peaks[i] - (float)dt * 0.7f);
            if (vu[i] > 0.001f || peaks[i] > 0.001f) busy = true;
        }
        if (!JogHeld && Math.Abs(Jog) > 0.001f)
        {
            Jog *= Math.Max(0, 1 - (float)dt * 14);
            if (Math.Abs(Jog) < 0.01f) Jog = 0;
            busy = true;
        }
        return busy;
    }

    public void Dispose() => Engine.Dispose();
}

/// <summary>Natürliche Sortierung wie im Explorer ("Track 2" vor "Track 10").</summary>
static class NaturalComparer
{
    [System.Runtime.InteropServices.DllImport("shlwapi.dll", CharSet = System.Runtime.InteropServices.CharSet.Unicode)]
    static extern int StrCmpLogicalW(string a, string b);
    public static int Compare(string a, string b) =>
        StrCmpLogicalW(System.IO.Path.GetFileName(a), System.IO.Path.GetFileName(b));
}
