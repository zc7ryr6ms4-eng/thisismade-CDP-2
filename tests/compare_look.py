"""Vergleicht die Gerätefront der Rust-Fassung Pixel für Pixel mit dem Python-Original.

    python3 tests/compare_look.py <ordner-mit-tmplayer> <rust.png> <python.png>

Zeichnet tmplayer/face_minimal.py mit demselben Demo-Zustand wie
`TMPLAYER_RENDER=... thisismade-cdp-2r` und bricht ab, wenn sich mehr als
0,1 % der Pixel unterscheiden.
"""
import sys
from types import SimpleNamespace

import cairo

src, rust_png, py_png = sys.argv[1:4]
sys.path.insert(0, src)
from tmplayer import face, face_minimal  # noqa: E402

st = SimpleNamespace(
    pressed=set(), disc_loaded=True, disc_angle=0.5, disc_color=(1, 1, 1),
    disc_lines=["NIGHT DRIVE", "ARTIST NAME", "ALBUM TITLE", "TRACK 04 / 12", "FLAC"], cover=None,
    bt_led=True, power_on=True, vu_l=0.7, vu_r=0.6, vu_peaks=(0.8, 0.75),
    main_text="004012003045", main_dots={}, vs_text="100", lv_text="072", stretch=True,
    cue_set=[True, False, True], varispeed_norm=0.5, level_norm=0.72, jog=0.0, repeat=1, shuffle=False,
    paused=False, remain=False, msg_mode=False, title="ARTIST – NIGHT DRIVE",
    resolution="44.1 kHz · 24 bit · FLAC",
)
surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, face.CANVAS_W, face.CANVAS_H)
cr = cairo.Context(surf)
cr.translate(face.MARGIN_X, face.MARGIN_TOP)
face_minimal.draw(cr, st)
surf.flush()
surf.write_to_png(py_png)

a = cairo.ImageSurface.create_from_png(py_png)
b = cairo.ImageSurface.create_from_png(rust_png)
if (a.get_width(), a.get_height()) != (b.get_width(), b.get_height()):
    print("LOOK FAILED: Größe", a.get_width(), a.get_height(), "≠", b.get_width(), b.get_height())
    sys.exit(1)
da, db = bytes(a.get_data()), bytes(b.get_data())
total = len(da) // 4
diff = 0
for i in range(0, len(da), 4):
    if max(abs(da[i + k] - db[i + k]) for k in range(4)) > 8:
        diff += 1
pct = 100.0 * diff / total
print("LOOK %s: %d von %d Pixeln abweichend (%.4f %%)" % ("OK" if pct <= 0.1 else "FAILED", diff, total, pct))
sys.exit(0 if pct <= 0.1 else 1)
