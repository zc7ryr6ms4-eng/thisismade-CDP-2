// Gerätefront des thisismade cdp-2 – Minimal-Design (Weiß, Orange, rotes Display), GDI+.
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
    public string Title = "";
    public string Resolution = "";
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

    // ------------------------------------------------------------- Minimal-Design
    static readonly Color Body = C(0.955, 0.955, 0.95);
    static readonly Color Line_ = C(0.74, 0.74, 0.75);
    static readonly Color Dot = C(0.80, 0.80, 0.81);
    static readonly Color Ink = C(0.12, 0.12, 0.13);
    static readonly Color Key = C(0.985, 0.985, 0.98);
    static readonly Color KeyHi = C(0.90, 0.90, 0.90);
    static readonly Color Orange = C(1.0, 0.40, 0.0);
    static readonly Color OrangeDim = C(0.86, 0.80, 0.75);

    static readonly Dictionary<float, Font> MonoFonts = new();

    static Font Mono(float size)
    {
        if (!MonoFonts.TryGetValue(size, out var f))
        {
            string fam = "Cascadia Mono";
            try { using var t = new FontFamily(fam); } catch { fam = "Consolas"; }
            f = new Font(fam, size, FontStyle.Regular, GraphicsUnit.Pixel);
            MonoFonts[size] = f;
        }
        return f;
    }

    static void MonoText(Graphics g, string s, float x, float baseline, float size, Color col, Align a = Align.Left)
    {
        var f = Mono(size);
        float ascent = size * f.FontFamily.GetCellAscent(f.Style) / f.FontFamily.GetEmHeight(f.Style);
        float w = g.MeasureString(s, f, PointF.Empty, Typo).Width;
        if (a == Align.Center) x -= w / 2;
        else if (a == Align.Right) x -= w;
        using var b = new SolidBrush(col);
        g.DrawString(s, f, b, x, baseline - ascent, Typo);
    }

    static void Stroke(Graphics g, GraphicsPath p, Color c, float w = 1f)
    {
        using var pen = new Pen(c, w);
        g.DrawPath(pen, p);
        p.Dispose();
    }

    static void FillStroke(Graphics g, GraphicsPath p, Color fill, Color edge, float w = 1f)
    {
        using (var b = new SolidBrush(fill)) g.FillPath(b, p);
        using (var pen = new Pen(edge, w)) g.DrawPath(pen, p);
        p.Dispose();
    }

    static void Ln(Graphics g, float x0, float y0, float x1, float y1, Color c, float w = 1f)
    {
        using var pen = new Pen(c, w);
        g.DrawLine(pen, x0, y0, x1, y1);
    }

    static void Led(Graphics g, float x, float y, bool on) => Rect(g, x - 3, y - 3, 6, 6, on ? Orange : OrangeDim);

    static void RoundKey(Graphics g, float cx, float cy, float r, bool pressed, Color fill)
        => FillStroke(g, Circle(cx, cy, r), pressed ? Orange : fill, pressed ? Orange : Line_);

    static void SquareKey(Graphics g, float x, float y, float w, float h, bool pressed, Color fill, float r = 6)
        => FillStroke(g, RRect(x, y, w, h, r), pressed ? Orange : fill, pressed ? Orange : Line_);

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
        Rect(g, -2, -2, DevW + 4, DevH + 4, Body);

        using (var dot = new SolidBrush(Dot))
        {
            for (int j = 13; j < DevH - 8; j += 16)
                for (int i = 13; i < 600; i += 16)
                {
                    float dx = i - DiscC.X, dy = j - DiscC.Y;
                    if (dx * dx + dy * dy < (WellR + 10) * (WellR + 10)) continue;
                    g.FillEllipse(dot, i - 1.1f, j - 1.1f, 2.2f, 2.2f);
                }
        }

        Ln(g, 610, 14, 610, DevH - 14, Line_);
        Ln(g, 620, 255, DevW - 14, 255, Line_);
        Ln(g, 620, 392, DevW - 14, 392, Line_);
        Ln(g, 620, 578, 1075, 578, Line_);
        Ln(g, 1075, 255, 1075, DevH - 14, Line_);

        Text(g, "thisismade", 30, 44, 24, Ink, Align.Left, true);
        MonoText(g, "CDP-2 / COMPACT DISC PLAYER", 31, 62, 10, TxtDim);
        Stroke(g, RRect(520, 34, 54, 14, 7), Orange);
        MonoText(g, "AUDIO", 547, 45, 9, Orange, Align.Center);

        float cx = DiscC.X, cy = DiscC.Y;
        FillStroke(g, Circle(cx, cy, WellR), C(0.90, 0.90, 0.895), Line_);
        for (int rr = 80; rr < WellR - 6; rr += 18) Stroke(g, Circle(cx, cy, rr), C(0.84, 0.84, 0.84));
        for (int k = 0; k < 12; k++)
        {
            double a = 2 * Math.PI * k / 12;
            Ln(g, cx + (float)Math.Cos(a) * (WellR - 10), cy + (float)Math.Sin(a) * (WellR - 10),
               cx + (float)Math.Cos(a) * (WellR - 2), cy + (float)Math.Sin(a) * (WellR - 2), TxtDim);
        }

        var d = Display;
        FillStroke(g, RRect(d.X - 4, d.Y - 4, d.Width + 8, d.Height + 8, 8), C(0.06, 0.05, 0.045), C(0.55, 0.55, 0.56));

        foreach (var (t, tx, ty) in new (string, float, float)[]
                 {
                     ("01  NUMBER", 630, 266), ("02  VOLUME", 1086, 268), ("03  MEMORY", 630, 406),
                     ("04  SHUTTLE", 890, 406), ("05  TRANSPORT", 630, 476), ("06  TEMPO", 1086, 406),
                     ("07  MODE", 630, 588),
                 })
            MonoText(g, t, tx, ty, 9, TxtDim);
    }

    static void DrawDynamic(Graphics g, FaceState st)
    {
        var P = st.Pressed;
        bool on = st.PowerOn;

        foreach (var b in TopBtns)
        {
            bool pr = P.Contains(b.id);
            FillStroke(g, RRect(b.x, TopY, TopW, TopH - 2, 12), pr ? Orange : Body,
                       pr || b.id == "power" ? Orange : Line_);
            MonoText(g, b.text.ToLowerInvariant(), b.x + TopW / 2, TopY + 16, 10,
                     pr ? Body : b.id == "power" ? Orange : Ink, Align.Center);
        }
        Led(g, 1146, 31, st.MediaLed && on);
        MonoText(g, "media", 1155, 35, 8, TxtDim);

        if (st.DiscLoaded) Disc(g, st);
        else
        {
            var s = g.Save();
            g.TranslateTransform(DiscC.X, DiscC.Y);
            g.RotateTransform(st.DiscAngle * 180f / MathF.PI);
            Spindle(g);
            g.Restore(s);
            MonoText(g, "no disc", DiscC.X, DiscC.Y + 70, 13, Ink, Align.Center);
            MonoText(g, "open / files / drop", DiscC.X, DiscC.Y + 90, 10, TxtDim, Align.Center);
        }

        DrawDisplay(g, st);

        foreach (var k in Keys)
        {
            float cx = k.x + KeyW / 2, cy = k.y + KeyH / 2 + 6;
            bool pr = P.Contains("key_" + k.lab);
            RoundKey(g, cx, cy, 19, pr, k.lab is "T" or "C" ? KeyHi : Key);
            string t = k.lab == "T" ? "time" : k.lab == "C" ? "clr" : k.lab;
            MonoText(g, t, cx, cy + (t.Length == 1 ? 5 : 3.5f), t.Length == 1 ? 15 : 10, pr ? Body : Ink, Align.Center);
        }
        bool pe = P.Contains("enter");
        SquareKey(g, Enter.X, Enter.Y + 12, Enter.Width, Enter.Height - 14, pe, KeyHi, 10);
        MonoText(g, "enter", Enter.X + Enter.Width / 2, Enter.Y + 12 + (Enter.Height - 14) / 2 + 4, 11, pe ? Body : Orange, Align.Center);

        Knob(g, st.LevelNorm);

        for (int i = 0; i < Mem.Length; i++)
        {
            bool pr = P.Contains(Mem[i].id);
            SquareKey(g, Mem[i].x, MemY + 2, MemW, MemH - 6, pr, Key, 8);
            MonoText(g, Mem[i].text.ToLowerInvariant(), Mem[i].x + 16, MemY + 28, 15, pr ? Body : Ink);
            Led(g, Mem[i].x + MemW - 14, MemY + 19, st.CueSet[i] && on);
        }

        var sh = Shuttle;
        float scy = sh.Y + sh.Height / 2 + 2;
        Ln(g, sh.X, scy, sh.Right, scy, Line_, 2);
        for (int k = -3; k <= 3; k++)
        {
            float tx = sh.X + sh.Width / 2 + k * sh.Width / 7;
            Ln(g, tx, scy - 6, tx, scy + 6, k == 0 ? Orange : TxtDim);
        }
        MonoText(g, "rew", sh.X, sh.Bottom + 12, 9, TxtDim);
        MonoText(g, "ff", sh.Right, sh.Bottom + 12, 9, TxtDim, Align.Right);
        float jx = sh.X + sh.Width / 2 + st.Jog * JogTravel;
        Rect(g, jx - 10, scy - 12, 20, 24, Orange);

        Fader(g, st.VarispeedNorm);

        foreach (var t in Transport)
        {
            bool pr = P.Contains(t.id), play = t.id == "play";
            SquareKey(g, t.x, TrY + 6, t.w, TrH - 12, pr, play ? Orange : Key, 12);
            Icon(g, t.id, t.x + t.w / 2, TrY + TrH / 2, pr || play ? Body : Ink);
        }

        foreach (var s in Small)
        {
            bool pr = P.Contains(s.id);
            bool? led = s.id switch
            {
                "keylock" => st.KeyLock,
                "repeat" => st.RepeatMode > 0,
                "shuffle" => st.Shuffle,
                _ => null,
            };
            FillStroke(g, RRect(s.x, SmallY + 12, SmallW, SmallH - 8, 13), pr ? Orange : Body, pr ? Orange : Line_);
            MonoText(g, s.text.ToLowerInvariant(), s.x + SmallW / 2 - (led.HasValue ? 6 : 0), SmallY + 29, 9,
                     pr ? Body : Ink, Align.Center);
            if (led.HasValue) Led(g, s.x + SmallW - 12, SmallY + 25, led.Value && on);
        }

        if (!on)
        {
            using var b = new SolidBrush(C(0, 0, 0, 0.12));
            g.FillRectangle(b, 0, 0, DevW, DevH);
        }
    }

    static void Spindle(Graphics g)
    {
        FillStroke(g, Circle(0, 0, 26), C(0.86, 0.86, 0.86), Line_);
        Fill(g, Circle(0, 0, 7), Orange);
    }

    static void Disc(Graphics g, FaceState st)
    {
        var saved = g.Save();
        g.TranslateTransform(DiscC.X, DiscC.Y);
        g.RotateTransform(st.DiscAngle * 180f / MathF.PI);
        Fill(g, Circle(0, 2, DiscR), C(0, 0, 0, 0.10));
        FillStroke(g, Circle(0, 0, DiscR), C(0.995, 0.995, 0.99), Line_);
        if (st.Cover != null)
        {
            using var clip = Circle(0, 0, DiscR - 2);
            var s2 = g.Save();
            g.SetClip(clip);
            g.InterpolationMode = InterpolationMode.HighQualityBicubic;
            g.DrawImage(st.Cover, -(DiscR - 2), -(DiscR - 2), 2 * (DiscR - 2), 2 * (DiscR - 2));
            g.Restore(s2);
        }
        else
        {
            var ink = C(0.10, 0.10, 0.11);
            Stroke(g, Circle(0, 0, DiscR - 14), C(0.80, 0.80, 0.81));
            Stroke(g, Circle(0, 0, HubR + 30), C(0.80, 0.80, 0.81));
            var lines = st.DiscLines;
            if (lines.Count > 0) Text(g, Trunc(lines[0], 22).ToLowerInvariant(), -150, -120, 22, ink, Align.Left, true);
            for (int i = 1; i < Math.Min(lines.Count, 5); i++)
                MonoText(g, Trunc(lines[i], 30).ToLowerInvariant(), -150, -96 + (i - 1) * 15, 10, C(0.30, 0.30, 0.32));
            MonoText(g, "thisismade / cdp-2", -150, 170, 10, ink);
            Rect(g, DiscR - 40, -5, 24, 10, Orange);
        }
        FillStroke(g, Circle(0, 0, HubR), C(0.93, 0.93, 0.93), Line_);
        Spindle(g);
        g.Restore(saved);
    }

    static string Trunc(string s, int n) => s.Length > n ? s[..n] : s;

    static void Knob(Graphics g, float value)
    {
        // mittig im Kasten "02 VOLUME" (x 1075…1186, y 255…392), samt Skala
        const float cx = 1131, cy = 331, r = 33;
        for (int i = 0; i < 31; i++)
        {
            double a = (225 - 9 * i) * Math.PI / 180;
            float r0 = r + 5, r1 = r + (i % 5 == 0 ? 12 : 8);
            bool lit = i / 30f <= value + 1e-6f;
            Ln(g, cx + (float)Math.Cos(a) * r0, cy - (float)Math.Sin(a) * r0,
               cx + (float)Math.Cos(a) * r1, cy - (float)Math.Sin(a) * r1, lit ? Orange : Line_, i % 5 == 0 ? 1.4f : 1f);
        }
        FillStroke(g, Circle(cx, cy, r), Key, Line_);
        double an = (225 - 270 * Math.Clamp(value, 0, 1)) * Math.PI / 180;
        using var pen = new Pen(Orange, 3f) { StartCap = LineCap.Round, EndCap = LineCap.Round };
        g.DrawLine(pen, cx + (float)Math.Cos(an) * 10, cy - (float)Math.Sin(an) * 10,
                   cx + (float)Math.Cos(an) * (r - 6), cy - (float)Math.Sin(an) * (r - 6));
    }

    static void Fader(Graphics g, float value)
    {
        float x = FaderX, y0 = FaderY0 + 4, y1 = FaderY1 - 10;
        Ln(g, x, y0, x, y1, Line_, 2);
        for (int i = 0; i < 11; i++)
        {
            float y = y1 - i * (y1 - y0) / 10;
            Ln(g, x + 18, y, x + (i % 5 == 0 ? 30 : 24), y, i == 5 ? Orange : TxtDim);
        }
        MonoText(g, "+", x - 26, y0 + 8, 11, TxtDim);
        MonoText(g, "-", x - 26, y1 + 2, 11, TxtDim);
        float cy = y1 - Math.Clamp(value, 0, 1) * (y1 - y0);
        Rect(g, x - 16, cy - 9, 32, 18, C(0.16, 0.16, 0.17));
        Rect(g, x - 16, cy - 1, 32, 2, Orange);
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
            if (on) TitleLine(g, st, x, y, w, L(true));
        }
        var ind = new (string, bool)[]
        {
            (st.RepeatMode == 2 ? "REPEAT 1" : "REPEAT", st.RepeatMode > 0), ("SHUFFLE", st.Shuffle),
            ("KEY LOCK", st.KeyLock), ("PAUSE", st.Paused), ("REMAIN", st.Remain),
        };
        for (int i = 0; i < ind.Length; i++) Text(g, ind[i].Item1, x + w - 14, y + 26 + i * 15, 10, L(ind[i].Item2), Align.Right);
        float by = y + 126;
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

    static readonly System.Diagnostics.Stopwatch Clock = System.Diagnostics.Stopwatch.StartNew();

    /// <summary>Titel (Laufschrift bei langen Namen) und Auflösung, innerhalb des Displays.</summary>
    static void TitleLine(Graphics g, FaceState st, float x, float y, float w, Color col)
    {
        string title = st.Title ?? "", res = st.Resolution ?? "";
        float ty = y + 101;
        var f = GetFont(11, true);
        float ascent = 11 * f.FontFamily.GetCellAscent(f.Style) / f.FontFamily.GetEmHeight(f.Style);
        float rw = res.Length > 0 ? g.MeasureString(res, f, PointF.Empty, Typo).Width : 0;
        using var b = new SolidBrush(col);
        if (res.Length > 0) g.DrawString(res, f, b, x + w - 14 - rw, ty - ascent, Typo);
        if (title.Length == 0) return;
        float boxX = x + 18, boxW = w - 32 - rw - (res.Length > 0 ? 16 : 0);
        float tw = g.MeasureString(title, f, PointF.Empty, Typo).Width;
        var saved = g.Save();
        g.SetClip(new RectangleF(boxX, ty - 13, boxW, 17));
        if (tw <= boxW) g.DrawString(title, f, b, boxX, ty - ascent, Typo);
        else
        {
            const float gap = 50;
            float off = (float)(Clock.Elapsed.TotalSeconds * 28 % (tw + gap));
            for (int k = 0; k < 2; k++) g.DrawString(title, f, b, boxX - off + k * (tw + gap), ty - ascent, Typo);
        }
        g.Restore(saved);
    }
}
