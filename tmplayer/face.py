"""Zeichnet die Gerätefront des thisismade cdp-2 (Cairo) und liefert die Klickflächen.

Koordinaten sind Geräteeinheiten: die Front ist DEV_W x DEV_H groß,
(0, 0) ist ihre linke obere Ecke.
"""
import math
import time

import cairo

DEV_W, DEV_H = 1200, 660
MARGIN_X, MARGIN_TOP, MARGIN_BOTTOM = 28, 24, 40
CANVAS_W = DEV_W + 2 * MARGIN_X
CANVAS_H = DEV_H + MARGIN_TOP + MARGIN_BOTTOM

FONT = "Inter"

# Farben
TXT = (0.22, 0.22, 0.24)
TXT_DIM = (0.50, 0.50, 0.52)
AMBER = (1.0, 0.60, 0.14)
VFD_ON = (1.0, 0.13, 0.08)
VFD_OFF = (0.20, 0.04, 0.035)

# ----------------------------------------------------------------- Layout
DISC_C = (320, 360)
WELL_R = 272
DISC_R = 250
HUB_R = 62

DISPLAY = (630, 70, 540, 170)
TOP_BTNS = [  # id, text, x
    ("data", "OPEN", 700), ("usb", "FILES", 772), ("cd", "CD", 844),
    ("output", "OUTPUT", 916), ("sync", "HELP", 988), ("power", "POWER", 1060),
]
TOP_W, TOP_Y, TOP_H = 64, 18, 26

KEYS = [("1", 630, 270), ("2", 690, 270), ("3", 750, 270), ("4", 810, 270), ("5", 870, 270),
        ("T", 930, 270), ("6", 630, 326), ("7", 690, 326), ("8", 750, 326), ("9", 810, 326),
        ("0", 870, 326), ("C", 930, 326)]
KEY_W, KEY_H = 50, 44
ENTER = (990, 270, 70, 100)
KNOB_C = (1120, 318)
KNOB_R = 48
MEM = [("cue1", "A", 630), ("cue2", "B", 712), ("cue3", "C", 794)]
MEM_Y, MEM_W, MEM_H = 412, 72, 44
SHUTTLE = (890, 412, 170, 44)
JOG_TRAVEL = 55
FADER_X, FADER_Y0, FADER_Y1 = 1120, 446, 626
TRANSPORT = [("prev", 630, 90), ("next", 730, 90), ("stop", 830, 90), ("play", 930, 130)]
TR_Y, TR_H = 482, 82
SMALL = [("vs_display", "KEY LOCK", 630), ("repeat", "REPEAT", 742), ("shuffle", "SHUFFLE", 854),
         ("eject", "EJECT", 966)]
SMALL_Y, SMALL_W, SMALL_H = 590, 94, 34


def hit_regions():
    r = []
    for rid, _t, x in TOP_BTNS:
        r.append((rid, "rect", (x - 2, TOP_Y - 4, TOP_W + 4, TOP_H + 8)))
    for lab, x, y in KEYS:
        r.append(("key_" + lab, "rect", (x - 3, y - 3, KEY_W + 6, KEY_H + 6)))
    r.append(("enter", "rect", ENTER))
    r.append(("level", "circle", (KNOB_C[0], KNOB_C[1], KNOB_R + 8)))
    for rid, _t, x in MEM:
        r.append((rid, "rect", (x - 3, MEM_Y - 3, MEM_W + 6, MEM_H + 6)))
    x, y, w, h = SHUTTLE
    r.append(("jog", "rect", (x - 4, y - 18, w + 8, h + 22)))
    r.append(("varispeed", "rect", (FADER_X - 40, FADER_Y0 - 24, 80, FADER_Y1 - FADER_Y0 + 40)))
    for rid, x, w in TRANSPORT:
        r.append((rid, "rect", (x - 3, TR_Y - 3, w + 6, TR_H + 6)))
    for rid, _t, x in SMALL:
        r.append((rid, "rect", (x - 3, SMALL_Y - 3, SMALL_W + 6, SMALL_H + 6)))
    dx, dy, dw, dh = DISPLAY
    r.append(("main_display", "rect", (dx, dy, dw, dh)))
    r.append(("disc", "circle", (DISC_C[0], DISC_C[1], DISC_R)))
    r.append(("resize", "rect", (DEV_W - 36, DEV_H - 36, 36 + MARGIN_X, 36 + MARGIN_BOTTOM)))
    return r


_REGIONS = hit_regions()


def hit(x, y):
    for rid, form, d in _REGIONS:
        if form == "rect":
            if d[0] <= x <= d[0] + d[2] and d[1] <= y <= d[1] + d[3]:
                return rid
        elif (x - d[0]) ** 2 + (y - d[1]) ** 2 <= d[2] ** 2:
            return rid
    return None


# ----------------------------------------------------------------- Helfer
def _rrect(cr, x, y, w, h, r):
    r = min(r, w / 2, h / 2)
    cr.new_sub_path()
    cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    cr.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
    cr.close_path()


def _circle(cr, cx, cy, r):
    cr.new_sub_path()
    cr.arc(cx, cy, r, 0, 2 * math.pi)
    cr.close_path()


def _rgb(cr, c, a=1.0):
    cr.set_source_rgba(c[0], c[1], c[2], a)


def _text(cr, s, x, y, size, color=TXT, align="center", bold=False):
    cr.select_font_face(FONT, cairo.FONT_SLANT_NORMAL,
                        cairo.FONT_WEIGHT_BOLD if bold else cairo.FONT_WEIGHT_NORMAL)
    cr.set_font_size(size)
    adv = cr.text_extents(s).x_advance
    if align == "center":
        x -= adv / 2
    elif align == "right":
        x -= adv
    _rgb(cr, color)
    cr.move_to(x, y)
    cr.show_text(s)


def _lin(y0, y1, c0, c1):
    g = cairo.LinearGradient(0, y0, 0, y1)
    g.add_color_stop_rgb(0, *c0)
    g.add_color_stop_rgb(1, *c1)
    return g


# ----------------------------------------------------------------- 7 Segmente
SEG = {
    "0": "abcdef", "1": "bc", "2": "abged", "3": "abgcd", "4": "fgbc", "5": "afgcd",
    "6": "afgedc", "7": "abc", "8": "abcdefg", "9": "abcdfg", "-": "g", " ": "", "_": "d",
    "A": "abcefg", "b": "cdefg", "C": "adef", "c": "deg", "d": "bcdeg", "E": "adefg",
    "F": "aefg", "G": "acdef", "H": "bcefg", "h": "cefg", "I": "ef", "i": "e", "J": "bcde",
    "L": "def", "n": "ceg", "o": "cdeg", "O": "abcdef", "P": "abefg", "q": "abcfg", "r": "eg",
    "S": "afgcd", "t": "defg", "U": "bcdef", "V": "bcdef", "u": "cde", "y": "bcdfg", "Y": "bcdfg",
    "=": "dg",
}


def _seg_char(ch):
    for c in (ch, ch.upper(), ch.lower()):
        if c in SEG:
            return SEG[c]
    return ""


def _digit(cr, x, y, w, h, ch, on_col=VFD_ON, off_col=VFD_OFF):
    t = max(2.0, w * 0.17)
    sk = 0.08
    hh = h / 2
    lit = _seg_char(ch)

    def P(px, py):
        return x + px + (h - py) * sk, y + py

    def hseg(px, py, L):
        return [(px, py), (px + t / 2, py - t / 2), (px + L - t / 2, py - t / 2),
                (px + L, py), (px + L - t / 2, py + t / 2), (px + t / 2, py + t / 2)]

    def vseg(px, py, L):
        return [(px, py), (px + t / 2, py + t / 2), (px + t / 2, py + L - t / 2),
                (px, py + L), (px - t / 2, py + L - t / 2), (px - t / 2, py + t / 2)]

    g = 1.0
    segs = {
        "a": hseg(t / 2 + g, t / 2, w - t - 2 * g), "g": hseg(t / 2 + g, hh, w - t - 2 * g),
        "d": hseg(t / 2 + g, h - t / 2, w - t - 2 * g),
        "f": vseg(t / 2, t / 2 + g, hh - t / 2 - 2 * g), "e": vseg(t / 2, hh + g, hh - t / 2 - 2 * g),
        "b": vseg(w - t / 2, t / 2 + g, hh - t / 2 - 2 * g),
        "c": vseg(w - t / 2, hh + g, hh - t / 2 - 2 * g),
    }
    for name, pts in segs.items():
        cr.new_path()
        for i, (px, py) in enumerate(pts):
            X, Y = P(px, py)
            (cr.move_to if i == 0 else cr.line_to)(X, Y)
        cr.close_path()
        _rgb(cr, on_col if name in lit else off_col)
        cr.fill()


def _digits(cr, text, x, y, w, h, pitch, on_col=None, off_col=None):
    for i, c in enumerate(text):
        _digit(cr, x + i * pitch, y, w, h, c, on_col or VFD_ON, off_col or VFD_OFF)


# ----------------------------------------------------------------- Bauteile
def _btn(cr, x, y, w, h, pressed, style="key", label=None, size=13, led=None, r=7):
    pal = {
        "key": ((0.99, 0.99, 0.99), (0.90, 0.90, 0.91), (0.70, 0.70, 0.72), (0.18, 0.18, 0.20)),
        "small": ((0.95, 0.95, 0.96), (0.87, 0.87, 0.88), (0.68, 0.68, 0.70), (0.30, 0.30, 0.32)),
        "amber": ((1.0, 0.66, 0.24), (0.95, 0.52, 0.08), (0.55, 0.28, 0.03), (0.16, 0.10, 0.04)),
    }[style]
    top, bot, side, fg = pal
    oy = 2.0 if pressed else 0.0
    _rrect(cr, x, y + 3, w, h, r)
    _rgb(cr, (0, 0, 0), 0.16)
    cr.fill()
    _rrect(cr, x, y + oy, w, h - oy + 1, r)
    _rgb(cr, side)
    cr.fill()
    _rrect(cr, x, y + oy, w, h - 3, r)
    cr.set_source(_lin(y, y + h, top, bot))
    cr.fill()
    cr.rectangle(x + r, y + oy + 0.6, w - 2 * r, 1)
    _rgb(cr, (1, 1, 1), 0.6)
    cr.fill()
    if label:
        _text(cr, label, x + w / 2, y + oy + (h - 3) / 2 + size * 0.36, size, fg)
    if led is not None:
        _circle(cr, x + w - 10, y + oy + 10, 3.2)
        _rgb(cr, (1.0, 0.18, 0.1) if led else (0.80, 0.80, 0.81))
        cr.fill()
    return oy


def _icon(cr, kind, cx, cy, color):
    _rgb(cr, color)
    if kind == "prev":
        cr.rectangle(cx - 12, cy - 9, 3, 18)
        cr.fill()
        for dx in (0, 11):
            cr.move_to(cx + 2 + dx, cy - 9); cr.line_to(cx - 8 + dx, cy); cr.line_to(cx + 2 + dx, cy + 9)
            cr.close_path()
            cr.fill()
    elif kind == "next":
        for dx in (0, 11):
            cr.move_to(cx - 13 + dx, cy - 9); cr.line_to(cx - 3 + dx, cy); cr.line_to(cx - 13 + dx, cy + 9)
            cr.close_path()
            cr.fill()
        cr.rectangle(cx + 9, cy - 9, 3, 18)
        cr.fill()
    elif kind == "stop":
        cr.rectangle(cx - 8, cy - 8, 16, 16)
        cr.fill()
    elif kind == "play":
        cr.move_to(cx - 18, cy - 10); cr.line_to(cx - 4, cy); cr.line_to(cx - 18, cy + 10)
        cr.close_path()
        cr.fill()
        cr.rectangle(cx + 4, cy - 10, 4, 20)
        cr.fill()
        cr.rectangle(cx + 12, cy - 10, 4, 20)
        cr.fill()


def _knob(cr, cx, cy, value):
    # Skala
    for i in range(21):
        a = math.radians(225 - 13.5 * i)
        r0, r1 = KNOB_R + 7, KNOB_R + (13 if i % 5 == 0 else 10)
        cr.new_path()
        cr.move_to(cx + math.cos(a) * r0, cy - math.sin(a) * r0)
        cr.line_to(cx + math.cos(a) * r1, cy - math.sin(a) * r1)
        cr.line_to(cx + math.cos(a + 0.015) * r1, cy - math.sin(a + 0.015) * r1)
        cr.line_to(cx + math.cos(a + 0.015) * r0, cy - math.sin(a + 0.015) * r0)
        cr.close_path()
        _rgb(cr, TXT_DIM)
        cr.fill()
    _circle(cr, cx, cy + 4, KNOB_R)
    _rgb(cr, (0, 0, 0), 0.2)
    cr.fill()
    _circle(cr, cx, cy, KNOB_R)
    cr.set_source(_lin(cy - KNOB_R, cy + KNOB_R, (0.96, 0.96, 0.97), (0.78, 0.78, 0.80)))
    cr.fill()
    _circle(cr, cx, cy, KNOB_R - 7)
    g = cairo.RadialGradient(cx - 12, cy - 14, 4, cx, cy, KNOB_R - 7)
    g.add_color_stop_rgb(0, 1.0, 1.0, 1.0)
    g.add_color_stop_rgb(1, 0.90, 0.90, 0.91)
    cr.set_source(g)
    cr.fill()
    a = math.radians(225 - 270 * max(0.0, min(1.0, value)))
    cr.new_path()
    ca, sa = math.cos(a), math.sin(a)
    px, py = -sa, -ca
    r0, r1 = 12, KNOB_R - 10
    cr.move_to(cx + ca * r0 + px * 2, cy - sa * r0 + py * 2)
    cr.line_to(cx + ca * r1 + px * 2, cy - sa * r1 + py * 2)
    cr.line_to(cx + ca * r1 - px * 2, cy - sa * r1 - py * 2)
    cr.line_to(cx + ca * r0 - px * 2, cy - sa * r0 - py * 2)
    cr.close_path()
    _rgb(cr, AMBER)
    cr.fill()


def _fader(cr, value):
    x = FADER_X
    for i in range(9):
        y = FADER_Y1 - i * (FADER_Y1 - FADER_Y0) / 8
        cr.rectangle(x - 30, y - 0.6, 12 if i != 4 else 16, 1.2)
        _rgb(cr, AMBER if i == 4 else TXT_DIM)
        cr.fill()
    _rrect(cr, x - 4, FADER_Y0 - 8, 8, FADER_Y1 - FADER_Y0 + 16, 4)
    _rgb(cr, (0.30, 0.30, 0.32))
    cr.fill()
    cy = FADER_Y1 - max(0.0, min(1.0, value)) * (FADER_Y1 - FADER_Y0)
    _rrect(cr, x - 22, cy - 11, 44, 26, 4)
    _rgb(cr, (0, 0, 0), 0.2)
    cr.fill()
    _rrect(cr, x - 22, cy - 14, 44, 28, 4)
    cr.set_source(_lin(cy - 14, cy + 14, (1.0, 1.0, 1.0), (0.86, 0.86, 0.87)))
    cr.fill()
    cr.rectangle(x - 18, cy - 1, 36, 2)
    _rgb(cr, AMBER)
    cr.fill()


def _disc(cr, st):
    cx, cy = DISC_C
    _circle(cr, cx + 3, cy + 8, DISC_R)
    _rgb(cr, (0, 0, 0), 0.5)
    cr.fill()
    cr.save()
    cr.translate(cx, cy)
    cr.rotate(st.disc_angle)
    # silberne Unterseite / Rand
    _circle(cr, 0, 0, DISC_R)
    g = cairo.RadialGradient(-60, -80, 10, 0, 0, DISC_R)
    g.add_color_stop_rgb(0, 0.86, 0.87, 0.89)
    g.add_color_stop_rgb(0.7, 0.66, 0.67, 0.70)
    g.add_color_stop_rgb(1, 0.78, 0.79, 0.82)
    cr.set_source(g)
    cr.fill()
    # Aufdruck
    _circle(cr, 0, 0, DISC_R - 4)
    cover = getattr(st, "cover", None)
    if cover is not None:
        cr.save()
        cr.clip()
        cw, ch = cover.get_width(), cover.get_height()
        s = 2 * (DISC_R - 4) / min(cw, ch)
        cr.scale(s, s)
        cr.set_source_surface(cover, -cw / 2, -ch / 2)
        cr.paint()
        cr.restore()
    else:
        col = st.disc_color
        _rgb(cr, col)
        cr.fill()
        light = sum(col) > 1.8
        ink = (0.12, 0.12, 0.13) if light else (0.95, 0.94, 0.90)
        for rr in (DISC_R - 22, DISC_R - 27, HUB_R + 24):
            _circle(cr, 0, 0, rr)
            _rgb(cr, ink, 0.4)
            cr.fill()
            _circle(cr, 0, 0, rr - 1.2)
            _rgb(cr, col)
            cr.fill()
        lines = st.disc_lines or []
        if lines:
            _text(cr, lines[0][:22], 0, -128, 22, ink, bold=True)
        for i, ln in enumerate(lines[1:5]):
            _text(cr, ln[:30], 0, -100 + i * 16, 12, ink)
        _text(cr, "thisismade", 0, 150, 18, ink)
        _text(cr, "COMPACT DISC · DIGITAL AUDIO", 0, 170, 9, ink)
        _circle(cr, 150, 0, 6)
        _rgb(cr, AMBER)
        cr.fill()
    # klarer Innenring + Spindel
    _circle(cr, 0, 0, HUB_R)
    _rgb(cr, (0.55, 0.57, 0.60))
    cr.fill()
    _circle(cr, 0, 0, HUB_R - 3)
    _rgb(cr, (0.30, 0.31, 0.33))
    cr.fill()
    _spindle(cr)
    cr.restore()


def _spindle(cr):
    _circle(cr, 0, 0, 30)
    cr.set_source(_lin(-30, 30, (0.80, 0.80, 0.82), (0.45, 0.45, 0.47)))
    cr.fill()
    _circle(cr, 0, 0, 22)
    cr.set_source(_lin(-22, 22, (0.40, 0.40, 0.42), (0.75, 0.75, 0.77)))
    cr.fill()
    for i in range(3):
        a = i * 2 * math.pi / 3 + 0.3
        _circle(cr, math.cos(a) * 14, math.sin(a) * 14, 3.2)
        _rgb(cr, (0.95, 0.95, 0.96))
        cr.fill()
    _circle(cr, 0, 0, 5)
    _rgb(cr, (0.15, 0.15, 0.16))
    cr.fill()


# ----------------------------------------------------------------- Gesamtbild
def draw(cr, st):
    draw_static(cr)
    draw_dynamic(cr, st)


def draw_static(cr):
    _rrect(cr, 0, 10, DEV_W, DEV_H, 18)
    _rgb(cr, (0, 0, 0), 0.22)
    cr.fill()
    _rrect(cr, 0, 0, DEV_W, DEV_H, 18)
    cr.set_source(_lin(0, DEV_H, (0.985, 0.985, 0.98), (0.90, 0.90, 0.90)))
    cr.fill()
    _rrect(cr, 1, 1, DEV_W - 2, DEV_H - 2, 17)
    _rrect(cr, 2, 2.5, DEV_W - 4, DEV_H - 4, 16)
    cr.rectangle(18, 1, DEV_W - 36, 1.2)
    _rgb(cr, (1, 1, 1), 0.9)
    cr.fill()

    _text(cr, "thisismade", 40, 42, 24, (0.12, 0.12, 0.13), align="left", bold=True)
    _text(cr, "CD PLAYER  ·  CDP-2", 184, 41, 12, TXT_DIM, align="left")

    # Plattenteller-Mulde
    cx, cy = DISC_C
    _circle(cr, cx, cy, WELL_R + 3)
    _rgb(cr, (0.80, 0.80, 0.81), 1.0)
    cr.fill()
    _circle(cr, cx, cy, WELL_R)
    g = cairo.RadialGradient(cx, cy - 40, 40, cx, cy, WELL_R)
    g.add_color_stop_rgb(0, 0.10, 0.10, 0.11)
    g.add_color_stop_rgb(1, 0.05, 0.05, 0.055)
    cr.set_source(g)
    cr.fill()
    # Laserschlitten-Schlitz
    cr.save()
    cr.translate(cx, cy)
    cr.rotate(math.radians(135))
    _rrect(cr, 60, -20, 190, 40, 8)
    _rgb(cr, (0.02, 0.02, 0.025))
    cr.fill()
    _circle(cr, 150, 0, 9)
    _rgb(cr, (0.20, 0.22, 0.30))
    cr.fill()
    _circle(cr, 150, 0, 4)
    _rgb(cr, (0.45, 0.50, 0.75))
    cr.fill()
    cr.restore()

    # Display-Rahmen
    x, y, w, h = DISPLAY
    _rrect(cr, x - 6, y - 6, w + 12, h + 12, 12)
    _rgb(cr, (0.80, 0.80, 0.81))
    cr.fill()
    _rrect(cr, x, y, w, h, 7)
    cr.set_source(_lin(y, y + h, (0.045, 0.025, 0.025), (0.07, 0.035, 0.035)))
    cr.fill()

    _text(cr, "VOLUME", KNOB_C[0], KNOB_C[1] + KNOB_R + 26, 11, TXT_DIM)
    _text(cr, "MEMORY", 630, MEM_Y - 10, 11, TXT_DIM, align="left")
    _text(cr, "SHUTTLE", SHUTTLE[0], MEM_Y - 10, 11, TXT_DIM, align="left")
    _text(cr, "TEMPO", FADER_X, FADER_Y0 - 30, 11, TXT_DIM)
    _text(cr, "+", FADER_X + 26, FADER_Y0 + 4, 12, TXT_DIM)
    _text(cr, "−", FADER_X + 26, FADER_Y1 + 4, 12, TXT_DIM)


def draw_dynamic(cr, st):
    P = st.pressed
    on = st.power_on

    # Tasten oben
    for rid, t, x in TOP_BTNS:
        led = (on if rid == "power" else None)
        _btn(cr, x, TOP_Y, TOP_W, TOP_H, rid in P, "small", t, 10, r=5)
        if led is not None:
            _circle(cr, x + 9, TOP_Y + 13, 2.6)
            _rgb(cr, AMBER if led else (0.12, 0.12, 0.13))
            cr.fill()
    _circle(cr, 1146, 31, 3.0)
    _rgb(cr, (0.30, 0.65, 1.0) if (st.bt_led and on) else (0.12, 0.12, 0.13))
    cr.fill()
    _text(cr, "MEDIA", 1156, 35, 9, TXT_DIM, align="left")

    # Disc
    if st.disc_loaded:
        _disc(cr, st)
    else:
        cr.save()
        cr.translate(*DISC_C)
        cr.rotate(st.disc_angle)
        _spindle(cr)
        cr.restore()
        _text(cr, "NO DISC", DISC_C[0], DISC_C[1] + 70, 14, TXT)
        _text(cr, "OPEN = Ordner · FILES = Dateien · oder hierher ziehen",
              DISC_C[0], DISC_C[1] + 92, 11, TXT_DIM)

    # Display
    _display(cr, st)

    # Ziffernblock
    for lab, x, y in KEYS:
        text = {"T": "TIME", "C": "CLR"}.get(lab, lab)
        _btn(cr, x, y, KEY_W, KEY_H, "key_" + lab in P, "key", text, 17 if len(text) == 1 else 11)
    x, y, w, h = ENTER
    _btn(cr, x, y, w, h, "enter" in P, "key", "ENTER", 12)

    _knob(cr, *KNOB_C, st.level_norm)

    # Memory
    for i, (rid, t, x) in enumerate(MEM):
        _btn(cr, x, MEM_Y, MEM_W, MEM_H, rid in P, "key", t, 17, led=st.cue_set[i] and on)

    # Shuttle
    x, y, w, h = SHUTTLE
    _rrect(cr, x, y + 12, w, h - 24, 10)
    _rgb(cr, (0.30, 0.30, 0.32))
    cr.fill()
    _text(cr, "REW", x + 16, y + h + 14, 10, TXT_DIM)
    _text(cr, "FF", x + w - 12, y + h + 14, 10, TXT_DIM)
    cx = x + w / 2 + st.jog * JOG_TRAVEL
    _rrect(cr, cx - 22, y + 4, 44, h - 4, 6)
    _rgb(cr, (0, 0, 0), 0.2)
    cr.fill()
    _rrect(cr, cx - 22, y, 44, h - 4, 6)
    cr.set_source(_lin(y, y + h, (1.0, 1.0, 1.0), (0.86, 0.86, 0.87)))
    cr.fill()
    cr.rectangle(cx - 1.5, y + 6, 3, h - 16)
    _rgb(cr, AMBER)
    cr.fill()

    _fader(cr, st.varispeed_norm)

    # Laufwerk
    for rid, x, w in TRANSPORT:
        style = "amber" if rid == "play" else "key"
        oy = _btn(cr, x, TR_Y, w, TR_H, rid in P, style)
        _icon(cr, rid, x + w / 2, TR_Y + oy + TR_H / 2 - 2,
              (0.16, 0.10, 0.04) if rid == "play" else (0.18, 0.18, 0.20))

    leds = {"vs_display": st.stretch, "repeat": st.repeat > 0, "shuffle": st.shuffle, "eject": None}
    for rid, t, x in SMALL:
        _btn(cr, x, SMALL_Y, SMALL_W, SMALL_H, rid in P, "small", t, 10,
             led=(leds[rid] and on) if leds[rid] is not None else None, r=5)

    if not on:
        _rrect(cr, 0, 0, DEV_W, DEV_H, 18)
        _rgb(cr, (0, 0, 0), 0.12)
        cr.fill()


def _display(cr, st, on_col=None, off_col=None, hot_on=(1.0, 0.62, 0.14), hot_off=(0.20, 0.11, 0.03)):
    on_col = on_col or VFD_ON
    off_col = off_col or VFD_OFF
    x, y, w, h = DISPLAY
    on = st.power_on
    L = (lambda c: on_col if (c and on) else off_col)
    dw, dh, pitch = 26, 46, 34
    if not on:
        main = " " * 12
    else:
        main = (st.main_text + " " * 12)[:12]
    if on and getattr(st, "msg_mode", False):
        _digits(cr, main, x + 18, y + 38, dw, dh, pitch, on_col, off_col)
    else:
        _text(cr, "TRACK", x + 18, y + 26, 10, L(True), align="left")
        _text(cr, "TOTAL", x + 136, y + 26, 10, L(True), align="left")
        _text(cr, "TIME", x + 254, y + 26, 10, L(True), align="left")
        _digits(cr, main[0:3], x + 18, y + 38, dw, dh, pitch, on_col, off_col)
        _digits(cr, main[3:6], x + 136, y + 38, dw, dh, pitch, on_col, off_col)
        _digits(cr, main[6:9], x + 254, y + 38, dw, dh, pitch, on_col, off_col)
        for dy in (14, 32):
            _circle(cr, x + 362 + (46 - dy) * 0.08, y + 38 + dy, 3)
            _rgb(cr, L(True))
            cr.fill()
        _digits(cr, main[10:12], x + 372, y + 38, dw, dh, pitch, on_col, off_col)
    # Titel (Laufschrift bei langen Namen) und Auflösung
    if on and not getattr(st, "msg_mode", False):
        _title_line(cr, st, x, y, w, L(True))
    # Anzeigen rechts
    ind = [("REPEAT" if st.repeat != 2 else "REPEAT 1", st.repeat > 0), ("SHUFFLE", st.shuffle),
           ("KEY LOCK", st.stretch), ("PAUSE", st.paused), ("REMAIN", st.remain)]
    for i, (t, a) in enumerate(ind):
        _text(cr, t, x + w - 14, y + 26 + i * 15, 10, L(a), align="right")
    # untere Zeile: Tempo, Lautstärke, Pegel
    by = y + 126
    _text(cr, "TEMPO", x + 18, by - 6, 10, L(True), align="left")
    _digits(cr, st.vs_text if on else "   ", x + 18, by, 15, 26, 20, on_col, off_col)
    _text(cr, "%", x + 84, by + 25, 12, L(True), align="left")
    _text(cr, "VOL", x + 110, by - 6, 10, L(True), align="left")
    _digits(cr, st.lv_text if on else "   ", x + 110, by, 15, 26, 20, on_col, off_col)
    mx = x + 200
    n = 30
    for row, val in enumerate((st.vu_l, st.vu_r)):
        yy = by + 2 + row * 15
        _text(cr, "LR"[row], mx, yy + 9, 10, L(True), align="left")
        lit = int(round(max(0.0, min(1.0, val if on else 0)) * n))
        pk = int(round(max(0.0, min(1.0, st.vu_peaks[row] if on else 0)) * n))
        for i in range(n):
            cr.rectangle(mx + 14 + i * 10.5, yy, 8, 10)
            hot = i >= n - 5
            col = hot_on if hot else on_col
            off = hot_off if hot else off_col
            _rgb(cr, col if (i < lit or (pk and i == pk - 1)) else off)
            cr.fill()


def _title_line(cr, st, x, y, w, col):
    title = getattr(st, "title", "") or ""
    res = getattr(st, "resolution", "") or ""
    ty = y + 101
    cr.select_font_face(FONT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    cr.set_font_size(11)
    rw = cr.text_extents(res).x_advance if res else 0
    if res:
        _rgb(cr, col)
        cr.move_to(x + w - 14 - rw, ty)
        cr.show_text(res)
    if not title:
        return
    box_x, box_w = x + 18, w - 32 - rw - (16 if res else 0)
    tw = cr.text_extents(title).x_advance
    cr.save()
    cr.rectangle(box_x, ty - 12, box_w, 16)
    cr.clip()
    _rgb(cr, col)
    if tw <= box_w:
        cr.move_to(box_x, ty)
        cr.show_text(title)
    else:
        gap = 50
        off = (time.monotonic() * 28) % (tw + gap)
        for k in (0, 1):
            cr.move_to(box_x - off + k * (tw + gap), ty)
            cr.show_text(title)
    cr.restore()
