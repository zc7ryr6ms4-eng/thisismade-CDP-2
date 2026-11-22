"""Gerätefront im Klemmbaustein-Stil: weiße Steine, rote Anzeigen und Akzente.

Gleiches Layout und gleiche Klickflächen wie face.py – nur anders gezeichnet.
"""
import math

import cairo

from .face import (CANVAS_H, CANVAS_W, DEV_H, DEV_W, DISC_C, DISC_R, DISPLAY, ENTER, FADER_X,  # noqa: F401
                   FADER_Y0, FADER_Y1, HUB_R, JOG_TRAVEL, KEY_H, KEY_W, KEYS, KNOB_C, KNOB_R, MARGIN_BOTTOM,
                   MARGIN_TOP, MARGIN_X, MEM, MEM_H, MEM_W, MEM_Y, SHUTTLE, SMALL, SMALL_H, SMALL_W, SMALL_Y,
                   TOP_BTNS, TOP_H, TOP_W, TOP_Y, TR_H, TR_Y, TRANSPORT, WELL_R, _circle, _display, _icon,
                   _rgb, _rrect, _text, hit)

NAME = "brick"

# Farbpalette (klassische Spielzeugstein-Farben)
RED = (0.79, 0.10, 0.10)
YELLOW = (0.98, 0.79, 0.05)
BLUE = (0.00, 0.33, 0.75)
GREEN = (0.00, 0.57, 0.26)
ORANGE = (1.00, 0.50, 0.00)
WHITE = (0.965, 0.965, 0.955)
BASE = (0.93, 0.93, 0.92)          # Grundplatte
WELL = (0.84, 0.84, 0.85)          # runde Platte unter der Disc
LABEL = (0.86, 0.86, 0.87)         # Beschriftungen
BLACK = (0.13, 0.13, 0.14)
DARK_GREY = (0.39, 0.40, 0.42)
LIGHT_GREY = (0.63, 0.65, 0.68)
TAN = (0.89, 0.80, 0.62)

PITCH = 30          # Noppenraster
STUD_R = 9.0
SIDE = 7.0          # sichtbare Steinflanke


def _shade(c, f):
    return tuple(max(0.0, min(1.0, v * f)) for v in c)


def _lighten(c, a):
    return tuple(min(1.0, v + (1 - v) * a) for v in c)


def _ink(c):
    """Lesbare Schriftfarbe auf Farbe c."""
    return BLACK if (0.3 * c[0] + 0.59 * c[1] + 0.11 * c[2]) > 0.55 else WHITE


# ----------------------------------------------------------------- Grundformen
# Modern und klar: flache Oberflächen, feine Kontur, kurze Flanke, weicher Schatten.
EDGE = 0.80          # Konturfarbe = Grundfarbe * EDGE
SIDE_F = 0.82        # Flankenfarbe


def _outline(cr, color, w=1.0):
    _rgb(cr, _shade(color, EDGE))
    cr.set_line_width(w)
    cr.stroke()


def stud(cr, cx, cy, color, r=STUD_R, flat=False):
    """Flache Noppe: weicher Schatten, kurze Flanke, glatter Deckel mit feiner Kontur."""
    h = 0 if flat else 3.0
    _circle(cr, cx + 0.8, cy + h + 1.8, r)
    _rgb(cr, (0, 0, 0), 0.10)
    cr.fill()
    if h:
        _circle(cr, cx, cy + h, r)
        _rgb(cr, _shade(color, SIDE_F))
        cr.fill()
        cr.rectangle(cx - r, cy, 2 * r, h)
        cr.fill()
    _circle(cr, cx, cy, r)
    _rgb(cr, _lighten(color, 0.08))
    cr.fill_preserve()
    _outline(cr, color, 0.9)
    cr.new_path()
    cr.arc(cx, cy, r - 2.2, math.radians(200), math.radians(290))
    _rgb(cr, (1, 1, 1), 0.55)
    cr.set_line_width(1.2)
    cr.stroke()


def _studs_in(cr, x, y, w, h, color, r=STUD_R, pitch=PITCH):
    nx = max(1, int(w // pitch))
    ny = max(1, int(h // pitch))
    ox = x + (w - (nx - 1) * pitch) / 2
    oy = y + (h - (ny - 1) * pitch) / 2 - 1.5
    for j in range(ny):
        for i in range(nx):
            stud(cr, ox + i * pitch, oy + j * pitch, color, r)


def block(cr, x, y, w, h, color, pressed=False, r=4, studs=False, stud_r=STUD_R, side=SIDE):
    """Stein bzw. Fliese: flache Oberseite, feine Kontur, kurze Flanke unten."""
    side = min(side, 5.0)
    oy = side * 0.7 if pressed else 0.0
    s = side - oy
    _rrect(cr, x + 1, y + s + 2.5, w, h, r)
    _rgb(cr, (0, 0, 0), 0.10)
    cr.fill()
    _rrect(cr, x, y + oy, w, h + s, r)
    _rgb(cr, _shade(color, SIDE_F))
    cr.fill()
    _rrect(cr, x, y + oy, w, h, r)
    _rgb(cr, _lighten(color, 0.06))
    cr.fill_preserve()
    _outline(cr, color, 1.0)
    if studs:
        _studs_in(cr, x, y + oy, w, h, color, stud_r)
    return oy


def round_tile(cr, cx, cy, r, color, pressed=False):
    oy = 2.5 if pressed else 0.0
    s = 4.0 - oy
    _circle(cr, cx + 1, cy + s + 2.5, r)
    _rgb(cr, (0, 0, 0), 0.10)
    cr.fill()
    _circle(cr, cx, cy + oy + s, r)
    _rgb(cr, _shade(color, SIDE_F))
    cr.fill()
    cr.rectangle(cx - r, cy + oy, 2 * r, s)
    cr.fill()
    _circle(cr, cx, cy + oy, r)
    _rgb(cr, _lighten(color, 0.06))
    cr.fill_preserve()
    _outline(cr, color, 1.0)
    return oy


def trans_led(cr, cx, cy, on, color=(1.0, 0.15, 0.10), r=6):
    """Runde Leuchte: klar, ohne Glanzeffekte."""
    if on:
        _circle(cr, cx, cy, r + 3.5)
        _rgb(cr, color, 0.18)
        cr.fill()
    _circle(cr, cx, cy, r + 1.2)
    _rgb(cr, (0, 0, 0), 0.12)
    cr.fill()
    _circle(cr, cx, cy, r)
    _rgb(cr, color if on else (0.80, 0.80, 0.81))
    cr.fill()


# ----------------------------------------------------------------- Gesamtbild
def draw(cr, st):
    draw_static(cr)
    draw_dynamic(cr, st)


def draw_static(cr):
    # Grundplatte
    _rrect(cr, 3, 12, DEV_W, DEV_H, 10)
    _rgb(cr, (0, 0, 0), 0.30)
    cr.fill()
    _rrect(cr, 0, 0, DEV_W, DEV_H + 8, 10)
    _rgb(cr, _shade(BASE, 0.78))
    cr.fill()
    _rrect(cr, 0, 0, DEV_W, DEV_H, 10)
    _rgb(cr, BASE)
    cr.fill()
    # feine Fuge zwischen Laufwerk und Bedienfeld
    cr.rectangle(600, 14, 1, DEV_H - 28)
    _rgb(cr, _shade(BASE, 0.88))
    cr.fill()
    cr.rectangle(601, 14, 1, DEV_H - 28)
    _rgb(cr, (1, 1, 1), 0.8)
    cr.fill()

    # Name direkt aufgedruckt
    _text(cr, "thisismade", 34, 46, 27, BLACK, align="left", bold=True)
    _text(cr, "CD PLAYER  ·  CDP-2", 200, 45, 12, DARK_GREY, align="left")

    # runde Platte für die Disc
    cx, cy = DISC_C
    _circle(cr, cx + 1, cy + 6, WELL_R)
    _rgb(cr, (0, 0, 0), 0.08)
    cr.fill()
    _circle(cr, cx, cy + 4, WELL_R)
    _rgb(cr, _shade(WELL, SIDE_F))
    cr.fill()
    _circle(cr, cx, cy, WELL_R)
    _rgb(cr, WELL)
    cr.fill_preserve()
    _outline(cr, WELL)
    _circle(cr, cx, cy, WELL_R - 14)
    _outline(cr, WELL, 0.8)

    # Display-Rahmen (schwarzer Stein mit Noppenreihe)
    x, y, w, h = DISPLAY
    block(cr, x - 10, y - 34, w + 20, h + 44, BLACK, r=5)
    n = int((w + 20) // PITCH)
    for i in range(n):
        stud(cr, x - 10 + (w + 20 - (n - 1) * PITCH) / 2 + i * PITCH, y - 18, BLACK, 7.5)
    _rrect(cr, x, y, w, h, 4)
    g = cairo.LinearGradient(0, y, 0, y + h)
    g.add_color_stop_rgb(0, 0.05, 0.02, 0.02)
    g.add_color_stop_rgb(1, 0.08, 0.03, 0.03)
    cr.set_source(g)
    cr.fill()

    # Beschriftungen, direkt aufgedruckt
    for t, tx, ty in (("VOLUME", KNOB_C[0], KNOB_C[1] + KNOB_R + 30), ("MEMORY", 630, MEM_Y - 12),
                      ("SHUTTLE", SHUTTLE[0], MEM_Y - 12), ("TEMPO", FADER_X, FADER_Y0 - 22)):
        _text(cr, t, tx, ty, 11, DARK_GREY, align="left" if t in ("MEMORY", "SHUTTLE") else "center", bold=True)


def draw_dynamic(cr, st):
    P = st.pressed
    on = st.power_on

    # Tasten oben (schwarze Fliesen, Power rot)
    for rid, t, x in TOP_BTNS:
        col = RED if rid == "power" else WHITE
        oy = block(cr, x, TOP_Y, TOP_W, TOP_H, col, rid in P, r=3, side=5)
        _text(cr, t, x + TOP_W / 2, TOP_Y + oy + 17, 10, _ink(col), bold=True)
    trans_led(cr, 1146, 31, st.bt_led and on, (0.2, 0.55, 1.0), 5)

    # Disc
    if st.disc_loaded:
        _disc(cr, st)
    else:
        cr.save()
        cr.translate(*DISC_C)
        cr.rotate(st.disc_angle)
        _hub(cr)
        cr.restore()
        _text(cr, "NO DISC", DISC_C[0], DISC_C[1] + 82, 15, BLACK, bold=True)
        _text(cr, "OPEN = Ordner · FILES = Dateien · oder hierher ziehen",
              DISC_C[0], DISC_C[1] + 104, 11, DARK_GREY)

    # Display-Inhalt (gleiche Anzeige wie klassisch)
    _display(cr, st)

    # Ziffernblock: runde Fliesen
    for lab, x, y in KEYS:
        kid = "key_" + lab
        col = WHITE
        r = min(KEY_W, KEY_H) / 2
        cx, cy = x + KEY_W / 2, y + KEY_H / 2 - 2
        oy = round_tile(cr, cx, cy, r, col, kid in P)
        text = {"T": "TIME", "C": "CLR"}.get(lab, lab)
        _text(cr, text, cx, cy + oy + (7 if len(text) == 1 else 4), 20 if len(text) == 1 else 11,
              RED if lab in "TC" else BLACK, bold=True)
    x, y, w, h = ENTER
    oy = block(cr, x, y, w, h - 6, RED, "enter" in P, studs=False)
    stud(cr, x + w / 2 - 15, y + oy + 18, RED, 8)
    stud(cr, x + w / 2 + 15, y + oy + 18, RED, 8)
    _text(cr, "ENTER", x + w / 2, y + oy + 64, 13, WHITE, bold=True)

    # Lautstärke: runde blaue Platte mit Noppen, dreht sich mit dem Wert
    _knob(cr, st.level_norm)

    # Memory A/B/C: orange Steine mit Leuchte
    for i, (rid, t, x) in enumerate(MEM):
        oy = block(cr, x, MEM_Y, MEM_W, MEM_H - 4, WHITE, rid in P)
        _text(cr, t, x + 26, MEM_Y + oy + 29, 22, BLACK, bold=True)
        trans_led(cr, x + MEM_W - 16, MEM_Y + oy + 19, st.cue_set[i] and on)

    # Shuttle: Schiene + gelber 1x2-Stein
    x, y, w, h = SHUTTLE
    block(cr, x, y + 12, w, h - 24, LIGHT_GREY, r=3, side=3)
    _text(cr, "REW", x + 16, y + h + 14, 10, BLACK, bold=True)
    _text(cr, "FF", x + w - 12, y + h + 14, 10, BLACK, bold=True)
    jx = x + w / 2 + st.jog * JOG_TRAVEL
    block(cr, jx - 26, y, 52, h - 6, RED, "jog" in P, r=3, studs=False)
    stud(cr, jx - 12, y + 17, RED, 8)
    stud(cr, jx + 12, y + 17, RED, 8)

    # Tempo-Fader: Schiene + roter 1x2-Stein
    _fader(cr, st.varispeed_norm)

    # Laufwerkstasten: große Steine mit aufgedrucktem Symbol
    colors = {"prev": WHITE, "next": WHITE, "stop": WHITE, "play": RED}
    for rid, x, w in TRANSPORT:
        col = colors[rid]
        oy = block(cr, x, TR_Y, w, TR_H - 6, col, rid in P)
        for k in range(int(w // PITCH)):
            stud(cr, x + (w - (int(w // PITCH) - 1) * PITCH) / 2 + k * PITCH, TR_Y + oy + 16, col, 8)
        _rrect(cr, x + 12, TR_Y + oy + 32, w - 24, 34, 3)
        _rgb(cr, LABEL if col == WHITE else WHITE)
        cr.fill()
        _icon(cr, rid, x + w / 2, TR_Y + oy + 49, RED if col == WHITE else BLACK)

    # kleine Tasten: weiße Fliesen mit Leuchte
    leds = {"vs_display": st.stretch, "repeat": st.repeat > 0, "shuffle": st.shuffle, "eject": None}
    for rid, t, x in SMALL:
        oy = block(cr, x, SMALL_Y, SMALL_W, SMALL_H - 4, WHITE, rid in P, r=3, side=5)
        _text(cr, t, x + (SMALL_W - 14) / 2, SMALL_Y + oy + 20, 10, BLACK, bold=True)
        if leds[rid] is not None:
            trans_led(cr, x + SMALL_W - 13, SMALL_Y + oy + 15, leds[rid] and on, r=5)

    if not on:
        _rrect(cr, 0, 0, DEV_W, DEV_H, 10)
        _rgb(cr, (0, 0, 0), 0.18)
        cr.fill()


def _hub(cr):
    """Runder 2x2-Stein als Spindel."""
    _circle(cr, 1, 6, 44)
    _rgb(cr, (0, 0, 0), 0.12)
    cr.fill()
    _circle(cr, 0, 4, 44)
    _rgb(cr, _shade(RED, SIDE_F))
    cr.fill()
    _circle(cr, 0, 0, 44)
    _rgb(cr, RED)
    cr.fill_preserve()
    _outline(cr, RED)
    for dx, dy in ((-14, -14), (14, -14), (-14, 14), (14, 14)):
        stud(cr, dx, dy, RED, 9)


def _disc(cr, st):
    cx, cy = DISC_C
    _circle(cr, cx + 2, cy + 8, DISC_R)
    _rgb(cr, (0, 0, 0), 0.12)
    cr.fill()
    cr.save()
    cr.translate(cx, cy)
    cr.rotate(st.disc_angle)
    col = WHITE
    # Flanke der runden Platte
    _circle(cr, 0, 4, DISC_R)
    _rgb(cr, _shade(col, SIDE_F))
    cr.fill()
    _circle(cr, 0, 0, DISC_R)
    _rgb(cr, col)
    cr.fill_preserve()
    _outline(cr, col)
    cover = getattr(st, "cover", None)
    inner = DISC_R - 40
    if cover is not None:
        cr.save()
        _circle(cr, 0, 0, inner)
        cr.clip()
        cw, ch = cover.get_width(), cover.get_height()
        s = 2 * inner / min(cw, ch)
        cr.scale(s, s)
        cr.set_source_surface(cover, -cw / 2, -ch / 2)
        cr.paint()
        cr.restore()
    else:
        ink = _ink(col)
        lines = st.disc_lines or []
        if lines:
            _text(cr, lines[0][:20], 0, -118, 22, ink, bold=True)
        for i, ln in enumerate(lines[1:5]):
            _text(cr, ln[:28], 0, -92 + i * 16, 12, ink, bold=True)
        _text(cr, "thisismade", 0, 140, 18, ink, bold=True)
    # Noppenring am Rand
    _circle(cr, 0, 0, DISC_R - 34)
    _outline(cr, col, 0.8)
    n = 16
    for i in range(n):
        a = 2 * math.pi * i / n
        stud(cr, math.cos(a) * (DISC_R - 17), math.sin(a) * (DISC_R - 17), col, 7.5)
    _hub(cr)
    cr.restore()


def _knob(cr, value):
    cx, cy = KNOB_C
    a = math.radians(225 - 270 * max(0.0, min(1.0, value)))
    # Skala aus kleinen Fliesen
    for i in range(11):
        t = math.radians(225 - 27 * i)
        px, py = cx + math.cos(t) * (KNOB_R + 12), cy - math.sin(t) * (KNOB_R + 12)
        _circle(cr, px, py, 3)
        _rgb(cr, RED if i * 0.1 <= value + 1e-6 else LIGHT_GREY)
        cr.fill()
    round_tile(cr, cx, cy, KNOB_R, WHITE)
    cr.save()
    cr.translate(cx, cy)
    cr.rotate(-a + math.pi / 2)
    for dx, dy in ((-15, -15), (15, -15), (-15, 15), (15, 15)):
        stud(cr, dx, dy, WHITE, 8)
    _rrect(cr, -4, -KNOB_R + 4, 8, 18, 2)
    _rgb(cr, RED)
    cr.fill()
    cr.restore()


def _fader(cr, value):
    x = FADER_X
    for i in range(9):
        y = FADER_Y1 - i * (FADER_Y1 - FADER_Y0) / 8
        cr.rectangle(x - 34, y - 1, 14 if i != 4 else 18, 2)
        _rgb(cr, RED if i == 4 else LIGHT_GREY)
        cr.fill()
    block(cr, x - 6, FADER_Y0 - 10, 12, FADER_Y1 - FADER_Y0 + 20, LIGHT_GREY, r=3, side=3)
    cy = FADER_Y1 - max(0.0, min(1.0, value)) * (FADER_Y1 - FADER_Y0)
    block(cr, x - 26, cy - 15, 52, 26, RED, r=3, side=5)
    stud(cr, x - 12, cy - 3, RED, 8)
    stud(cr, x + 12, cy - 3, RED, 8)
