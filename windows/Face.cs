// Gerätefront des thisismade cdp-2 – GDI+-Zeichnung und Klickflächen.
// Koordinaten: Geräteeinheiten (1200 x 660), y nach unten.
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Drawing.Text;

namespace Thisismade;

public sealed class FaceState
{
    public HashSet<string> Pressed = new();
    public bool DiscLoaded;
    public float DiscAngle;               // Radiant
    public Color DiscColor = Color.FromArgb(237, 232, 219);
    public List<string> DiscLines = new();
    public Image Cover;
    public bool MediaLed;
    public bool PowerOn = true;
    public float[] Vu = { 0, 0 };
    public float[] Peaks = { 0, 0 };
    public string MainText = "------------";
    public bool MsgMode;
    public string VsText = "100";
    public string LvText = "080";
    public bool KeyLock;
    public bool[] CueSet = { false, false, false };
    public float VarispeedNorm = 0.5f;
    public float LevelNorm = 0.8f;
    public float Jog;
    public int RepeatMode;
    public bool Shuffle, Paused, Remain;
}

public static class Face
{
    public const float DevW = 1200, DevH = 660;

    static Color C(double r, double g, double b, double a = 1) =>
        Color.FromArgb((int)Math.Round(a * 255), (int)Math.Round(r * 255), (int)Math.Round(g * 255), (int)Math.Round(b * 255));

    static readonly Color Txt = C(0.22, 0.22, 0.24);
    static readonly Color TxtDim = C(0.50, 0.50, 0.52);
    static readonly Color Amber = C(1.0, 0.60, 0.14);
    static readonly Color SegOn = C(1.0, 0.13, 0.08);
    static readonly Color SegOff = C(0.20, 0.04, 0.035);
    static readonly Color LedOn = C(1.0, 0.18, 0.10);
    static readonly Color LedOff = C(0.80, 0.80, 0.81);

    public static readonly PointF DiscC = new(320, 360);
    public const float WellR = 272, DiscR = 250, HubR = 62;
    public static readonly RectangleF Display = new(630, 70, 540, 170);
    static readonly (string id, string text, float x)[] TopBtns =
    {
        ("data", "OPEN", 700), ("usb", "FILES", 772), ("cd", "CD", 844),
        ("output", "OUTPUT", 916), ("sync", "HELP", 988), ("power", "POWER", 1060),
    };
    const float TopW = 64, TopY = 18, TopH = 26;
    static readonly (string lab, float x, float y)[] Keys =
    {
        ("1", 630, 270), ("2", 690, 270), ("3", 750, 270), ("4", 810, 270), ("5", 870, 270),
        ("T", 930, 270), ("6", 630, 326), ("7", 690, 326), ("8", 750, 326), ("9", 810, 326),
        ("0", 870, 326), ("C", 930, 326),
    };
    const float KeyW = 50, KeyH = 44;
    static readonly RectangleF Enter = new(990, 270, 70, 100);
    static readonly PointF KnobC = new(1120, 318);
    const float KnobR = 48;
    static readonly (string id, string text, float x)[] Mem = { ("cue1", "A", 630), ("cue2", "B", 712), ("cue3", "C", 794) };
    const float MemY = 412, MemW = 72, MemH = 44;
    static readonly RectangleF Shuttle = new(890, 412, 170, 44);
    public const float JogTravel = 55;
    const float FaderX = 1120, FaderY0 = 446, FaderY1 = 626;
    static readonly (string id, float x, float w)[] Transport = { ("prev", 630, 90), ("next", 730, 90), ("stop", 830, 90), ("play", 930, 130) };
    const float TrY = 482, TrH = 82;
    static readonly (string id, string text, float x)[] Small =
    {
        ("keylock", "KEY LOCK", 630), ("repeat", "REPEAT", 742), ("shuffle", "SHUFFLE", 854), ("eject", "EJECT", 966),
    };
    const float SmallY = 590, SmallW = 94, SmallH = 34;

    // ------------------------------------------------------------- Klickflächen
    record Region(string Id, RectangleF Rect, PointF Center, float Radius, bool IsCircle);
    static readonly List<Region> Regions = BuildRegions();

    static List<Region> BuildRegions()
    {
        var r = new List<Region>();
        void R(string id, float x, float y, float w, float h) => r.Add(new Region(id, new RectangleF(x, y, w, h), default, 0, false));
        void Ci(string id, PointF c, float rad) => r.Add(new Region(id, default, c, rad, true));
        foreach (var b in TopBtns) R(b.id, b.x - 2, TopY - 4, TopW + 4, TopH + 8);
        foreach (var k in Keys) R("key_" + k.lab, k.x - 3, k.y - 3, KeyW + 6, KeyH + 6);
        R("enter", Enter.X, Enter.Y, Enter.Width, Enter.Height);
        Ci("level", KnobC, KnobR + 8);
        foreach (var m in Mem) R(m.id, m.x - 3, MemY - 3, MemW + 6, MemH + 6);
        R("jog", Shuttle.X - 4, Shuttle.Y - 18, Shuttle.Width + 8, Shuttle.Height + 22);
        R("varispeed", FaderX - 40, FaderY0 - 24, 80, FaderY1 - FaderY0 + 40);
        foreach (var t in Transport) R(t.id, t.x - 3, TrY - 3, t.w + 6, TrH + 6);
        foreach (var s in Small) R(s.id, s.x - 3, SmallY - 3, SmallW + 6, SmallH + 6);
        R("main_display", Display.X, Display.Y, Display.Width, Display.Height);
        Ci("disc", DiscC, DiscR);
        return r;
    }

    public static string Hit(PointF p)
    {
        foreach (var reg in Regions)
        {
            if (reg.IsCircle)
            {
                float dx = p.X - reg.Center.X, dy = p.Y - reg.Center.Y;
                if (dx * dx + dy * dy <= reg.Radius * reg.Radius) return reg.Id;
            }
            else if (reg.Rect.Contains(p)) return reg.Id;
        }
        return null;
    }

    // ------------------------------------------------------------- Helfer
    static GraphicsPath RRect(float x, float y, float w, float h, float r)
    {
        r = Math.Min(r, Math.Min(w / 2, h / 2));
        var p = new GraphicsPath();
        if (r <= 0.01f) { p.AddRectangle(new RectangleF(x, y, w, h)); return p; }
        float d = 2 * r;
        p.AddArc(x, y, d, d, 180, 90);
        p.AddArc(x + w - d, y, d, d, 270, 90);
        p.AddArc(x + w - d, y + h - d, d, d, 0, 90);
        p.AddArc(x, y + h - d, d, d, 90, 90);
        p.CloseFigure();
        return p;
    }

    static GraphicsPath Circle(float cx, float cy, float r)
    {
        var p = new GraphicsPath();
        p.AddEllipse(cx - r, cy - r, 2 * r, 2 * r);
        return p;
    }

    static void Fill(Graphics g, GraphicsPath p, Color c)
    {
        using var b = new SolidBrush(c);
        g.FillPath(b, p);
        p.Dispose();
    }

    static void FillV(Graphics g, GraphicsPath p, float y0, float y1, Color c0, Color c1)
    {
        if (y1 - y0 < 0.5f) y1 = y0 + 0.5f;
        using var b = new LinearGradientBrush(new PointF(0, y0 - 0.01f), new PointF(0, y1 + 0.01f), c0, c1) { WrapMode = WrapMode.TileFlipXY };
        g.FillPath(b, p);
        p.Dispose();
    }

    static void FillRadial(Graphics g, float cx, float cy, float r, PointF focus, Color center, Color edge)
    {
        using var path = Circle(cx, cy, r);
        using var b = new PathGradientBrush(path) { CenterPoint = focus, CenterColor = center, SurroundColors = new[] { edge } };
        g.FillPath(b, path);
    }

    static void Rect(Graphics g, float x, float y, float w, float h, Color c)
    {
        using var b = new SolidBrush(c);
        g.FillRectangle(b, x, y, w, h);
    }

    enum Align { Left, Center, Right }

    static readonly Dictionary<(float, bool), Font> Fonts = new();
    static readonly StringFormat Typo = (StringFormat)StringFormat.GenericTypographic.Clone();

    static Font GetFont(float size, bool bold)
    {
        if (!Fonts.TryGetValue((size, bold), out var f))
        {
            string family = "Segoe UI Variable Text";
            try { using var test = new FontFamily(family); } catch { family = "Segoe UI"; }
            f = new Font(family, size, bold ? FontStyle.Bold : FontStyle.Regular, GraphicsUnit.Pixel);
            Fonts[(size, bold)] = f;
        }
        return f;
    }

    static void Text(Graphics g, string s, float x, float baseline, float size, Color col, Align a = Align.Center, bool bold = false)
    {
        var f = GetFont(size, bold);
        var fam = f.FontFamily;
        var style = f.Style;
        float ascent = size * fam.GetCellAscent(style) / fam.GetEmHeight(style);
        Typo.FormatFlags |= StringFormatFlags.MeasureTrailingSpaces;
        float w = g.MeasureString(s, f, PointF.Empty, Typo).Width;
        if (a == Align.Center) x -= w / 2;
        else if (a == Align.Right) x -= w;
        using var b = new SolidBrush(col);
        g.DrawString(s, f, b, x, baseline - ascent, Typo);
    }

    // ------------------------------------------------------------- 7 Segmente
    static readonly Dictionary<char, string> Seg = new()
    {
        ['0'] = "abcdef", ['1'] = "bc", ['2'] = "abged", ['3'] = "abgcd", ['4'] = "fgbc", ['5'] = "afgcd",
        ['6'] = "afgedc", ['7'] = "abc", ['8'] = "abcdefg", ['9'] = "abcdfg", ['-'] = "g", [' '] = "", ['_'] = "d",
        ['A'] = "abcefg", ['b'] = "cdefg", ['C'] = "adef", ['c'] = "deg", ['d'] = "bcdeg", ['E'] = "adefg",
        ['F'] = "aefg", ['G'] = "acdef", ['H'] = "bcefg", ['h'] = "cefg", ['I'] = "ef", ['i'] = "e", ['J'] = "bcde",
        ['L'] = "def", ['n'] = "ceg", ['o'] = "cdeg", ['O'] = "abcdef", ['P'] = "abefg", ['q'] = "abcfg", ['r'] = "eg",
        ['S'] = "afgcd", ['t'] = "defg", ['U'] = "bcdef", ['V'] = "bcdef", ['u'] = "cde", ['y'] = "bcdfg", ['Y'] = "bcdfg",
        ['='] = "dg",
    };

    static string SegChar(char ch)
    {
        if (Seg.TryGetValue(ch, out var s)) return s;
        if (Seg.TryGetValue(char.ToUpperInvariant(ch), out s)) return s;
        if (Seg.TryGetValue(char.ToLowerInvariant(ch), out s)) return s;
        return "";
    }

    static void Digit(Graphics g, float x, float y, float w, float h, char ch)
    {
        float t = Math.Max(2f, w * 0.17f), sk = 0.08f, hh = h / 2, gap = 1f;
        string lit = SegChar(ch);
        PointF P(float px, float py) => new(x + px + (h - py) * sk, y + py);
        PointF[] HSeg(float px, float py, float L) => new[]
        {
            P(px, py), P(px + t / 2, py - t / 2), P(px + L - t / 2, py - t / 2),
            P(px + L, py), P(px + L - t / 2, py + t / 2), P(px + t / 2, py + t / 2),
        };
        PointF[] VSeg(float px, float py, float L) => new[]
        {
            P(px, py), P(px + t / 2, py + t / 2), P(px + t / 2, py + L - t / 2),
            P(px, py + L), P(px - t / 2, py + L - t / 2), P(px - t / 2, py + t / 2),
        };
        var segs = new (char, PointF[])[]
        {
            ('a', HSeg(t / 2 + gap, t / 2, w - t - 2 * gap)), ('g', HSeg(t / 2 + gap, hh, w - t - 2 * gap)),
            ('d', HSeg(t / 2 + gap, h - t / 2, w - t - 2 * gap)),
            ('f', VSeg(t / 2, t / 2 + gap, hh - t / 2 - 2 * gap)), ('e', VSeg(t / 2, hh + gap, hh - t / 2 - 2 * gap)),
            ('b', VSeg(w - t / 2, t / 2 + gap, hh - t / 2 - 2 * gap)), ('c', VSeg(w - t / 2, hh + gap, hh - t / 2 - 2 * gap)),
        };
        using var on = new SolidBrush(SegOn);
        using var off = new SolidBrush(SegOff);
        foreach (var (name, pts) in segs) g.FillPolygon(lit.Contains(name) ? on : off, pts);
    }

    static void Digits(Graphics g, string text, float x, float y, float w, float h, float pitch)
    {
        for (int i = 0; i < text.Length; i++) Digit(g, x + i * pitch, y, w, h, text[i]);
    }

    // ------------------------------------------------------------- Bauteile
    enum Style { Key, Small, AmberKey }

    static float Button(Graphics g, float x, float y, float w, float h, bool pressed, Style style = Style.Key,
                        string label = null, float size = 13, bool? led = null, float r = 7)
    {
        (Color top, Color bot, Color side, Color fg) = style switch
        {
            Style.Key => (C(0.99, 0.99, 0.99), C(0.90, 0.90, 0.91), C(0.70, 0.70, 0.72), C(0.18, 0.18, 0.20)),
            Style.Small => (C(0.95, 0.95, 0.96), C(0.87, 0.87, 0.88), C(0.68, 0.68, 0.70), C(0.30, 0.30, 0.32)),
            _ => (C(1.0, 0.66, 0.24), C(0.95, 0.52, 0.08), C(0.55, 0.28, 0.03), C(0.16, 0.10, 0.04)),
        };
        float oy = pressed ? 2 : 0;
        Fill(g, RRect(x, y + 3, w, h, r), C(0, 0, 0, 0.16));
        Fill(g, RRect(x, y + oy, w, h - oy + 1, r), side);
        FillV(g, RRect(x, y + oy, w, h - 3, r), y, y + h, top, bot);
        Rect(g, x + r, y + oy + 0.6f, w - 2 * r, 1, C(1, 1, 1, 0.6));
        if (label != null) Text(g, label, x + w / 2, y + oy + (h - 3) / 2 + size * 0.36f, size, fg);
        if (led.HasValue) Fill(g, Circle(x + w - 10, y + oy + 10, 3.2f), led.Value ? LedOn : LedOff);
        return oy;
    }

    static void Tri(Graphics g, Brush b, params PointF[] pts) => g.FillPolygon(b, pts);

    static void Icon(Graphics g, string kind, float cx, float cy, Color col)
    {
        using var b = new SolidBrush(col);
        switch (kind)
        {
            case "prev":
                g.FillRectangle(b, cx - 12, cy - 9, 3, 18);
                foreach (float dx in new[] { 0f, 11f }) Tri(g, b, new(cx + 2 + dx, cy - 9), new(cx - 8 + dx, cy), new(cx + 2 + dx, cy + 9));
                break;
            case "next":
                foreach (float dx in new[] { 0f, 11f }) Tri(g, b, new(cx - 13 + dx, cy - 9), new(cx - 3 + dx, cy), new(cx - 13 + dx, cy + 9));
                g.FillRectangle(b, cx + 9, cy - 9, 3, 18);
                break;
            case "stop":
                g.FillRectangle(b, cx - 8, cy - 8, 16, 16);
                break;
            default:
                Tri(g, b, new(cx - 18, cy - 10), new(cx - 4, cy), new(cx - 18, cy + 10));
                g.FillRectangle(b, cx + 4, cy - 10, 4, 20);
                g.FillRectangle(b, cx + 12, cy - 10, 4, 20);
                break;
        }
    }

    static void Knob(Graphics g, float value)
    {
        float cx = KnobC.X, cy = KnobC.Y;
        using (var tick = new SolidBrush(TxtDim))
        {
            for (int i = 0; i < 21; i++)
            {
                double a = (225 - 13.5 * i) * Math.PI / 180, a2 = a + 0.015;
                float r0 = KnobR + 7, r1 = KnobR + (i % 5 == 0 ? 13 : 10);
                g.FillPolygon(tick, new[]
                {
                    new PointF(cx + (float)Math.Cos(a) * r0, cy - (float)Math.Sin(a) * r0),
                    new PointF(cx + (float)Math.Cos(a) * r1, cy - (float)Math.Sin(a) * r1),
                    new PointF(cx + (float)Math.Cos(a2) * r1, cy - (float)Math.Sin(a2) * r1),
                    new PointF(cx + (float)Math.Cos(a2) * r0, cy - (float)Math.Sin(a2) * r0),
                });
            }
        }
        Fill(g, Circle(cx, cy + 4, KnobR), C(0, 0, 0, 0.2));
        FillV(g, Circle(cx, cy, KnobR), cy - KnobR, cy + KnobR, C(0.96, 0.96, 0.97), C(0.78, 0.78, 0.80));
        FillRadial(g, cx, cy, KnobR - 7, new PointF(cx - 12, cy - 14), C(1, 1, 1), C(0.90, 0.90, 0.91));
        double ang = (225 - 270 * Math.Clamp(value, 0, 1)) * Math.PI / 180;
        float ca = (float)Math.Cos(ang), sa = (float)Math.Sin(ang), px = -sa, py = -ca;
        float q0 = 12, q1 = KnobR - 10;
        using var amber = new SolidBrush(Amber);
        g.FillPolygon(amber, new[]
        {
            new PointF(cx + ca * q0 + px * 2, cy - sa * q0 + py * 2), new PointF(cx + ca * q1 + px * 2, cy - sa * q1 + py * 2),
            new PointF(cx + ca * q1 - px * 2, cy - sa * q1 - py * 2), new PointF(cx + ca * q0 - px * 2, cy - sa * q0 - py * 2),
        });
    }

    static void Fader(Graphics g, float value)
    {
        float x = FaderX;
        for (int i = 0; i < 9; i++)
        {
            float y = FaderY1 - i * (FaderY1 - FaderY0) / 8;
            Rect(g, x - 30, y - 0.6f, i == 4 ? 16 : 12, 1.2f, i == 4 ? Amber : TxtDim);
        }
        Fill(g, RRect(x - 4, FaderY0 - 8, 8, FaderY1 - FaderY0 + 16, 4), C(0.30, 0.30, 0.32));
        float cy = FaderY1 - Math.Clamp(value, 0, 1) * (FaderY1 - FaderY0);
        Fill(g, RRect(x - 22, cy - 11, 44, 26, 4), C(0, 0, 0, 0.2));
        FillV(g, RRect(x - 22, cy - 14, 44, 28, 4), cy - 14, cy + 14, C(1, 1, 1), C(0.86, 0.86, 0.87));
        Rect(g, x - 18, cy - 1, 36, 2, Amber);
    }

    static void Spindle(Graphics g)
    {
        FillV(g, Circle(0, 0, 30), -30, 30, C(0.80, 0.80, 0.82), C(0.45, 0.45, 0.47));
        FillV(g, Circle(0, 0, 22), -22, 22, C(0.40, 0.40, 0.42), C(0.75, 0.75, 0.77));
        for (int i = 0; i < 3; i++)
        {
            double a = i * 2 * Math.PI / 3 + 0.3;
            Fill(g, Circle((float)Math.Cos(a) * 14, (float)Math.Sin(a) * 14, 3.2f), C(0.95, 0.95, 0.96));
        }
        Fill(g, Circle(0, 0, 5), C(0.15, 0.15, 0.16));
    }

    static void Disc(Graphics g, FaceState st)
    {
        Fill(g, Circle(DiscC.X + 3, DiscC.Y + 8, DiscR), C(0, 0, 0, 0.5));
        var saved = g.Save();
        g.TranslateTransform(DiscC.X, DiscC.Y);
        g.RotateTransform(st.DiscAngle * 180f / MathF.PI);
        FillRadial(g, 0, 0, DiscR, new PointF(-60, -80), C(0.86, 0.87, 0.89), C(0.70, 0.71, 0.74));
        float pr = DiscR - 4;
        if (st.Cover != null)
        {
            using var clip = Circle(0, 0, pr);
            var s2 = g.Save();
            g.SetClip(clip);
            g.InterpolationMode = InterpolationMode.HighQualityBicubic;
            g.DrawImage(st.Cover, -pr, -pr, 2 * pr, 2 * pr);
            g.Restore(s2);
        }
        else
        {
            var col = st.DiscColor;
            Fill(g, Circle(0, 0, pr), col);
            bool light = col.R + col.G + col.B > 1.8 * 255;
            var ink = light ? C(0.12, 0.12, 0.13) : C(0.95, 0.94, 0.90);
            foreach (float rr in new[] { DiscR - 22, DiscR - 27, HubR + 24 })
            {
                Fill(g, Circle(0, 0, rr), Color.FromArgb(102, ink));
                Fill(g, Circle(0, 0, rr - 1.2f), col);
            }
            var lines = st.DiscLines;
            if (lines.Count > 0) Text(g, Trunc(lines[0], 22), 0, -128, 22, ink, Align.Center, true);
            for (int i = 1; i < Math.Min(lines.Count, 5); i++) Text(g, Trunc(lines[i], 30), 0, -100 + (i - 1) * 16, 12, ink);
            Text(g, "thisismade", 0, 150, 18, ink);
            Text(g, "COMPACT DISC · DIGITAL AUDIO", 0, 170, 9, ink);
            Fill(g, Circle(150, 0, 6), Amber);
        }
        Fill(g, Circle(0, 0, HubR), C(0.55, 0.57, 0.60));
        Fill(g, Circle(0, 0, HubR - 3), C(0.30, 0.31, 0.33));
        Spindle(g);
        g.Restore(saved);
    }

    static string Trunc(string s, int n) => s.Length > n ? s[..n] : s;

    // ------------------------------------------------------------- Gesamtbild
    public static void Draw(Graphics g, FaceState st)
    {
        g.SmoothingMode = SmoothingMode.AntiAlias;
        g.PixelOffsetMode = PixelOffsetMode.HighQuality;
        g.TextRenderingHint = TextRenderingHint.AntiAlias;
        g.CompositingQuality = CompositingQuality.HighQuality;
        DrawStatic(g);
        DrawDynamic(g, st);
    }

    static void DrawStatic(Graphics g)
    {
        using (var p = new GraphicsPath())
        {
            p.AddRectangle(new RectangleF(-2, -2, DevW + 4, DevH + 4));
            FillV(g, p, 0, DevH, C(0.985, 0.985, 0.98), C(0.90, 0.90, 0.90));
        }
        Rect(g, 0, 0.5f, DevW, 1.2f, C(1, 1, 1, 0.9));

        Text(g, "thisismade", 40, 42, 24, C(0.12, 0.12, 0.13), Align.Left, true);
        Text(g, "CD PLAYER  ·  CDP-2", 184, 41, 12, TxtDim, Align.Left);

        float cx = DiscC.X, cy = DiscC.Y;
        Fill(g, Circle(cx, cy, WellR + 3), C(0.80, 0.80, 0.81));
        FillRadial(g, cx, cy, WellR, new PointF(cx, cy - 40), C(0.10, 0.10, 0.11), C(0.05, 0.05, 0.055));
        var s = g.Save();
        g.TranslateTransform(cx, cy);
        g.RotateTransform(135);
        Fill(g, RRect(60, -20, 190, 40, 8), C(0.02, 0.02, 0.025));
        Fill(g, Circle(150, 0, 9), C(0.20, 0.22, 0.30));
        Fill(g, Circle(150, 0, 4), C(0.45, 0.50, 0.75));
        g.Restore(s);

        var d = Display;
        Fill(g, RRect(d.X - 6, d.Y - 6, d.Width + 12, d.Height + 12, 12), C(0.80, 0.80, 0.81));
        FillV(g, RRect(d.X, d.Y, d.Width, d.Height, 7), d.Top, d.Bottom, C(0.045, 0.025, 0.025), C(0.07, 0.035, 0.035));

        Text(g, "VOLUME", KnobC.X, KnobC.Y + KnobR + 26, 11, TxtDim);
        Text(g, "MEMORY", 630, MemY - 10, 11, TxtDim, Align.Left);
        Text(g, "SHUTTLE", Shuttle.X, MemY - 10, 11, TxtDim, Align.Left);
        Text(g, "TEMPO", FaderX, FaderY0 - 30, 11, TxtDim);
        Text(g, "+", FaderX + 26, FaderY0 + 4, 12, TxtDim);
        Text(g, "−", FaderX + 26, FaderY1 + 4, 12, TxtDim);
    }

    static void DrawDynamic(Graphics g, FaceState st)
    {
        var P = st.Pressed;
        bool on = st.PowerOn;

        foreach (var b in TopBtns)
        {
            Button(g, b.x, TopY, TopW, TopH, P.Contains(b.id), Style.Small, b.text, 10, null, 5);
            if (b.id == "power") Fill(g, Circle(b.x + 9, TopY + 13, 2.6f), on ? LedOn : LedOff);
        }
        Fill(g, Circle(1146, 31, 3), st.MediaLed && on ? C(0.30, 0.65, 1.0) : LedOff);
        Text(g, "MEDIA", 1156, 35, 9, TxtDim, Align.Left);

        if (st.DiscLoaded) Disc(g, st);
        else
        {
            var s = g.Save();
            g.TranslateTransform(DiscC.X, DiscC.Y);
            g.RotateTransform(st.DiscAngle * 180f / MathF.PI);
            Spindle(g);
            g.Restore(s);
            Text(g, "NO DISC", DiscC.X, DiscC.Y + 70, 14, C(0.85, 0.85, 0.86));
            Text(g, "OPEN = Ordner · FILES = Dateien · oder hierher ziehen", DiscC.X, DiscC.Y + 92, 11, TxtDim);
        }

        DrawDisplay(g, st);

        foreach (var k in Keys)
        {
            string t = k.lab == "T" ? "TIME" : k.lab == "C" ? "CLR" : k.lab;
            Button(g, k.x, k.y, KeyW, KeyH, P.Contains("key_" + k.lab), Style.Key, t, t.Length == 1 ? 17 : 11);
        }
        Button(g, Enter.X, Enter.Y, Enter.Width, Enter.Height, P.Contains("enter"), Style.Key, "ENTER", 12);

        Knob(g, st.LevelNorm);

        for (int i = 0; i < Mem.Length; i++)
            Button(g, Mem[i].x, MemY, MemW, MemH, P.Contains(Mem[i].id), Style.Key, Mem[i].text, 17, st.CueSet[i] && on);

        var sh = Shuttle;
        Fill(g, RRect(sh.X, sh.Y + 12, sh.Width, sh.Height - 24, 10), C(0.30, 0.30, 0.32));
        Text(g, "REW", sh.X + 16, sh.Bottom + 14, 10, TxtDim);
        Text(g, "FF", sh.Right - 12, sh.Bottom + 14, 10, TxtDim);
        float jx = sh.X + sh.Width / 2 + st.Jog * JogTravel;
        Fill(g, RRect(jx - 22, sh.Y + 4, 44, sh.Height - 4, 6), C(0, 0, 0, 0.2));
        FillV(g, RRect(jx - 22, sh.Y, 44, sh.Height - 4, 6), sh.Y, sh.Bottom, C(1, 1, 1), C(0.86, 0.86, 0.87));
        Rect(g, jx - 1.5f, sh.Y + 6, 3, sh.Height - 16, Amber);

        Fader(g, st.VarispeedNorm);

        foreach (var t in Transport)
        {
            float oy = Button(g, t.x, TrY, t.w, TrH, P.Contains(t.id), t.id == "play" ? Style.AmberKey : Style.Key);
            Icon(g, t.id, t.x + t.w / 2, TrY + oy + TrH / 2 - 2, t.id == "play" ? C(0.16, 0.10, 0.04) : C(0.18, 0.18, 0.20));
        }

        foreach (var s in Small)
        {
            bool? led = s.id switch
            {
                "keylock" => st.KeyLock && on,
                "repeat" => st.RepeatMode > 0 && on,
                "shuffle" => st.Shuffle && on,
                _ => null,
            };
            Button(g, s.x, SmallY, SmallW, SmallH, P.Contains(s.id), Style.Small, s.text, 10, led, 5);
        }

        if (!on)
        {
            using var p = new GraphicsPath();
            p.AddRectangle(new RectangleF(0, 0, DevW, DevH));
            Fill(g, p.Clone() as GraphicsPath, C(0, 0, 0, 0.12));
        }
    }

    static void DrawDisplay(Graphics g, FaceState st)
    {
        float x = Display.X, y = Display.Y, w = Display.Width;
        bool on = st.PowerOn;
        Color L(bool a) => a && on ? SegOn : SegOff;
        const float dw = 26, dh = 46, pitch = 34;
        string main = on ? (st.MainText + new string(' ', 12))[..12] : new string(' ', 12);
        if (on && st.MsgMode)
        {
            Digits(g, main, x + 18, y + 38, dw, dh, pitch);
        }
        else
        {
            Text(g, "TRACK", x + 18, y + 26, 10, L(true), Align.Left);
            Text(g, "TOTAL", x + 136, y + 26, 10, L(true), Align.Left);
            Text(g, "TIME", x + 254, y + 26, 10, L(true), Align.Left);
            Digits(g, main[0..3], x + 18, y + 38, dw, dh, pitch);
            Digits(g, main[3..6], x + 136, y + 38, dw, dh, pitch);
            Digits(g, main[6..9], x + 254, y + 38, dw, dh, pitch);
            foreach (float dy in new[] { 14f, 32f }) Fill(g, Circle(x + 362 + (46 - dy) * 0.08f, y + 38 + dy, 3), L(true));
            Digits(g, main[10..12], x + 372, y + 38, dw, dh, pitch);
        }
        var ind = new (string, bool)[]
        {
            (st.RepeatMode == 2 ? "REPEAT 1" : "REPEAT", st.RepeatMode > 0), ("SHUFFLE", st.Shuffle),
            ("KEY LOCK", st.KeyLock), ("PAUSE", st.Paused), ("REMAIN", st.Remain),
        };
        for (int i = 0; i < ind.Length; i++) Text(g, ind[i].Item1, x + w - 14, y + 26 + i * 15, 10, L(ind[i].Item2), Align.Right);
        float by = y + 118;
        Text(g, "TEMPO", x + 18, by - 6, 10, L(true), Align.Left);
        Digits(g, on ? st.VsText : "   ", x + 18, by, 15, 26, 20);
        Text(g, "%", x + 84, by + 25, 12, L(true), Align.Left);
        Text(g, "VOL", x + 110, by - 6, 10, L(true), Align.Left);
        Digits(g, on ? st.LvText : "   ", x + 110, by, 15, 26, 20);
        float mx = x + 200;
        const int n = 30;
        for (int row = 0; row < 2; row++)
        {
            float yy = by + 2 + row * 15;
            Text(g, row == 0 ? "L" : "R", mx, yy + 9, 10, L(true), Align.Left);
            int lit = (int)Math.Round(Math.Clamp(on ? st.Vu[row] : 0, 0, 1) * n);
            int pk = (int)Math.Round(Math.Clamp(on ? st.Peaks[row] : 0, 0, 1) * n);
            for (int i = 0; i < n; i++)
            {
                bool hot = i >= n - 5, isOn = i < lit || (pk > 0 && i == pk - 1);
                Rect(g, mx + 14 + i * 10.5f, yy, 8, 10,
                     isOn ? (hot ? C(1.0, 0.62, 0.14) : SegOn) : (hot ? C(0.20, 0.11, 0.03) : SegOff));
            }
        }
    }
}
