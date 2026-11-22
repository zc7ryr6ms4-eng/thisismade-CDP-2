// Hauptfenster: randloses Windows-11-Fenster mit der Gerätefront, Maus/Tastatur/Drag & Drop.
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Drawing.Imaging;
using System.Runtime.InteropServices;

namespace Thisismade;

sealed class MainForm : Form
{
    readonly Player player;
    readonly MediaControls media;
    readonly System.Windows.Forms.Timer frameTimer = new() { Interval = 16 };
    readonly System.Windows.Forms.Timer longTimer = new() { Interval = 650 };
    readonly System.Windows.Forms.Timer jogTimer = new() { Interval = 50 };
    readonly ContextMenuStrip menu = new();
    double lastTick;
    double idleAcc;
    Form helpForm;

    sealed class Action_
    {
        public string Id;
        public Point Start;
        public bool Right, Shift, LongDone;
        public int StartValue;
        public float Moved;
        public float PrevAngle;
        public bool WasPlaying;
        public double Scrub, LastSeek;
    }
    Action_ act;

    public MainForm(string[] args)
    {
        Text = Program.AppName;
        FormBorderStyle = FormBorderStyle.None;
        StartPosition = FormStartPosition.CenterScreen;
        DoubleBuffered = true;
        KeyPreview = true;
        AllowDrop = true;
        BackColor = Color.FromArgb(242, 242, 241);
        SetStyle(ControlStyles.AllPaintingInWmPaint | ControlStyles.UserPaint | ControlStyles.OptimizedDoubleBuffer | ControlStyles.ResizeRedraw, true);
        try { Icon = Icon.ExtractAssociatedIcon(Application.ExecutablePath); } catch { }

        player = new Player();
        player.Changed += () => Invalidate();
        player.ShowHelp = ShowHelp;
        player.OpenFolderDialog = OpenFolder;
        player.OpenFilesDialog = OpenFiles;
        player.QuitApp = Close;

        var area = Screen.PrimaryScreen?.WorkingArea ?? new Rectangle(0, 0, 1600, 900);
        var saved = player.Settings.Window;
        if (saved is Rectangle r && r.Width > 200 && Screen.AllScreens.Any(s => s.WorkingArea.IntersectsWith(r)))
        {
            StartPosition = FormStartPosition.Manual;
            Bounds = r;
        }
        else
        {
            float z = Math.Min(area.Width * 0.75f / Face.DevW, area.Height * 0.75f / Face.DevH);
            ClientSize = new Size((int)(Face.DevW * z), (int)(Face.DevH * z));
        }
        MinimumSize = new Size((int)(Face.DevW * 0.3f), (int)(Face.DevH * 0.3f));

        media = new MediaControls(this, player);
        player.MediaLed = media.Available;
        player.NowPlaying = (t, img, playing) => media.Update(t, img, playing, t != null);

        BuildMenu();
        frameTimer.Tick += (_, _) => Tick();
        longTimer.Tick += (_, _) => { longTimer.Stop(); LongPress(); };
        jogTimer.Tick += (_, _) => JogStep();
        frameTimer.Start();
        lastTick = player.Now;

        Shown += (_, _) =>
        {
            Native.StyleWindow(Handle);
            if (Environment.GetEnvironmentVariable("TMPLAYER_SELFTEST") is string st) SelfTest(st);
            else if (args.Length > 0) player.Open(args);
            else player.RestoreSession();
        };
        FormClosing += (_, _) =>
        {
            if (Environment.GetEnvironmentVariable("TMPLAYER_SELFTEST") == null)
                player.SaveSettings(WindowState == FormWindowState.Normal ? Bounds : RestoreBounds);
            frameTimer.Stop();
            media.Dispose();
            player.Dispose();
            Native.KeepAwake(false);
        };
    }

    // ------------------------------------------------------------ Zeichnen
    (float s, float ox, float oy) Fit()
    {
        float s = Math.Min(ClientSize.Width / Face.DevW, ClientSize.Height / Face.DevH);
        return (s, (ClientSize.Width - Face.DevW * s) / 2, (ClientSize.Height - Face.DevH * s) / 2);
    }

    PointF ToDev(Point p)
    {
        var (s, ox, oy) = Fit();
        return new PointF((p.X - ox) / s, (p.Y - oy) / s);
    }

    protected override void OnPaint(PaintEventArgs e)
    {
        var g = e.Graphics;
        var (s, ox, oy) = Fit();
        g.Clear(BackColor);
        g.TranslateTransform(ox, oy);
        g.ScaleTransform(s, s);
        Face.Draw(g, player.State());
    }

    void Tick()
    {
        double now = player.Now;
        double dt = Math.Min(0.1, now - lastTick);
        lastTick = now;
        if (player.Animate(dt) || act != null) { Invalidate(); idleAcc = 0; }
        else
        {
            idleAcc += dt;
            if (idleAcc > 0.25) { idleAcc = 0; Invalidate(); }
        }
    }

    // ------------------------------------------------------------ Fenster: verschieben, Größe, Seitenverhältnis
    protected override void WndProc(ref Message m)
    {
        if (m.Msg == Native.WM_NCHITTEST)
        {
            base.WndProc(ref m);
            var p = PointToClient(new Point((short)(m.LParam.ToInt64() & 0xFFFF), (short)((m.LParam.ToInt64() >> 16) & 0xFFFF)));
            const int b = 8;
            bool l = p.X < b, r = p.X >= ClientSize.Width - b, t = p.Y < b, bo = p.Y >= ClientSize.Height - b;
            if (WindowState == FormWindowState.Normal)
            {
                if (bo && r) m.Result = Native.HTBOTTOMRIGHT;
                else if (bo && l) m.Result = Native.HTBOTTOMLEFT;
                else if (t && r) m.Result = Native.HTTOPRIGHT;
                else if (t && l) m.Result = Native.HTTOPLEFT;
                else if (r) m.Result = Native.HTRIGHT;
                else if (l) m.Result = Native.HTLEFT;
                else if (bo) m.Result = Native.HTBOTTOM;
                else if (t) m.Result = Native.HTTOP;
            }
            return;
        }
        if (m.Msg == Native.WM_SIZING)
        {
            var rc = Marshal.PtrToStructure<Native.RECT>(m.LParam);
            int edge = m.WParam.ToInt32();
            float ratio = Face.DevW / Face.DevH;
            int w = rc.Right - rc.Left, h = rc.Bottom - rc.Top;
            if (edge is Native.WMSZ_LEFT or Native.WMSZ_RIGHT) h = (int)(w / ratio);
            else if (edge is Native.WMSZ_TOP or Native.WMSZ_BOTTOM) w = (int)(h * ratio);
            else h = (int)(w / ratio);
            if (edge is Native.WMSZ_TOPLEFT or Native.WMSZ_TOPRIGHT or Native.WMSZ_TOP) rc.Top = rc.Bottom - h; else rc.Bottom = rc.Top + h;
            if (edge is Native.WMSZ_TOPLEFT or Native.WMSZ_BOTTOMLEFT or Native.WMSZ_LEFT) rc.Left = rc.Right - w; else rc.Right = rc.Left + w;
            Marshal.StructureToPtr(rc, m.LParam, false);
            m.Result = (IntPtr)1;
            return;
        }
        if (m.Msg == Native.WM_COPYDATA)
        {
            var cds = Marshal.PtrToStructure<Native.COPYDATASTRUCT>(m.LParam);
            var text = Marshal.PtrToStringUni(cds.lpData) ?? "";
            var paths = text.Split('\n', StringSplitOptions.RemoveEmptyEntries);
            if (paths.Length > 0) player.Open(paths);
            Activate();
            m.Result = (IntPtr)1;
            return;
        }
        base.WndProc(ref m);
    }

    void DragWindow()
    {
        Native.ReleaseCapture();
        Native.SendMessage(Handle, Native.WM_NCLBUTTONDOWN, (IntPtr)Native.HTCAPTION, IntPtr.Zero);
    }

    // ------------------------------------------------------------ Maus
    protected override void OnMouseMove(MouseEventArgs e)
    {
        base.OnMouseMove(e);
        if (act != null) { DragUpdate(e); return; }
        Cursor = Face.Hit(ToDev(e.Location)) switch
        {
            null => Cursors.Default,
            "disc" => Cursors.Hand,
            "jog" => Cursors.SizeWE,
            "varispeed" or "level" => Cursors.SizeNS,
            _ => Cursors.Hand,
        };
    }

    protected override void OnMouseDown(MouseEventArgs e)
    {
        base.OnMouseDown(e);
        bool right = e.Button == MouseButtons.Right;
        if (!right && e.Button != MouseButtons.Left) return;
        var d = ToDev(e.Location);
        var id = Face.Hit(d);
        var pl = player;

        if (right && (id == null || id == "disc")) { menu.Show(this, e.Location); return; }
        if (id == null || (id == "disc" && !pl.PowerOn)) { if (!right) DragWindow(); return; }
        if (!pl.PowerOn && id != "power") return;

        var a = new Action_ { Id = id, Start = e.Location, Right = right, Shift = ModifierKeys.HasFlag(Keys.Shift) };
        switch (id)
        {
            case "varispeed":
            case "level":
                if (e.Clicks == 2 && id == "varispeed") { pl.SetVarispeed(100); pl.Flash("tEnPo 100", 0.6); }
                a.StartValue = id == "varispeed" ? pl.Varispeed : pl.Level;
                break;
            case "jog":
                pl.JogHeld = true;
                pl.Pressed.Add("jog");
                jogTimer.Start();
                break;
            case "disc":
                a.PrevAngle = MathF.Atan2(d.Y - Face.DiscC.Y, d.X - Face.DiscC.X);
                a.WasPlaying = pl.Engine.State == PlayState.Playing;
                a.Scrub = pl.Engine.Position;
                break;
            case "main_display":
                break;
            default:
                pl.Pressed.Add(id);
                var longIds = new[] { "power", "key_C", "key_T", "cue1", "cue2", "cue3" };
                if (!right && longIds.Contains(id) && !(id.StartsWith("cue") && a.Shift)) longTimer.Start();
                break;
        }
        act = a;
        Capture = true;
        Invalidate();
    }

    void LongPress()
    {
        if (act == null) return;
        act.LongDone = true;
        switch (act.Id)
        {
            case "power": player.QuitApp?.Invoke(); break;
            case "key_C": player.KeypadLong("C"); break;
            case "key_T": player.KeypadLong("T"); break;
            case "cue1": case "cue2": case "cue3": player.CueSet(act.Id[^1] - '1'); break;
        }
    }

    void DragUpdate(MouseEventArgs e)
    {
        var a = act;
        var pl = player;
        float s = Fit().s;
        float ox = e.X - a.Start.X, oy = e.Y - a.Start.Y;
        a.Moved = Math.Max(a.Moved, MathF.Sqrt(ox * ox + oy * oy) / s);
        switch (a.Id)
        {
            case "varispeed":
            case "level":
                float k = ModifierKeys.HasFlag(Keys.Shift) ? 0.2f : 1f;
                float delta = (-oy + ox * 0.5f) / s;
                if (a.Id == "varispeed") pl.SetVarispeed(a.StartValue + (int)MathF.Round(delta * k * 100 / 180));
                else pl.SetLevel(a.StartValue + (int)MathF.Round(delta * k * 100 / 220));
                break;
            case "jog":
                pl.Jog = Math.Clamp(ox / s / (Face.JogTravel * 1.6f), -1, 1);
                break;
            case "disc":
                var d = ToDev(e.Location);
                float ang = MathF.Atan2(d.Y - Face.DiscC.Y, d.X - Face.DiscC.X);
                float da = ang - a.PrevAngle;
                while (da > MathF.PI) da -= 2 * MathF.PI;
                while (da < -MathF.PI) da += 2 * MathF.PI;
                a.PrevAngle = ang;
                if (a.Moved > 4 && !pl.Scrubbing)
                {
                    pl.Scrubbing = true;
                    if (a.WasPlaying) pl.Pause();
                }
                if (pl.Scrubbing)
                {
                    pl.DiscAngle += da;
                    a.Scrub = Math.Max(0, a.Scrub + da / (2 * Math.PI) * 1.8);
                    if (pl.Now - a.LastSeek > 0.06) { a.LastSeek = pl.Now; pl.SeekTo(a.Scrub); }
                    Invalidate();
                }
                break;
        }
    }

    protected override void OnMouseUp(MouseEventArgs e)
    {
        base.OnMouseUp(e);
        var a = act;
        if (a == null) return;
        act = null;
        Capture = false;
        longTimer.Stop();
        var pl = player;
        pl.Pressed.Remove(a.Id);
        bool inside = Face.Hit(ToDev(e.Location)) == a.Id;
        switch (a.Id)
        {
            case "jog":
                pl.JogHeld = false;
                pl.Pressed.Remove("jog");
                jogTimer.Stop();
                break;
            case "disc":
                if (pl.Scrubbing)
                {
                    pl.SeekTo(a.Scrub);
                    pl.Scrubbing = false;
                    if (a.WasPlaying) pl.Play();
                }
                else if (a.Moved < 4) pl.PlayPause();
                break;
            case "varispeed":
            case "level":
                break;
            case "main_display":
                if (inside) pl.ToggleTimeMode();
                break;
            default:
                if (inside && !a.LongDone) Press(a.Id, a.Right, a.Shift);
                break;
        }
        Invalidate();
    }

    void Press(string id, bool right, bool shift)
    {
        var pl = player;
        if (id == "power") { pl.TogglePower(); return; }
        if (!pl.PowerOn) return;
        if (id.StartsWith("key_")) { pl.Keypad(id[4..]); return; }
        switch (id)
        {
            case "enter": pl.Enter(); break;
            case "cue1": case "cue2": case "cue3":
                int i = id[^1] - '1';
                if (right || shift) pl.CueClear(i); else pl.CuePress(i);
                break;
            case "play": pl.PlayPause(); break;
            case "stop": pl.Stop(); break;
            case "prev": pl.PrevTrack(); break;
            case "next": pl.NextTrack(); break;
            case "data": OpenFolder(); break;
            case "usb": OpenFiles(); break;
            case "cd": pl.OpenCd(); break;
            case "output": Launch("ms-settings:sound"); break;
            case "sync": ShowHelp(); break;
            case "keylock": pl.ToggleKeyLock(); break;
            case "repeat": pl.CycleRepeat(); break;
            case "shuffle": pl.SetShuffle(!pl.Shuffle); break;
            case "eject": pl.Eject(); break;
        }
    }

    void JogStep()
    {
        float j = player.Jog;
        if (Math.Abs(j) > 0.08f && player.HasTracks) player.SeekRelative(j * Math.Abs(j) * 16 * 0.05);
    }

    protected override void OnMouseWheel(MouseEventArgs e)
    {
        base.OnMouseWheel(e);
        var pl = player;
        if (!pl.PowerOn) return;
        float step = e.Delta / 120f;
        if (step == 0) return;
        int unit = (int)MathF.Round(step);
        if (unit == 0) unit = step > 0 ? 1 : -1;
        switch (Face.Hit(ToDev(e.Location)))
        {
            case "varispeed": pl.SetVarispeed(pl.Varispeed + unit); break;
            case "disc":
            case "jog":
                if (pl.HasTracks) { pl.DiscAngle += step * 0.15f; pl.SeekRelative(step * 2); }
                break;
            default: pl.SetLevel(pl.Level + unit * 2); break;
        }
    }

    // ------------------------------------------------------------ Tastatur
    void FlashKey(string id)
    {
        player.Pressed.Add(id);
        Invalidate();
        var t = new System.Windows.Forms.Timer { Interval = 120 };
        t.Tick += (_, _) => { t.Stop(); t.Dispose(); player.Pressed.Remove(id); Invalidate(); };
        t.Start();
    }

    protected override bool ProcessCmdKey(ref Message msg, Keys keyData)
    {
        var pl = player;
        var key = keyData & Keys.KeyCode;
        bool ctrl = keyData.HasFlag(Keys.Control), shift = keyData.HasFlag(Keys.Shift);
        if (ctrl)
        {
            switch (key)
            {
                case Keys.O: if (shift) OpenFolder(); else OpenFiles(); return true;
                case Keys.Q: case Keys.W: Close(); return true;
                case Keys.Oemplus: case Keys.Add: Zoom(1.1f); return true;
                case Keys.OemMinus: case Keys.Subtract: Zoom(1 / 1.1f); return true;
                case Keys.D0: case Keys.NumPad0: ZoomReset(); return true;
            }
            return base.ProcessCmdKey(ref msg, keyData);
        }
        if (!pl.PowerOn && key != Keys.P) return base.ProcessCmdKey(ref msg, keyData);
        if (key >= Keys.D0 && key <= Keys.D9 && !shift) { var c = ((char)('0' + (key - Keys.D0))).ToString(); FlashKey("key_" + c); pl.Keypad(c); return true; }
        if (key >= Keys.NumPad0 && key <= Keys.NumPad9) { var c = ((char)('0' + (key - Keys.NumPad0))).ToString(); FlashKey("key_" + c); pl.Keypad(c); return true; }
        switch (key)
        {
            case Keys.Space: FlashKey("play"); pl.PlayPause(); return true;
            case Keys.Enter: FlashKey("enter"); pl.Enter(); return true;
            case Keys.Escape: case Keys.OemPeriod: FlashKey("stop"); pl.Stop(); return true;
            case Keys.Left: pl.SeekRelative(shift ? -30 : -5); return true;
            case Keys.Right: pl.SeekRelative(shift ? 30 : 5); return true;
            case Keys.Up: pl.SetLevel(pl.Level + 2); return true;
            case Keys.Down: pl.SetLevel(pl.Level - 2); return true;
            case Keys.PageDown: case Keys.N: FlashKey("next"); pl.NextTrack(); return true;
            case Keys.PageUp: case Keys.B: FlashKey("prev"); pl.PrevTrack(); return true;
            case Keys.Back: case Keys.Delete: case Keys.C: FlashKey("key_C"); pl.ClearEntry(); return true;
            case Keys.Oemplus: case Keys.Add: pl.SetVarispeed(pl.Varispeed + 1); return true;
            case Keys.OemMinus: case Keys.Subtract: pl.SetVarispeed(pl.Varispeed - 1); return true;
            case Keys.Oem2: case Keys.Oem5: pl.SetVarispeed(100); return true;   // # bzw. \
            case Keys.T: FlashKey("key_T"); pl.ToggleTimeMode(); return true;
            case Keys.M: FlashKey("keylock"); pl.ToggleKeyLock(); return true;
            case Keys.R: FlashKey("repeat"); pl.CycleRepeat(); return true;
            case Keys.S: FlashKey("shuffle"); pl.SetShuffle(!pl.Shuffle); return true;
            case Keys.Q: case Keys.W: case Keys.E:
                int i = key == Keys.Q ? 0 : key == Keys.W ? 1 : 2;
                FlashKey("cue" + (i + 1));
                if (shift) pl.CueSet(i); else pl.CuePress(i);
                return true;
            case Keys.O: OpenFolder(); return true;
            case Keys.D: pl.OpenCd(); return true;
            case Keys.J: pl.Eject(); return true;
            case Keys.P: FlashKey("power"); pl.TogglePower(); return true;
            case Keys.H: case Keys.F1: ShowHelp(); return true;
        }
        if (!pl.MediaLed)   // ohne Windows-Mediensteuerung: Medientasten selbst auswerten
        {
            switch (key)
            {
                case Keys.MediaPlayPause: pl.PlayPause(); return true;
                case Keys.MediaNextTrack: pl.NextTrack(); return true;
                case Keys.MediaPreviousTrack: pl.PrevTrack(true); return true;
                case Keys.MediaStop: pl.Stop(); return true;
            }
        }
        return base.ProcessCmdKey(ref msg, keyData);
    }

    void Zoom(float f) => SetZoom(ClientSize.Width / Face.DevW * f);

    void ZoomReset()
    {
        var area = Screen.FromControl(this).WorkingArea;
        SetZoom(Math.Min(area.Width * 0.75f / Face.DevW, area.Height * 0.75f / Face.DevH));
    }

    void SetZoom(float z)
    {
        z = Math.Clamp(z, 0.3f, 2.5f);
        var c = new Point(Left + Width / 2, Top + Height / 2);
        ClientSize = new Size((int)(Face.DevW * z), (int)(Face.DevH * z));
        Location = new Point(c.X - Width / 2, c.Y - Height / 2);
    }

    // ------------------------------------------------------------ Drag & Drop
    protected override void OnDragEnter(DragEventArgs e)
    {
        base.OnDragEnter(e);
        if (e.Data?.GetDataPresent(DataFormats.FileDrop) == true) e.Effect = DragDropEffects.Copy;
    }

    protected override void OnDragDrop(DragEventArgs e)
    {
        base.OnDragDrop(e);
        if (e.Data?.GetData(DataFormats.FileDrop) is string[] files && files.Length > 0) player.Open(files);
    }

    // ------------------------------------------------------------ Dialoge & Menü
    void OpenFolder()
    {
        using var dlg = new FolderBrowserDialog
        {
            Description = "Ordner laden", UseDescriptionForTitle = true,
            InitialDirectory = Environment.GetFolderPath(Environment.SpecialFolder.MyMusic),
        };
        if (dlg.ShowDialog(this) == DialogResult.OK) player.Open(new[] { dlg.SelectedPath });
    }

    void OpenFiles()
    {
        using var dlg = new OpenFileDialog
        {
            Title = "Dateien laden", Multiselect = true,
            Filter = "Audio und Playlists|*.mp3;*.m4a;*.m4b;*.mp4;*.aac;*.wav;*.aif;*.aiff;*.flac;*.wma;*.alac;*.ac3;*.mp2;*.m3u;*.m3u8|Alle Dateien|*.*",
            InitialDirectory = Environment.GetFolderPath(Environment.SpecialFolder.MyMusic),
        };
        if (dlg.ShowDialog(this) == DialogResult.OK) player.Open(dlg.FileNames);
    }

    void BuildMenu()
    {
        void Add(string text, Action a, Keys keys = Keys.None)
        {
            var it = new ToolStripMenuItem(text, null, (_, _) => a());
            if (keys != Keys.None) it.ShortcutKeys = keys;
            menu.Items.Add(it);
        }
        Add("Ordner laden …", OpenFolder);
        Add("Dateien laden …", OpenFiles);
        Add("Audio-CD lesen", () => player.OpenCd());
        Add("Auswerfen", () => player.Eject());
        menu.Items.Add(new ToolStripSeparator());
        Add("Wiederholen umschalten", () => player.CycleRepeat());
        Add("Zufall umschalten", () => player.SetShuffle(!player.Shuffle));
        Add("Key Lock umschalten", () => player.ToggleKeyLock());
        menu.Items.Add(new ToolStripSeparator());
        Add("Größer", () => Zoom(1.1f));
        Add("Kleiner", () => Zoom(1 / 1.1f));
        Add("Immer im Vordergrund", () => TopMost = !TopMost);
        Add("Minimieren", () => WindowState = FormWindowState.Minimized);
        menu.Items.Add(new ToolStripSeparator());
        Add("Bedienung", ShowHelp);
        Add($"Über {Program.AppName}", () => MessageBox.Show(this,
            $"{Program.AppName} {Program.Version}\n\nCD-Player-Software mit Tempo, Key Lock, Memory-Cues und Shuttle.\n\nhttps://github.com/zc7ryr6ms4-eng/thisismade-CDP-2",
            Program.AppName, MessageBoxButtons.OK, MessageBoxIcon.Information));
        Add("Beenden", Close);
    }

    static void Launch(string uri)
    {
        try { System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo(uri) { UseShellExecute = true }); } catch { }
    }

    void ShowHelp()
    {
        if (helpForm is { IsDisposed: false }) { helpForm.Activate(); return; }
        var tb = new TextBox
        {
            Multiline = true, ReadOnly = true, ScrollBars = ScrollBars.Vertical, Dock = DockStyle.Fill,
            Font = new Font("Segoe UI", 10f), Text = HelpText.Replace("\n", "\r\n"), BorderStyle = BorderStyle.None,
            BackColor = Color.White,
        };
        helpForm = new Form
        {
            Text = Program.AppName + " – Bedienung", Width = 640, Height = 700, StartPosition = FormStartPosition.CenterParent,
            Icon = Icon, Padding = new Padding(14),
            BackColor = Color.White,
        };
        helpForm.Controls.Add(tb);
        helpForm.Show(this);
        tb.SelectionStart = 0;
    }

    // ------------------------------------------------------------ Selbsttest (GitHub Actions)
    void SelfTest(string file)
    {
        player.Open(new[] { file });
        int step = 0;
        double pos1 = 0;
        float maxPeak = 0;
        var t = new System.Windows.Forms.Timer { Interval = 1500 };
        var peakTimer = new System.Windows.Forms.Timer { Interval = 50 };
        peakTimer.Tick += (_, _) => maxPeak = Math.Max(maxPeak, Math.Max(player.Engine.PeakL, player.Engine.PeakR));
        peakTimer.Start();
        t.Tick += (_, _) =>
        {
            step++;
            if (step == 1)
            {
                pos1 = player.Engine.Position;
                player.SetVarispeed(130);
                player.CueSet(0);
                player.ToggleKeyLock();
                return;
            }
            t.Stop();
            peakTimer.Stop();
            double pos2 = player.Engine.Position;
            var fs = player.State();
            bool ok = player.Engine.State == PlayState.Playing && pos1 > 0.5 && pos2 > pos1 + 1.0 && maxPeak > 0.05f && player.Tracks.Count == 1
                      && fs.Resolution.Contains("kHz") && fs.Title.Length > 0;
            var shot = Environment.GetEnvironmentVariable("TMPLAYER_SCREENSHOT") ?? "screenshot.png";
            using (var bmp = new Bitmap(1200, 660))
            {
                using (var g = Graphics.FromImage(bmp)) Face.Draw(g, player.State());
                bmp.Save(shot, ImageFormat.Png);
            }
            var line = $"SELFTEST {(ok ? "OK" : "FAILED")} state={player.Engine.State} pos1={pos1:F2} pos2={pos2:F2} peak={maxPeak:F2} tracks={player.Tracks.Count} keylock={player.Engine.KeyLock} title={fs.Title} res={fs.Resolution}";
            File.WriteAllText(Environment.GetEnvironmentVariable("TMPLAYER_RESULT") ?? "selftest.txt", line);
            Environment.ExitCode = ok ? 0 : 1;
            Close();
        };
        t.Start();
    }

    const string HelpText = """
THISISMADE CD PLAYER – BEDIENUNG

LADEN
• OPEN: Ordner laden (Unterordner werden mitgelesen)
• FILES: einzelne Dateien oder Playlists (.m3u) laden
• CD: eingelegte Audio-CD abspielen
• Dateien oder Ordner einfach auf den Player ziehen
• EJECT: Disc auswerfen · Rechtsklick auf freie Fläche: Menü

LAUFWERK
• ▶❚❚ Play/Pause · ■ Stopp · ⏮ ⏭ Titel zurück/vor (⏮ nach 3 s: Titelanfang)
• Klick auf die Disc: Play/Pause · Disc mit der Maus drehen: scratchen/spulen
• Mausrad über der Disc: ±2 s

ZIFFERNBLOCK
• Titelnummer tippen, dann ENTER → springt zum Titel
• TIME: vergangene Zeit ↔ Restzeit · gedrückt halten: Key Lock
• CLR: Eingabe löschen; ohne Eingabe: Wiederholen · gedrückt halten: Zufall

MEMORY A · B · C
• Leere Taste: Merkpunkt setzen (LED leuchtet) · belegte Taste: dorthin springen
• Gedrückt halten: neu setzen · Rechtsklick oder Shift+Klick: löschen
• Merkpunkte werden pro Titel gespeichert

SHUTTLE: Schieber ziehen = Rück-/Vorlauf bis 16-fach

TEMPO: Fader ziehen (hoch = schneller), Shift = fein, Doppelklick = 100 %, Bereich 50–150 %.
KEY LOCK aus = Tempo und Tonhöhe gemeinsam (Varispeed), an = nur Tempo (Time Stretch).

VOLUME: Drehregler ziehen oder Mausrad auf freier Fläche · REPEAT aus/alle/einer · SHUFFLE

DISPLAY: TRACK = Titel · TOTAL = Anzahl · TIME = Min:Sek. Rechts: REPEAT, SHUFFLE,
KEY LOCK, PAUSE, REMAIN. Klick aufs Display: Zeitmodus.

OBEN: OUTPUT = Sound-Einstellungen · HELP = diese Hilfe · POWER = Standby, halten = Beenden.
MEDIA-LED: verbunden mit der Windows-Mediensteuerung (Medientasten, Sperrbildschirm).

TASTATUR
Leertaste Play/Pause · Esc Stopp · N/B Titel · ←/→ ±5 s (Shift ±30 s) · ↑/↓ Lautstärke
0–9 + Enter Titelwahl · +/- Tempo ±1 · # Tempo 100 · M Key Lock
Q W E Memory A–C (Shift = setzen) · T Zeitmodus · R Wiederholen · S Zufall
O Ordner · Strg+O Dateien · D Audio-CD · J Auswerfen · P Power · F1/H Hilfe
Strg + / Strg - / Strg 0 Größe · Strg+Q Beenden
Fenster verschieben: freie Fläche ziehen · Größe: Fensterrand ziehen

Formate: MP3, AAC/M4A, FLAC, ALAC, WAV, AIFF, WMA u. a. (alles, was Windows abspielt).
""";
}
