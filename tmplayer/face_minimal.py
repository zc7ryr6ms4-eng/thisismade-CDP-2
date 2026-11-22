"""Gerätefront im minimalistischen Industrie-Stil: Weiß, Orange, feine Linien.

Flache Flächen, Punktraster, kleine technische Beschriftungen mit Nummern,
runde Tasten. Gleiches Layout und gleiche Klickflächen wie face.py.
"""
import math

import cairo

from .face import (CANVAS_H, CANVAS_W, DEV_H, DEV_W, DISC_C, DISC_R, DISPLAY, ENTER, FADER_X,  # noqa: F401
                   FADER_Y0, FADER_Y1, HUB_R, JOG_TRAVEL, KEY_H, KEY_W, KEYS, KNOB_C, KNOB_R, MARGIN_BOTTOM,
                   MARGIN_TOP, MARGIN_X, MEM, MEM_H, MEM_W, MEM_Y, SHUTTLE, SMALL, SMALL_H, SMALL_W, SMALL_Y,
                   TOP_BTNS, TOP_H, TOP_W, TOP_Y, TR_H, TR_Y, TRANSPORT, WELL_R, _circle, _display, _icon,
                   _rgb, _rrect, _text, hit)

NAME = "minimal"

BODY = (0.955, 0.955, 0.95)
PANEL = (0.92, 0.92, 0.915)
LINE = (0.74, 0.74, 0.75)
DOT = (0.80, 0.80, 0.81)
TXT = (0.12, 0.12, 0.13)
TXT_DIM = (0.50, 0.50, 0.52)
KEY = (0.985, 0.985, 0.98)
KEY_HI = (0.90, 0.90, 0.90)
ORANGE = (1.0, 0.40, 0.0)
ORANGE_DIM = (0.86, 0.80, 0.75)
SEG_ON = (1.0, 0.13, 0.08)
SEG_OFF = (0.20, 0.04, 0.035)
MONO = "monospace"


def _mono(cr, s, x, y, size, color=TXT_DIM, align="left"):
    cr.select_font_face(MONO, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
    cr.set_font_size(size)
    adv = cr.text_extents(s).x_advance
    if align == "center":
        x -= adv / 2
    elif align == "right":
        x -= adv
    _rgb(cr, color)
    cr.move_to(x, y)
    cr.show_text(s)


def _stroke(cr, color, w=1.0, a=1.0):
    _rgb(cr, color, a)
    cr.set_line_width(w)
    cr.stroke()


def _line(cr, x0, y0, x1, y1, color=LINE, w=1.0):
    cr.new_path()
    cr.move_to(x0, y0)
    cr.line_to(x1, y1)
    _stroke(cr, color, w)


def _round_key(cr, cx, cy, r, pressed, fill=KEY, ring=LINE, active=False):
    """Flache runde Taste; gedrückt bzw. aktiv = orange."""
    _circle(cr, cx, cy, r)
    _rgb(cr, ORANGE if (pressed or active) else fill)
    cr.fill_preserve()
    _stroke(cr, ORANGE if (pressed or active) else ring, 1.0)


def _square_key(cr, x, y, w, h, pressed, fill=KEY, r=6, active=False):
    _rrect(cr, x, y, w, h, r)
    _rgb(cr, ORANGE if (pressed or active) else fill)
    cr.fill_preserve()
    _stroke(cr, ORANGE if (pressed or active) else LINE, 1.0)


def _led(cr, x, y, on):
    cr.rectangle(x - 3, y - 3, 6, 6)
    _rgb(cr, ORANGE if on else ORANGE_DIM)
    cr.fill()


# ----------------------------------------------------------------- Gesamtbild
def draw(cr, st):
    draw_static(cr)
    draw_dynamic(cr, st)


def draw_static(cr):
    # Gehäuse: eine flache schwarze Platte
    _rrect(cr, 0, 6, DEV_W, DEV_H, 14)
    _rgb(cr, (0, 0, 0), 0.18)
    cr.fill()
    _rrect(cr, 0, 0, DEV_W, DEV_H, 14)
    _rgb(cr, BODY)
    cr.fill_preserve()
    _stroke(cr, (0.80, 0.80, 0.81), 1.2)

    # Punktraster auf der linken Hälfte
    for j in range(13, int(DEV_H) - 8, 16):
        for i in range(13, 600, 16):
            if (i - DISC_C[0]) ** 2 + (j - DISC_C[1]) ** 2 < (WELL_R + 10) ** 2:
                continue
            _circle(cr, i, j, 1.1)
            _rgb(cr, DOT)
            cr.fill()

    # Trennlinie und Raster-Linien des Bedienfelds
    _line(cr, 610, 14, 610, DEV_H - 14)
    _line(cr, 620, 255, DEV_W - 14, 255)
    _line(cr, 620, 392, DEV_W - 14, 392)
    _line(cr, 620, 578, 1075, 578)
    _line(cr, 1075, 255, 1075, DEV_H - 14)

    # Name und Modell
    _text(cr, "thisismade", 30, 44, 24, TXT, align="left", bold=True)
    _mono(cr, "CDP-2 / COMPACT DISC PLAYER", 31, 62, 10, TXT_DIM)
    _rrect(cr, 520, 34, 54, 14, 7)
    _stroke(cr, ORANGE, 1.0)
    _mono(cr, "AUDIO", 547, 45, 9, ORANGE, align="center")

    # Teller: flache Mulde mit Rillen
    cx, cy = DISC_C
    _circle(cr, cx, cy, WELL_R)
    _rgb(cr, (0.90, 0.90, 0.895))
    cr.fill_preserve()
    _stroke(cr, LINE, 1.0)
    for rr in range(80, int(WELL_R) - 6, 18):
        _circle(cr, cx, cy, rr)
        _stroke(cr, (0.84, 0.84, 0.84), 1.0)
    for k in range(12):
        a = 2 * math.pi * k / 12
        _line(cr, cx + math.cos(a) * (WELL_R - 10), cy + math.sin(a) * (WELL_R - 10),
              cx + math.cos(a) * (WELL_R - 2), cy + math.sin(a) * (WELL_R - 2), TXT_DIM, 1.0)

    # Display
    x, y, w, h = DISPLAY
    _rrect(cr, x - 4, y - 4, w + 8, h + 8, 8)
    _rgb(cr, (0.06, 0.05, 0.045))
    cr.fill_preserve()
    _stroke(cr, (0.55, 0.55, 0.56), 1.0)

    # Nummerierte Beschriftungen
    for t, tx, ty in (("01  NUMBER", 630, 266), ("02  VOLUME", 1086, 268), ("03  MEMORY", 630, 406),
                      ("04  SHUTTLE", 890, 406), ("05  TRANSPORT", 630, 476), ("06  TEMPO", 1086, 406),
                      ("07  MODE", 630, 588)):
        _mono(cr, t, tx, ty, 9, TXT_DIM)


def draw_dynamic(cr, st):
    P = st.pressed
    on = st.power_on

    # obere Textknöpfe
    for rid, t, x in TOP_BTNS:
        pr = rid in P
        _rrect(cr, x, TOP_Y, TOP_W, TOP_H - 2, 12)
        _rgb(cr, ORANGE if pr else BODY)
        cr.fill_preserve()
        _stroke(cr, ORANGE if (pr or rid == "power") else LINE, 1.0)
        _mono(cr, t.lower(), x + TOP_W / 2, TOP_Y + 16, 10, BODY if pr else (ORANGE if rid == "power" else TXT), "center")
    _led(cr, 1146, 31, st.bt_led and on)
    _mono(cr, "mpris", 1155, 35, 8, TXT_DIM)

    # Disc
    if st.disc_loaded:
        _disc(cr, st)
    else:
        cr.save()
        cr.translate(*DISC_C)
        cr.rotate(st.disc_angle)
        _spindle(cr)
        cr.restore()
        _mono(cr, "no disc", DISC_C[0], DISC_C[1] + 70, 13, TXT, "center")
        _mono(cr, "open / files / drop", DISC_C[0], DISC_C[1] + 90, 10, TXT_DIM, "center")

    _display(cr, st, SEG_ON, SEG_OFF, (1.0, 0.62, 0.14), (0.20, 0.11, 0.03))

    # Ziffernblock: runde Tasten
    for lab, x, y in KEYS:
        kid = "key_" + lab
        cx, cy = x + KEY_W / 2, y + KEY_H / 2 + 6
        pr = kid in P
        _round_key(cr, cx, cy, 19, pr, KEY_HI if lab in "TC" else KEY)
        text = {"T": "time", "C": "clr"}.get(lab, lab)
        _mono(cr, text, cx, cy + (5 if len(text) == 1 else 3.5), 15 if len(text) == 1 else 10,
              BODY if pr else TXT, "center")
    x, y, w, h = ENTER
    _square_key(cr, x, y + 12, w, h - 14, "enter" in P, KEY_HI, r=10)
    _mono(cr, "enter", x + w / 2, y + 12 + (h - 14) / 2 + 4, 11, BODY if "enter" in P else ORANGE, "center")

    _knob(cr, st.level_norm)

    # Memory A/B/C
    for i, (rid, t, x) in enumerate(MEM):
        pr = rid in P
        _square_key(cr, x, MEM_Y + 2, MEM_W, MEM_H - 6, pr, r=8)
        _mono(cr, t.lower(), x + 16, MEM_Y + 28, 15, BODY if pr else TXT)
        _led(cr, x + MEM_W - 14, MEM_Y + 19, st.cue_set[i] and on)

    # Shuttle: Linie mit orangem Schieber
    x, y, w, h = SHUTTLE
    cy = y + h / 2 + 2
    _line(cr, x, cy, x + w, cy, LINE, 2.0)
    for k in range(-3, 4):
        _line(cr, x + w / 2 + k * w / 7, cy - 6, x + w / 2 + k * w / 7, cy + 6, TXT_DIM if k else ORANGE, 1.0)
    _mono(cr, "rew", x, y + h + 12, 9, TXT_DIM)
    _mono(cr, "ff", x + w, y + h + 12, 9, TXT_DIM, "right")
    jx = x + w / 2 + st.jog * JOG_TRAVEL
    cr.rectangle(jx - 10, cy - 12, 20, 24)
    _rgb(cr, ORANGE)
    cr.fill()

    _fader(cr, st.varispeed_norm)

    # Laufwerk
    for rid, x, w in TRANSPORT:
        pr = rid in P
        play = rid == "play"
        _square_key(cr, x, TR_Y + 6, w, TR_H - 12, pr, ORANGE if play else KEY, r=12)
        col = BODY if (pr or play) else TXT
        _icon(cr, rid, x + w / 2, TR_Y + TR_H / 2, col)

    # Modus-Tasten
    leds = {"vs_display": st.stretch, "repeat": st.repeat > 0, "shuffle": st.shuffle, "eject": None}
    for rid, t, x in SMALL:
        pr = rid in P
        _rrect(cr, x, SMALL_Y + 12, SMALL_W, SMALL_H - 8, 13)
        _rgb(cr, ORANGE if pr else BODY)
        cr.fill_preserve()
        _stroke(cr, ORANGE if pr else LINE, 1.0)
        _mono(cr, t.lower(), x + SMALL_W / 2 - (6 if leds[rid] is not None else 0), SMALL_Y + 29, 9,
              BODY if pr else TXT, "center")
        if leds[rid] is not None:
            _led(cr, x + SMALL_W - 12, SMALL_Y + 25, leds[rid] and on)

    if not on:
        _rrect(cr, 0, 0, DEV_W, DEV_H, 14)
        _rgb(cr, (0, 0, 0), 0.12)
        cr.fill()


def _spindle(cr):
    _circle(cr, 0, 0, 26)
    _rgb(cr, (0.86, 0.86, 0.86))
    cr.fill_preserve()
    _stroke(cr, LINE, 1.0)
    _circle(cr, 0, 0, 7)
    _rgb(cr, ORANGE)
    cr.fill()


def _disc(cr, st):
    cx, cy = DISC_C
    cr.save()
    cr.translate(cx, cy)
    cr.rotate(st.disc_angle)
    _circle(cr, 0, 2, DISC_R)
    _rgb(cr, (0, 0, 0), 0.10)
    cr.fill()
    _circle(cr, 0, 0, DISC_R)
    _rgb(cr, (0.995, 0.995, 0.99))
    cr.fill_preserve()
    _stroke(cr, LINE, 1.0)
    cover = getattr(st, "cover", None)
    if cover is not None:
        cr.save()
        _circle(cr, 0, 0, DISC_R - 2)
        cr.clip()
        cw, ch = cover.get_width(), cover.get_height()
        s = 2 * (DISC_R - 2) / min(cw, ch)
        cr.scale(s, s)
        cr.set_source_surface(cover, -cw / 2, -ch / 2)
        cr.paint()
        cr.restore()
    else:
        ink = (0.10, 0.10, 0.11)
        for rr in (DISC_R - 14, HUB_R + 30):
            _circle(cr, 0, 0, rr)
            _stroke(cr, (0.80, 0.80, 0.81), 1.0)
        lines = st.disc_lines or []
        if lines:
            _text(cr, lines[0][:22].lower(), -150, -120, 22, ink, align="left", bold=True)
        for i, ln in enumerate(lines[1:5]):
            _mono(cr, ln[:30].lower(), -150, -96 + i * 15, 10, (0.30, 0.30, 0.32))
        _mono(cr, "thisismade / cdp-2", -150, 170, 10, ink)
        # orange Markierung, zeigt die Drehung
        cr.rectangle(DISC_R - 40, -5, 24, 10)
        _rgb(cr, ORANGE)
        cr.fill()
    _circle(cr, 0, 0, HUB_R)
    _rgb(cr, (0.93, 0.93, 0.93))
    cr.fill_preserve()
    _stroke(cr, LINE, 1.0)
    _spindle(cr)
    cr.restore()


def _knob(cr, value):
    # mittig im Kasten "02 VOLUME" (x 1075…1186, y 255…392), samt Skala
    cx, cy = 1131, 331
    r = 33
    for i in range(31):
        a = math.radians(225 - 9 * i)
        r0, r1 = r + 5, r + (12 if i % 5 == 0 else 8)
        lit = i / 30 <= value + 1e-6
        _line(cr, cx + math.cos(a) * r0, cy - math.sin(a) * r0, cx + math.cos(a) * r1, cy - math.sin(a) * r1,
              ORANGE if lit else LINE, 1.4 if i % 5 == 0 else 1.0)
    _circle(cr, cx, cy, r)
    _rgb(cr, KEY)
    cr.fill_preserve()
    _stroke(cr, LINE, 1.0)
    a = math.radians(225 - 270 * max(0.0, min(1.0, value)))
    _line(cr, cx + math.cos(a) * 10, cy - math.sin(a) * 10, cx + math.cos(a) * (r - 6), cy - math.sin(a) * (r - 6),
          ORANGE, 3.0)


def _fader(cr, value):
    x = FADER_X
    y0, y1 = FADER_Y0 + 4, FADER_Y1 - 10
    _line(cr, x, y0, x, y1, LINE, 2.0)
    for i in range(11):
        y = y1 - i * (y1 - y0) / 10
        _line(cr, x + 18, y, x + (30 if i % 5 == 0 else 24), y, ORANGE if i == 5 else TXT_DIM, 1.0)
    _mono(cr, "+", x - 26, y0 + 8, 11, TXT_DIM)
    _mono(cr, "-", x - 26, y1 + 2, 11, TXT_DIM)
    cy = y1 - max(0.0, min(1.0, value)) * (y1 - y0)
    cr.rectangle(x - 16, cy - 9, 32, 18)
    _rgb(cr, (0.16, 0.16, 0.17))
    cr.fill()
    cr.rectangle(x - 16, cy - 1, 32, 2)
    _rgb(cr, ORANGE)
    cr.fill()
