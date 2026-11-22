"""thisismade cdp-2 – GTK4-Oberfläche und Bedienlogik."""
import hashlib
import io
import json
import math
import os
import random
import re
import shutil
import sys
import time
from types import SimpleNamespace
from urllib.parse import unquote, urlparse

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("GdkPixbuf", "2.0")
import cairo  # noqa: E402
from gi.repository import Gdk, GdkPixbuf, Gio, GLib, Gtk  # noqa: E402

from . import face  # noqa: E402
from . import face_minimal as design  # noqa: E402
from .engine import Engine, probe_cd  # noqa: E402
from .mpris import Mpris  # noqa: E402

APP_ID = "io.github.thisismade.cdp2"
APP_NAME = "thisismade cdp-2"
VERSION = "1.0.0"

AUDIO_EXT = {".mp3", ".flac", ".ogg", ".oga", ".opus", ".wav", ".wave", ".aif", ".aiff",
             ".aifc", ".m4a", ".m4b", ".mp4", ".aac", ".wma", ".ape", ".wv", ".mka",
             ".mpc", ".tta", ".ac3", ".dsf", ".dff", ".spx", ".caf", ".mp2"}
PLAYLIST_EXT = {".m3u", ".m3u8"}
COVER_NAMES = ("cover", "folder", "front", "album", "albumart", "albumartsmall", "artwork")

DISC_COLORS = [(0.93, 0.91, 0.86), (0.96, 0.96, 0.95), (0.13, 0.13, 0.14),
               (1.0, 0.60, 0.14), (0.20, 0.42, 0.40), (0.78, 0.80, 0.83)]

SCRUB_NS_PER_TURN = 1.8e9       # eine Disc-Umdrehung = 1,8 s
DISC_RPS = 0.55                 # sichtbare Umdrehungen pro Sekunde bei 100 %

CURSORS = {"disc": "grab", "jog": "ew-resize", "resize": "se-resize",
           "varispeed": "ns-resize", "level": "ns-resize", "main_display": "pointer",
           "sync": "help"}

CSS = b"""
window.tmplayer, window.tmplayer > widget { background: none; box-shadow: none; }
"""


def _natkey(s):
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", s.lower())]


def _config_dir():
    d = os.path.join(GLib.get_user_config_dir(), "thisismade-cdp-2")
    old = os.path.join(GLib.get_user_config_dir(), "thisismade-cd-player")   # Vorversion
    if not os.path.isdir(d) and os.path.isdir(old):
        try:
            shutil.copytree(old, d)
        except OSError:
            pass
    os.makedirs(d, exist_ok=True)
    return d


def _cache_dir():
    d = os.path.join(GLib.get_user_cache_dir(), "thisismade-cdp-2")
    os.makedirs(d, exist_ok=True)
    return d


def uri_to_path(uri):
    if uri.startswith("file://"):
        return unquote(urlparse(uri).path)
    return None


# ====================================================================== App
class PlayerApp(Gtk.Application):
    VS_MIN, VS_MAX = 50, 150

    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.HANDLES_OPEN)
        GLib.set_application_name(APP_NAME)
        self.win = None
        self._res_t = 0.0
        self._res_cache = ""
        self.engine = None
        self.mpris = None
        self.tracks = []            # [{uri, title, artist, album, ...}]
        self.order = []
        self.opos = 0
        self.index = -1
        self._next_index = None
        self.cues = {}              # uri -> [ns|None]*3
        self.repeat = 0             # 0 aus, 1 alle, 2 einer
        self.shuffle = False
        self.time_mode = 0          # 0 vergangen, 1 Rest
        self.varispeed = 100
        self.level = 80
        self.entry = ""
        self.entry_time = 0
        self.msg = ""
        self.msg_until = 0
        self.power_on = True
        self.pressed = set()
        self.jog = 0.0
        self.jog_held = False
        self.disc_angle = 0.0
        self.scrubbing = False
        self.vu = [0.0, 0.0]
        self.vu_target = [0.0, 0.0]
        self.peaks = [0.0, 0.0]
        self.peak_t = [0.0, 0.0]
        self.cover_surface = None
        self.art_url = None
        self.disc_lines = []
        self.disc_color = DISC_COLORS[0]
        self._inhibit = 0
        self._errors = 0
        self._vs_timer = 0
        self._save_t = 0

    # ------------------------------------------------------------ Lebenszyklus
    def do_startup(self):
        Gtk.Application.do_startup(self)
        prov = Gtk.CssProvider()
        _load_css(prov, CSS)
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), prov,
                                                  Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.engine = Engine()
        e = self.engine
        e.connect("state-changed", self._on_state)
        e.connect("tags-changed", self._on_tags)
        e.connect("duration-changed", lambda *_: self._mpris("Metadata"))
        e.connect("eos", self._on_eos)
        e.connect("gapless-advance", self._on_gapless)
        e.connect("error", self._on_error)
        e.connect("level", self._on_level)
        e.connect("seeked", lambda _e, ns: self.mpris and self.mpris.seeked(ns))
        self._load_settings()
        self.engine.set_volume((self.level / 100.0) ** 3)
        self.engine.set_stretch(self._settings.get("stretch", False))
        self.engine.set_rate(self.varispeed / 100.0)

        for name, cb in (("open-folder", lambda *_: self.open_folder_dialog()),
                         ("open-files", lambda *_: self.open_files_dialog()),
                         ("open-cd", lambda *_: self.open_cd()),
                         ("repeat", lambda *_: self.cycle_repeat()),
                         ("shuffle", lambda *_: self.set_shuffle(not self.shuffle)),
                         ("stretch", lambda *_: self.toggle_stretch()),
                         ("eject", lambda *_: self.eject()),
                         ("help", lambda *_: self.show_help()),
                         ("about", lambda *_: self.show_about()),
                         ("quit", lambda *_: self.quit_app())):
            a = Gio.SimpleAction.new(name, None)
            a.connect("activate", cb)
            self.add_action(a)
        self.set_accels_for_action("app.quit", ["<Ctrl>q"])
        self.set_accels_for_action("app.open-files", ["<Ctrl>o"])
        self.set_accels_for_action("app.help", ["F1"])
        self.mpris = Mpris(self, APP_ID)
        GLib.timeout_add_seconds(10, self._autosave)

    def do_activate(self):
        if self.win is None:
            self.win = PlayerWindow(self)
            if SELFTEST:
                GLib.idle_add(self._selftest_start)
            else:
                self._restore_session()
        self.win.present()

    # ------------------------------------------------------------ Selbsttest (CI)
    def _selftest_start(self):
        """TMPLAYER_SELFTEST=<audiodatei>: spielt die Datei ohne Soundkarte ab,
        prüft Wiedergabe, Pegel, Tempo und speichert einen Screenshot."""
        from gi.repository import Gst
        sink = Gst.ElementFactory.make("fakesink", None)
        sink.set_property("sync", True)          # in Echtzeit, wie eine Soundkarte
        self.engine.pb.set_property("audio-sink", sink)
        self._st_levels = 0
        self.engine.connect("level", lambda *_: setattr(self, "_st_levels", self._st_levels + 1))
        self.open_gfiles([Gio.File.new_for_path(SELFTEST)])
        GLib.timeout_add(1500, self._selftest_tempo)
        return False

    def _selftest_tempo(self):
        self._st_pos1 = self.engine.position()
        self.set_varispeed(130, immediate=True)
        self.cue_set(0)
        GLib.timeout_add(1500, self._selftest_finish)
        return False

    def _selftest_finish(self):
        pos2 = self.engine.position()
        res = {
            "state": self.engine.state, "pos1_s": self._st_pos1 / 1e9, "pos2_s": pos2 / 1e9,
            "levels": self._st_levels, "tracks": len(self.tracks), "pitch": self.engine.has_pitch,
            "scaletempo": self.engine.has_scaletempo, "cue": self._cues()[0] is not None,
            "resolution": self.engine.resolution(), "title": self._title_text(),
        }
        out = os.environ.get("TMPLAYER_SCREENSHOT", "screenshot.png")
        surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, face.CANVAS_W, face.CANVAS_H)
        cr = cairo.Context(surf)
        cr.translate(face.MARGIN_X, face.MARGIN_TOP)
        design.draw(cr, self.state())
        surf.write_to_png(out)
        ok = (res["state"] == "playing" and res["pos1_s"] > 0.5 and res["pos2_s"] > res["pos1_s"]
              and res["levels"] > 5 and res["tracks"] == 1 and res["cue"])
        print("SELFTEST", "OK" if ok else "FAILED", json.dumps(res))
        self.exit_code = 0 if ok else 1
        self.quit()
        return False

    def do_open(self, files, _n, _hint):
        self.do_activate()
        self.open_gfiles(files)

    def do_shutdown(self):
        if not SELFTEST:
            self._save_settings()
        if self.engine:
            self.engine.unload()
        if self.mpris:
            self.mpris.close()
        Gtk.Application.do_shutdown(self)

    def quit_app(self):
        self.flash("bYE", 0.4)
        GLib.timeout_add(250, lambda: (self.quit(), False)[1])

    def on_mpris_ready(self):
        self.redraw()

    def mpris_raise(self):
        if self.win:
            self.win.present()

    # ------------------------------------------------------------ Einstellungen
    def _settings_path(self):
        return os.path.join(_config_dir(), "settings.json")

    def _load_settings(self):
        try:
            with open(self._settings_path(), encoding="utf-8") as f:
                s = json.load(f)
        except (OSError, ValueError):
            s = {}
        self._settings = s
        self.level = int(s.get("level", 80))
        self.varispeed = int(s.get("varispeed", 100))
        self.repeat = int(s.get("repeat", 0))
        self.shuffle = bool(s.get("shuffle", False))
        self.time_mode = int(s.get("time_mode", 0))
        self.cues = {k: v for k, v in s.get("cues", {}).items() if isinstance(v, list) and len(v) == 3}
        self.zoom = float(s.get("zoom", 0.0))

    def _save_settings(self):
        s = {
            "level": self.level, "varispeed": self.varispeed, "repeat": self.repeat,
            "shuffle": self.shuffle, "time_mode": self.time_mode,
            "stretch": self.engine.stretch if self.engine else False,
            "cues": {k: v for k, v in self.cues.items() if any(x is not None for x in v)},
            "zoom": self.win.current_zoom() if self.win else self.zoom,
            "uris": [t["uri"] for t in self.tracks if t["uri"].startswith("file://")][:5000],
            "index": self.index,
            "position": int(self.engine.position()) if self.engine else 0,
        }
        try:
            tmp = self._settings_path() + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(s, f)
            os.replace(tmp, self._settings_path())
        except OSError as ex:
            print("Einstellungen nicht gespeichert:", ex, file=sys.stderr)

    def _autosave(self):
        if self.engine and self.engine.state == "playing":
            self._save_settings()
        return True

    def _restore_session(self):
        uris = [u for u in self._settings.get("uris", []) if uri_to_path(u) and os.path.exists(uri_to_path(u))]
        if not uris:
            return
        self.set_tracks([self._track_for_uri(u) for u in uris], autoplay=False)
        idx = int(self._settings.get("index", 0))
        if 0 <= idx < len(self.tracks):
            self.play_index(idx, play=False, start_ns=int(self._settings.get("position", 0)))

    # ------------------------------------------------------------ Titel laden
    def _track_for_uri(self, uri):
        p = uri_to_path(uri)
        title = os.path.splitext(os.path.basename(p))[0] if p else uri
        return {"uri": uri, "title": title, "path": p}

    def _scan(self, path, out):
        if os.path.isdir(path):
            try:
                entries = sorted(os.listdir(path), key=_natkey)
            except OSError:
                return
            files = [e for e in entries if not e.startswith(".")]
            for e in files:
                full = os.path.join(path, e)
                if os.path.isfile(full) and os.path.splitext(e)[1].lower() in AUDIO_EXT:
                    out.append(full)
            for e in files:
                full = os.path.join(path, e)
                if os.path.isdir(full):
                    self._scan(full, out)
        elif os.path.isfile(path):
            ext = os.path.splitext(path)[1].lower()
            if ext in AUDIO_EXT:
                out.append(path)
            elif ext in PLAYLIST_EXT:
                base = os.path.dirname(path)
                try:
                    with open(path, encoding="utf-8", errors="replace") as f:
                        for ln in f:
                            ln = ln.strip()
                            if not ln or ln.startswith("#"):
                                continue
                            if ln.startswith("file://"):
                                ln = uri_to_path(ln)
                            full = ln if os.path.isabs(ln) else os.path.join(base, ln)
                            if os.path.isfile(full):
                                out.append(full)
                except OSError:
                    pass

    def open_gfiles(self, gfiles):
        paths, others = [], []
        for gf in gfiles:
            p = gf.get_path()
            if p:
                self._scan(p, paths)
            else:
                others.append(gf.get_uri())
        tracks = [self._track_for_uri(GLib.filename_to_uri(p, None)) for p in paths]
        for u in others:
            if u.startswith("cdda://"):
                self.open_cd()
                return
            tracks.append({"uri": u, "title": os.path.basename(unquote(u)) or u, "path": None})
        if tracks:
            self.set_tracks(tracks, autoplay=True)
        else:
            self.flash("no AUdio")

    def open_uris(self, uris):
        self.open_gfiles([Gio.File.new_for_uri(u) for u in uris])

    def set_tracks(self, tracks, autoplay=True):
        self.engine.stop()
        self.tracks = tracks
        self.entry = ""
        self._make_order(keep=None)
        self.flash("LoAd %3d" % len(tracks), 1.0)
        if autoplay:
            self.play_index(self.order[0], play=True)
        self._mpris("Metadata", "CanGoNext", "CanGoPrevious", "CanPlay", "CanPause", "CanSeek")

    def eject(self):
        self.engine.unload()
        self.tracks, self.order, self.index = [], [], -1
        self.cover_surface = None
        self.disc_lines = []
        self.flash("EJECt")
        self._mpris("Metadata", "PlaybackStatus", "CanGoNext", "CanGoPrevious", "CanPlay")

    def open_cd(self):
        self.flash("rEAd  cd", 15)

        def done(n, err):
            if n:
                tracks = [{"uri": "cdda://%d" % i, "title": "TRACK %02d" % i, "album": "AUDIO CD",
                           "path": None} for i in range(1, n + 1)]
                self.set_tracks(tracks, autoplay=True)
                self.flash("cd   %3d tr" % n, 1.5)
            else:
                self.flash("no  cd", 1.5)
                if err:
                    print(err, file=sys.stderr)
            return False

        probe_cd(done)

    def _make_order(self, keep):
        n = len(self.tracks)
        self.order = list(range(n))
        if self.shuffle and n > 1:
            random.shuffle(self.order)
            if keep is not None and keep in self.order:
                self.order.remove(keep)
                self.order.insert(0, keep)
        self.opos = self.order.index(keep) if keep is not None and keep in self.order else 0

    def has_tracks(self):
        return bool(self.tracks) and self.index >= 0

    # ------------------------------------------------------------ Transport
    def play_index(self, i, play=True, start_ns=0):
        if not (0 <= i < len(self.tracks)):
            return
        self.index = i
        if i in self.order:
            self.opos = self.order.index(i)
        t = self.tracks[i]
        self.engine.load(t["uri"], play=play, start_ns=start_ns)
        self._prepare_next()
        self._update_disc()
        self._mpris("Metadata", "PlaybackStatus")

    def _next_in_order(self, wrap):
        if not self.order:
            return None
        p = self.opos + 1
        if p >= len(self.order):
            if not wrap:
                return None
            p = 0
        return self.order[p]

    def _prev_in_order(self, wrap=True):
        if not self.order:
            return None
        p = self.opos - 1
        if p < 0:
            if not wrap:
                return None
            p = len(self.order) - 1
        return self.order[p]

    def _prepare_next(self):
        if self.repeat == 2:
            nxt = self.index
        else:
            nxt = self._next_in_order(wrap=self.repeat == 1)
        self._next_index = nxt
        self.engine.set_next_uri(self.tracks[nxt]["uri"] if nxt is not None else None)

    def play(self):
        if not self.power_on:
            return
        if not self.has_tracks():
            if self.tracks:
                self.play_index(self.order[0])
            else:
                self.flash("no  dISC")
            return
        self.engine.play()

    def pause(self):
        self.engine.pause()

    def play_pause(self):
        if self.engine.state == "playing":
            self.pause()
        else:
            self.play()

    def stop(self):
        self.engine.stop()
        self.redraw()

    def next_track(self):
        if not self.tracks:
            return
        nxt = self._next_in_order(wrap=True)
        if nxt is not None:
            self.play_index(nxt, play=True)

    def prev_track(self, force=False):
        if not self.tracks:
            return
        if not force and self.engine.position() > 3 * 1e9:
            self.seek_to(0)
            return
        prv = self._prev_in_order(wrap=True)
        if prv is not None:
            self.play_index(prv)

    def seek_to(self, ns):
        self.engine.seek(int(ns))

    def seek_relative(self, delta_ns):
        self.engine.seek(int(self.engine.position() + delta_ns))

    def jump_to_track(self, n):
        if 1 <= n <= len(self.tracks):
            self.play_index(n - 1)
        else:
            self.flash("Err  %3d" % n)

    # ------------------------------------------------------------ Modi
    def set_repeat(self, r):
        self.repeat = r % 3
        self.flash(("rEP  oFF", "rEP  ALL", "rEP  onE")[self.repeat])
        if self.has_tracks():
            self._prepare_next()
        self._mpris("LoopStatus")

    def cycle_repeat(self):
        self.set_repeat(self.repeat + 1)

    def set_shuffle(self, on):
        self.shuffle = on
        self._make_order(keep=self.index if self.index >= 0 else None)
        if self.has_tracks():
            self._prepare_next()
        self.flash("SHUF  on" if on else "SHUF  oFF")
        self._mpris("Shuffle")

    def toggle_time_mode(self):
        self.time_mode = 1 - self.time_mode
        self.flash("ELAPSEd" if self.time_mode == 0 else "rEnAIn", 0.8)

    def toggle_stretch(self):
        self.engine.set_stretch(not self.engine.stretch)
        self.flash("LoCK  on" if self.engine.stretch else "LoCK  oFF", 1.0)

    def set_varispeed(self, v, immediate=False):
        v = int(max(self.VS_MIN, min(self.VS_MAX, v)))
        if v == self.varispeed:
            return
        self.varispeed = v
        self.redraw()
        if immediate:
            self._apply_varispeed()
        elif not self._vs_timer:
            self._vs_timer = GLib.timeout_add(110, self._apply_varispeed)

    def _apply_varispeed(self):
        self._vs_timer = 0
        self.engine.set_rate(self.varispeed / 100.0)
        self._mpris("Rate")
        return False

    def set_level(self, v):
        v = int(max(0, min(100, v)))
        if v != self.level:
            self.level = v
            self.engine.set_volume((v / 100.0) ** 3)
            self._mpris("Volume")
            self.redraw()

    def toggle_power(self):
        self.power_on = not self.power_on
        if not self.power_on:
            self._was_playing = self.engine.state == "playing"
            self.engine.pause()
        else:
            self.flash("HELLo", 0.6)
        self.redraw()

    # ------------------------------------------------------------ Cue
    def _cues(self):
        if not self.has_tracks():
            return [None, None, None]
        return self.cues.setdefault(self.tracks[self.index]["uri"], [None, None, None])

    def cue_press(self, i):
        if not self.has_tracks():
            self.flash("no  dISC")
            return
        c = self._cues()
        if c[i] is None:
            self.cue_set(i)
        else:
            self.seek_to(c[i])
            if self.engine.state != "playing":
                self.play()
            self.flash("CUE %d" % (i + 1), 0.6)

    def cue_set(self, i):
        if not self.has_tracks():
            return
        self._cues()[i] = int(self.engine.position())
        self.flash("CUE %d  SEt" % (i + 1), 0.8)

    def cue_clear(self, i):
        if self.has_tracks():
            self._cues()[i] = None
            self.flash("CUE %d  CLr" % (i + 1), 0.8)

    # ------------------------------------------------------------ Ziffernblock
    def keypad(self, k):
        now = time.monotonic()
        if k.isdigit():
            if now - self.entry_time > 4:
                self.entry = ""
            self.entry = (self.entry + k)[-3:]
            self.entry_time = now
        elif k == "T":
            self.toggle_time_mode()
        elif k == "C":
            if self.entry:
                self.entry = ""
            else:
                self.cycle_repeat()
        self.redraw()

    def keypad_long(self, k):
        if k == "C":
            self.set_shuffle(not self.shuffle)
        elif k == "T":
            self.toggle_stretch()

    def enter(self):
        if self.entry and time.monotonic() - self.entry_time < 4:
            n = int(self.entry)
            self.entry = ""
            self.jump_to_track(n)
        else:
            self.entry = ""
            self.play_pause()
        self.redraw()

    # ------------------------------------------------------------ Engine-Events
    def _on_state(self, _e):
        playing = self.engine.state == "playing"
        if playing and not self._inhibit and self.win:
            self._inhibit = self.inhibit(self.win, Gtk.ApplicationInhibitFlags.SUSPEND,
                                         "Musikwiedergabe")
        elif not playing and self._inhibit:
            self.uninhibit(self._inhibit)
            self._inhibit = 0
        if playing:
            self._errors = 0
        self._mpris("PlaybackStatus", "Metadata")
        self.redraw()

    def _on_tags(self, _e):
        self._update_disc()
        self._mpris("Metadata")

    def _on_eos(self, _e):
        if self.repeat == 2:
            self.seek_to(0)
            self.engine.play()
            return
        nxt = self._next_in_order(wrap=self.repeat == 1)
        if nxt is None:
            self.engine.stop()
            if self.order:
                self.play_index(self.order[0], play=False)
                self.engine.stop()
            self.flash("End", 1.2)
        else:
            self.play_index(nxt)

    def _on_gapless(self, _e):
        if self._next_index is not None:
            self.index = self._next_index
            if self.index in self.order:
                self.opos = self.order.index(self.index)
        self._prepare_next()
        self._update_disc()
        self._mpris("Metadata")

    def _on_error(self, _e, text):
        print("Wiedergabefehler:", text, file=sys.stderr)
        self.flash("Err", 1.2)
        self._errors += 1
        if self._errors < len(self.tracks):
            nxt = self._next_in_order(wrap=self.repeat == 1)
            if nxt is not None:
                GLib.timeout_add(400, lambda: (self.play_index(nxt), False)[1])

    def _on_level(self, _e, l, r):
        self.vu_target = [l, r]

    # ------------------------------------------------------------ Disc-Aufdruck
    def current_info(self):
        if not self.has_tracks():
            return {}
        t = dict(self.tracks[self.index])
        for k, v in self.engine.tags.items():
            t[k] = v
        t["art_url"] = self.art_url
        return t

    def _update_disc(self):
        info = self.current_info()
        if not info:
            return
        lines = [info.get("title", "")]
        for k in ("artist", "album"):
            if info.get(k):
                lines.append(info[k])
        lines.append("TRACK %02d / %02d" % (self.index + 1, len(self.tracks)))
        codec = info.get("codec")
        if codec:
            br = info.get("bitrate")
            lines.append(codec + (" %d KBPS" % (br // 1000) if br else ""))
        self.disc_lines = [str(x).upper()[:30] for x in lines if x]
        key = info.get("album") or os.path.dirname(info.get("path") or "") or info.get("uri", "")
        self.disc_color = DISC_COLORS[int(hashlib.md5(key.encode()).hexdigest(), 16) % len(DISC_COLORS)]

        data, url = self.engine.cover, None
        if data:
            h = hashlib.md5(data).hexdigest()[:16]
            fn = os.path.join(_cache_dir(), "cover-%s.img" % h)
            if not os.path.exists(fn):
                try:
                    with open(fn, "wb") as f:
                        f.write(data)
                except OSError:
                    pass
            url = GLib.filename_to_uri(fn, None)
        elif info.get("path"):
            d = os.path.dirname(info["path"])
            try:
                for e in sorted(os.listdir(d)):
                    b, ext = os.path.splitext(e)
                    if ext.lower() in (".jpg", ".jpeg", ".png", ".webp") and b.lower() in COVER_NAMES:
                        url = GLib.filename_to_uri(os.path.join(d, e), None)
                        with open(os.path.join(d, e), "rb") as f:
                            data = f.read()
                        break
            except OSError:
                pass
        if url != self.art_url:
            self.art_url = url
            self.cover_surface = _surface_from_bytes(data) if data else None
        self.redraw()

    # ------------------------------------------------------------ Anzeige
    def flash(self, text, secs=1.0):
        self.msg = text
        self.msg_until = time.monotonic() + secs
        self.redraw()

    def redraw(self):
        if self.win:
            self.win.area.queue_draw()

    def _mpris(self, *names):
        if self.mpris:
            self.mpris.changed(*names)

    def display_state(self):
        now = time.monotonic()
        blink = int(now * 2) % 2 == 0
        dots = {}
        if self.msg and now < self.msg_until:
            main = self.msg
        elif not self.tracks:
            main = "------------"
        else:
            tr = "%03d" % (self.index + 1 if self.index >= 0 else 0)
            if self.entry and now - self.entry_time < 4:
                tr = self.entry.rjust(3, "-") if blink else "   "
            idx = "%03d" % min(999, len(self.tracks))
            pos = self.engine.position()
            dur = self.engine.duration()
            if self.time_mode == 1 and dur:
                rem = max(0, dur - pos) / 1e9
                mm, ss = divmod(int(rem + 0.999), 60)
                tm = "-%02d" % min(99, mm)
            else:
                mm, ss = divmod(int(pos / 1e9), 60)
                tm = "%03d" % min(999, mm)
            sec = "%03d" % ss
            if self.engine.state == "paused" and not blink:
                tm, sec = "   ", "   "
            main = tr + idx + tm + sec
            if self.repeat == 1:
                dots[0] = (2,)
            elif self.repeat == 2:
                dots[0] = (1, 2)
            if self.shuffle:
                dots[1] = (2,)
        return main, dots

    def _title_text(self):
        info = self.current_info()
        if not info:
            return ""
        t = info.get("title", "")
        if info.get("artist"):
            t = info["artist"] + " – " + t
        return t.upper()

    def _res_text(self):
        now = time.monotonic()
        if now - self._res_t > 1.0:      # Caps höchstens 1× pro Sekunde abfragen
            self._res_t = now
            self._res_cache = self.engine.resolution() if self.has_tracks() else ""
        return self._res_cache

    def state(self):
        main, dots = self.display_state()
        cues = self._cues()
        return SimpleNamespace(
            pressed=self.pressed, disc_loaded=bool(self.tracks), disc_angle=self.disc_angle,
            disc_color=self.disc_color, disc_lines=self.disc_lines, cover=self.cover_surface,
            bt_led=bool(self.mpris and self.mpris.connected), power_on=self.power_on,
            vu_l=self.vu[0], vu_r=self.vu[1], vu_peaks=tuple(self.peaks),
            main_text=main, main_dots=dots,
            vs_text="%03d" % self.varispeed, lv_text="%03d" % self.level,
            stretch=self.engine.stretch, cue_set=[c is not None for c in cues],
            varispeed_norm=(self.varispeed - self.VS_MIN) / (self.VS_MAX - self.VS_MIN),
            level_norm=self.level / 100.0, jog=self.jog,
            repeat=self.repeat, shuffle=self.shuffle, paused=self.engine.state == "paused",
            remain=self.time_mode == 1, msg_mode=bool(self.msg and time.monotonic() < self.msg_until),
            title=self._title_text(), resolution=self._res_text(),
        )

    def animate(self, dt, now):
        """Wird pro Frame aufgerufen. Gibt True zurück, wenn neu gezeichnet werden soll."""
        busy = False
        playing = self.engine.state == "playing" and self.power_on
        if playing and not self.scrubbing:
            self.disc_angle += dt * 2 * math.pi * DISC_RPS * self.varispeed / 100.0
            busy = True
        for i in range(2):
            tgt = self.vu_target[i] if playing else 0.0
            if tgt >= self.vu[i]:
                self.vu[i] = tgt
            else:
                self.vu[i] = max(tgt, self.vu[i] - dt * 1.6)
            if self.vu[i] >= self.peaks[i]:
                self.peaks[i] = self.vu[i]
                self.peak_t[i] = now
            elif now - self.peak_t[i] > 0.8:
                self.peaks[i] = max(0.0, self.peaks[i] - dt * 0.7)
            if self.vu[i] > 0.001 or self.peaks[i] > 0.001:
                busy = True
        if not playing:
            self.vu_target = [0.0, 0.0]
        if not self.jog_held and abs(self.jog) > 0.001:
            self.jog *= max(0.0, 1 - dt * 14)
            if abs(self.jog) < 0.01:
                self.jog = 0.0
            busy = True
        return busy

    # ------------------------------------------------------------ Dialoge
    def open_folder_dialog(self):
        d = Gtk.FileDialog(title="Ordner laden (DATA)")
        d.set_initial_folder(Gio.File.new_for_path(GLib.get_user_special_dir(
            GLib.UserDirectory.DIRECTORY_MUSIC) or GLib.get_home_dir()))

        def done(dlg, res):
            try:
                f = dlg.select_folder_finish(res)
            except GLib.Error:
                return
            if f:
                self.open_gfiles([f])

        d.select_folder(self.win, None, done)

    def open_files_dialog(self):
        d = Gtk.FileDialog(title="Dateien laden (USB)")
        flt = Gtk.FileFilter()
        flt.set_name("Audio und Playlists")
        flt.add_mime_type("audio/*")
        for ext in sorted(AUDIO_EXT | PLAYLIST_EXT):
            flt.add_suffix(ext[1:])
        store = Gio.ListStore.new(Gtk.FileFilter)
        store.append(flt)
        d.set_filters(store)
        d.set_default_filter(flt)

        def done(dlg, res):
            try:
                model = dlg.open_multiple_finish(res)
            except GLib.Error:
                return
            files = [model.get_item(i) for i in range(model.get_n_items())]
            if files:
                self.open_gfiles(files)

        d.open_multiple(self.win, None, done)

    def show_about(self):
        dlg = Gtk.AboutDialog(transient_for=self.win, modal=True)
        dlg.set_program_name(APP_NAME)
        dlg.set_version(VERSION)
        dlg.set_logo_icon_name(APP_ID)
        dlg.set_comments("CD-Player-Software für GNOME mit Varispeed, Key Lock, Memory-Cues und Shuttle.")
        dlg.set_website("https://github.com/zc7ryr6ms4-eng/thisismade-CDP-2")
        dlg.set_license_type(getattr(Gtk.License, "BSD_3", Gtk.License.BSD))
        dlg.present()

    def show_help(self):
        w = Gtk.Window(title=APP_NAME + " – Bedienung", transient_for=self.win, modal=False)
        w.set_default_size(560, 640)
        lab = Gtk.Label()
        lab.set_markup(HELP)
        lab.set_wrap(True)
        lab.set_xalign(0)
        lab.set_selectable(True)
        lab.set_margin_top(18)
        lab.set_margin_bottom(18)
        lab.set_margin_start(22)
        lab.set_margin_end(22)
        sc = Gtk.ScrolledWindow()
        sc.set_child(lab)
        w.set_child(sc)
        w.present()


def _load_css(prov, css):
    # Die Signatur von load_from_data hat sich zwischen GTK-4-Versionen geändert.
    if hasattr(prov, "load_from_string"):          # GTK ≥ 4.12
        prov.load_from_string(css.decode())
        return
    try:
        prov.load_from_data(css)
    except TypeError:
        prov.load_from_data(css.decode(), -1)


def _surface_from_bytes(data, size=640):
    try:
        loader = GdkPixbuf.PixbufLoader()
        loader.write(data)
        loader.close()
        pb = loader.get_pixbuf()
        w, h = pb.get_width(), pb.get_height()
        s = min(w, h)
        pb = pb.new_subpixbuf((w - s) // 2, (h - s) // 2, s, s)
        pb = pb.scale_simple(size, size, GdkPixbuf.InterpType.BILINEAR)
        ok, buf = pb.save_to_bufferv("png", [], [])
        if not ok:
            return None
        return cairo.ImageSurface.create_from_png(io.BytesIO(buf))
    except (GLib.Error, cairo.Error, OSError, TypeError) as ex:
        print("Cover nicht lesbar:", ex, file=sys.stderr)
        return None


# ====================================================================== Fenster
class PlayerWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title=APP_NAME)
        self.app = app
        self.set_decorated(False)
        self.add_css_class("tmplayer")
        self.set_icon_name(APP_ID)
        z = app.zoom
        if z <= 0:
            z = self._auto_zoom()
        self.set_default_size(int(face.CANVAS_W * z), int(face.CANVAS_H * z))

        self.area = Gtk.DrawingArea()
        self.area.set_draw_func(self._draw)
        self.area.set_focusable(True)
        self.set_child(self.area)
        self._bg = None
        self._bg_key = None
        self._fit_cache = (1.0, 0.0, 0.0)

        drag = Gtk.GestureDrag()
        drag.set_button(0)
        drag.connect("drag-begin", self._on_begin)
        drag.connect("drag-update", self._on_update)
        drag.connect("drag-end", self._on_end)
        self.area.add_controller(drag)

        scroll = Gtk.EventControllerScroll.new(Gtk.EventControllerScrollFlags.BOTH_AXES)
        scroll.connect("scroll", self._on_scroll)
        self.area.add_controller(scroll)

        motion = Gtk.EventControllerMotion()
        motion.connect("motion", self._on_motion)
        self.area.add_controller(motion)
        self._mouse = (0.0, 0.0)

        keys = Gtk.EventControllerKey()
        keys.connect("key-pressed", self._on_key)
        self.add_controller(keys)

        drop = Gtk.DropTarget.new(Gdk.FileList, Gdk.DragAction.COPY)
        drop.connect("drop", self._on_drop)
        self.area.add_controller(drop)

        menu = Gio.Menu()
        sec = Gio.Menu()
        sec.append("Ordner laden …", "app.open-folder")
        sec.append("Dateien laden …", "app.open-files")
        sec.append("Audio-CD lesen", "app.open-cd")
        sec.append("Auswerfen", "app.eject")
        menu.append_section(None, sec)
        sec = Gio.Menu()
        sec.append("Wiederholen umschalten", "app.repeat")
        sec.append("Zufall umschalten", "app.shuffle")
        sec.append("Varispeed / Time Stretch", "app.stretch")
        menu.append_section(None, sec)
        sec = Gio.Menu()
        sec.append("Bedienung", "app.help")
        sec.append("Über " + APP_NAME, "app.about")
        sec.append("Beenden", "app.quit")
        menu.append_section(None, sec)
        self.menu = Gtk.PopoverMenu.new_from_model(menu)
        self.menu.set_parent(self.area)
        self.menu.set_has_arrow(False)

        self._act = None
        self._last_frame = None
        self._idle_acc = 0.0
        self.area.add_tick_callback(self._tick)
        self.connect("close-request", self._on_close)

    def _on_close(self, *_):
        self.app._save_settings()
        self.menu.unparent()
        return False

    def _auto_zoom(self):
        try:
            mons = Gdk.Display.get_default().get_monitors()
            g = mons.get_item(0).get_geometry()
            return max(0.35, min(1.0, (g.height * 0.82) / face.CANVAS_H))
        except Exception:  # noqa: BLE001
            return 0.6

    def current_zoom(self):
        return self.get_width() / face.CANVAS_W if self.get_width() else self.app.zoom

    def set_zoom(self, z):
        z = max(0.3, min(2.0, z))
        self.set_default_size(int(face.CANVAS_W * z), int(face.CANVAS_H * z))

    # ------------------------------------------------------------ Zeichnen
    def _fit(self, w, h):
        s = min(w / face.CANVAS_W, h / face.CANVAS_H)
        ox = (w - face.CANVAS_W * s) / 2
        oy = (h - face.CANVAS_H * s) / 2
        return s, ox, oy

    def _to_dev(self, x, y):
        s, ox, oy = self._fit_cache
        return (x - ox) / s - face.MARGIN_X, (y - oy) / s - face.MARGIN_TOP

    def _draw(self, _area, cr, w, h):
        s, ox, oy = self._fit(w, h)
        self._fit_cache = (s, ox, oy)
        key = (w, h)
        if self._bg is None or self._bg_key != key:
            self._bg = cr.get_target().create_similar(cairo.CONTENT_COLOR_ALPHA, w, h)
            bc = cairo.Context(self._bg)
            bc.translate(ox, oy)
            bc.scale(s, s)
            bc.translate(face.MARGIN_X, face.MARGIN_TOP)
            design.draw_static(bc)
            self._bg_key = key
        cr.set_source_surface(self._bg, 0, 0)
        cr.paint()
        cr.translate(ox, oy)
        cr.scale(s, s)
        cr.translate(face.MARGIN_X, face.MARGIN_TOP)
        design.draw_dynamic(cr, self.app.state())

    def _tick(self, widget, clock):
        t = clock.get_frame_time() / 1e6
        dt = 0.0 if self._last_frame is None else min(0.1, t - self._last_frame)
        self._last_frame = t
        busy = self.app.animate(dt, t)
        if busy or self._act:
            widget.queue_draw()
            self._idle_acc = 0
        else:
            self._idle_acc += dt
            if self._idle_acc > 0.25:       # Uhr / Blinken
                self._idle_acc = 0
                widget.queue_draw()
        return True

    # ------------------------------------------------------------ Maus
    def _on_motion(self, _c, x, y):
        self._mouse = (x, y)
        rid = face.hit(*self._to_dev(x, y))
        name = CURSORS.get(rid, "pointer" if rid else "default")
        self.area.set_cursor_from_name(name)

    def _on_begin(self, g, x, y):
        a = self.app
        btn = g.get_current_button()
        mods = g.get_current_event_state()
        shift = bool(mods & Gdk.ModifierType.SHIFT_MASK)
        dx, dy = self._to_dev(x, y)
        rid = face.hit(dx, dy)
        self.area.grab_focus()

        if btn == 3 and rid in (None, "disc"):
            r = Gdk.Rectangle()
            r.x, r.y, r.width, r.height = int(x), int(y), 1, 1
            self.menu.set_pointing_to(r)
            self.menu.popup()
            g.set_state(Gtk.EventSequenceState.DENIED)
            return
        if rid is None or (rid == "disc" and not a.power_on):
            self._begin_window_op(g, btn, x, y, move=True)
            return
        if rid == "resize":
            self._begin_window_op(g, btn, x, y, move=False)
            return
        if not a.power_on and rid != "power":
            return

        act = SimpleNamespace(id=rid, btn=btn, shift=shift, x=x, y=y, t=time.monotonic(),
                              long_done=False, long_src=0, moved=0.0)
        self._act = act

        if rid in ("varispeed", "level"):
            act.start = a.varispeed if rid == "varispeed" else a.level
            now = time.monotonic()
            last = getattr(self, "_last_knob", (None, 0))
            if last[0] == rid and now - last[1] < 0.35:
                if rid == "varispeed":
                    a.set_varispeed(100, immediate=True)
                    a.flash("VAri  100", 0.6)
                act.start = a.varispeed if rid == "varispeed" else a.level
            self._last_knob = (rid, now)
            return
        if rid == "jog":
            a.jog_held = True
            act.jog_timer = GLib.timeout_add(50, self._jog_step)
            a.pressed.add("jog")
            return
        if rid == "disc":
            act.prev_angle = math.atan2(dy - face.DISC_C[1], dx - face.DISC_C[0])
            act.was_playing = a.engine.state == "playing"
            act.scrub = a.engine.position()
            act.last_seek = 0.0
            return
        if rid == "main_display":
            return
        # Taste
        a.pressed.add(rid)
        if btn == 1 and rid in ("power", "key_C", "key_T") or (rid.startswith("cue") and btn == 1 and not shift):
            act.long_src = GLib.timeout_add(650, self._on_long, act)
        a.redraw()

    def _begin_window_op(self, g, btn, x, y, move):
        surf = self.get_surface()
        dev = g.get_device()
        ts = g.get_current_event_time()
        if surf is None or dev is None:
            return
        # Koordinaten des DrawingArea → Surface (Fenster ohne Dekoration: identisch)
        if move:
            surf.begin_move(dev, btn, x, y, ts)
        else:
            surf.begin_resize(Gdk.SurfaceEdge.SOUTH_EAST, dev, btn, x, y, ts)
        g.set_state(Gtk.EventSequenceState.DENIED)

    def _on_long(self, act):
        a = self.app
        act.long_src = 0
        if self._act is not act:
            return False
        act.long_done = True
        rid = act.id
        if rid == "power":
            a.quit_app()
        elif rid == "key_C":
            a.keypad_long("C")
        elif rid == "key_T":
            a.keypad_long("T")
        elif rid.startswith("cue"):
            a.cue_set(int(rid[-1]) - 1)
        return False

    def _on_update(self, g, ox, oy):
        act = self._act
        if act is None:
            return
        a = self.app
        s = self._fit_cache[0]
        act.moved = max(act.moved, math.hypot(ox, oy) / s)
        if act.id in ("varispeed", "level"):
            k = 0.2 if (g.get_current_event_state() & Gdk.ModifierType.SHIFT_MASK) else 1.0
            delta = (-oy + ox * 0.5) / s
            if act.id == "varispeed":
                a.set_varispeed(round(act.start + delta * k * 100 / 180))
            else:
                a.set_level(round(act.start + delta * k * 100 / 220))
        elif act.id == "jog":
            a.jog = max(-1.0, min(1.0, ox / s / (face.JOG_TRAVEL * 1.6)))
        elif act.id == "disc":
            dx, dy = self._to_dev(act.x + ox, act.y + oy)
            ang = math.atan2(dy - face.DISC_C[1], dx - face.DISC_C[0])
            d = ang - act.prev_angle
            d = (d + math.pi) % (2 * math.pi) - math.pi
            act.prev_angle = ang
            if act.moved > 4 and not a.scrubbing:
                a.scrubbing = True
                if act.was_playing:
                    a.engine.pause()
            if a.scrubbing:
                a.disc_angle += d
                act.scrub = max(0, act.scrub + d / (2 * math.pi) * SCRUB_NS_PER_TURN)
                now = time.monotonic()
                if now - act.last_seek > 0.06:
                    act.last_seek = now
                    a.seek_to(act.scrub)
                a.redraw()

    def _on_end(self, g, ox, oy):
        act = self._act
        self._act = None
        if act is None:
            return
        a = self.app
        if act.long_src:
            GLib.source_remove(act.long_src)
        rid = act.id
        a.pressed.discard(rid)
        inside = face.hit(*self._to_dev(act.x + ox, act.y + oy)) == rid
        if rid == "jog":
            a.jog_held = False
            GLib.source_remove(act.jog_timer)
        elif rid == "disc":
            if a.scrubbing:
                a.seek_to(act.scrub)
                a.scrubbing = False
                if act.was_playing:
                    a.engine.play()
            elif act.moved < 4:
                a.play_pause()
        elif rid in ("varispeed", "level"):
            if rid == "varispeed":
                a._apply_varispeed() if a._vs_timer == 0 else None
        elif rid == "main_display":
            if inside:
                a.toggle_time_mode()
        elif inside and not act.long_done:
            self._activate(rid, act.btn, act.shift)
        a.redraw()

    def _activate(self, rid, btn, shift):
        a = self.app
        if rid == "power":
            a.toggle_power()
            return
        if not a.power_on:
            return
        if rid.startswith("key_"):
            a.keypad(rid[4:])
        elif rid == "enter":
            a.enter()
        elif rid.startswith("cue"):
            i = int(rid[-1]) - 1
            if btn == 3 or shift:
                a.cue_clear(i)
            else:
                a.cue_press(i)
        elif rid == "play":
            a.play_pause()
        elif rid == "stop":
            a.stop()
        elif rid == "prev":
            a.prev_track()
        elif rid == "next":
            a.next_track()
        elif rid == "data":
            if btn == 3:
                a.open_cd()
            else:
                a.open_folder_dialog()
        elif rid == "usb":
            a.open_files_dialog()
        elif rid == "cd":
            a.open_cd()
        elif rid == "vs_display":
            a.toggle_stretch()
        elif rid == "repeat":
            a.cycle_repeat()
        elif rid == "shuffle":
            a.set_shuffle(not a.shuffle)
        elif rid == "eject":
            a.eject()
        elif rid == "output":
            _launch(["gnome-control-center", "sound"])
        elif rid == "sync":
            a.show_help()

    def _jog_step(self):
        a = self.app
        j = a.jog
        if abs(j) > 0.08 and a.has_tracks():
            speed = math.copysign(j * j, j) * 16.0     # bis 16-fach
            a.seek_relative(speed * 0.05 * 1e9)
        return True

    def _on_scroll(self, c, dx, dy):
        a = self.app
        if not a.power_on:
            return True
        rid = face.hit(*self._to_dev(*self._mouse))
        step = -(dy if abs(dy) >= abs(dx) else -dx)
        if c.get_unit() == Gdk.ScrollUnit.SURFACE:
            step /= 10.0
        if rid == "varispeed":
            if step:
                a.set_varispeed(a.varispeed + (round(step) or (1 if step > 0 else -1)))
        elif rid in ("disc", "jog"):
            if a.has_tracks():
                a.disc_angle += step * 0.15
                a.seek_relative(step * 2e9)
        elif step:
            a.set_level(a.level + (round(step * 2) or (1 if step > 0 else -1)))
        return True

    def _on_drop(self, _t, value, _x, _y):
        try:
            files = value.get_files()
        except AttributeError:
            return False
        if files:
            self.app.open_gfiles(files)
            return True
        return False

    # ------------------------------------------------------------ Tastatur
    def _flash_key(self, rid):
        a = self.app
        a.pressed.add(rid)
        a.redraw()
        GLib.timeout_add(120, lambda: (a.pressed.discard(rid), a.redraw(), False)[2])

    def _on_key(self, _c, keyval, _code, state):
        a = self.app
        name = Gdk.keyval_name(keyval) or ""
        ctrl = bool(state & Gdk.ModifierType.CONTROL_MASK)
        shift = bool(state & Gdk.ModifierType.SHIFT_MASK)
        if ctrl:
            if name in ("plus", "equal", "KP_Add"):
                self.set_zoom(self.current_zoom() * 1.1)
            elif name in ("minus", "KP_Subtract"):
                self.set_zoom(self.current_zoom() / 1.1)
            elif name in ("0", "KP_0"):
                self.set_zoom(self._auto_zoom())
            elif name == "o":
                a.open_files_dialog()
            elif name == "q":
                a.quit_app()
            else:
                return False
            return True
        if not a.power_on and name not in ("p",):
            return False
        digit = None
        if len(name) == 1 and name.isdigit():
            digit = name
        elif name.startswith("KP_") and name[3:].isdigit():
            digit = name[3:]
        if digit is not None:
            self._flash_key("key_" + digit)
            a.keypad(digit)
        elif name in ("Return", "KP_Enter"):
            self._flash_key("enter")
            a.enter()
        elif name == "space":
            self._flash_key("play")
            a.play_pause()
        elif name in ("Escape", "period"):
            self._flash_key("stop")
            a.stop()
        elif name in ("Page_Down", "n"):
            self._flash_key("next")
            a.next_track()
        elif name in ("Page_Up", "b"):
            self._flash_key("prev")
            a.prev_track()
        elif name == "Right":
            a.seek_relative((30 if shift else 5) * 1e9)
        elif name == "Left":
            a.seek_relative(-(30 if shift else 5) * 1e9)
        elif name == "Up":
            a.set_level(a.level + 2)
        elif name == "Down":
            a.set_level(a.level - 2)
        elif name in ("bracketleft", "minus", "KP_Subtract"):
            a.set_varispeed(a.varispeed - 1)
        elif name in ("bracketright", "plus", "KP_Add"):
            a.set_varispeed(a.varispeed + 1)
        elif name in ("backslash", "numbersign"):
            a.set_varispeed(100, immediate=True)
        elif name in ("t", "T"):
            self._flash_key("key_T")
            a.toggle_time_mode()
        elif name in ("c", "BackSpace", "Delete"):
            self._flash_key("key_C")
            a.entry = ""
            a.redraw()
        elif name in ("m", "M"):
            a.toggle_stretch()
        elif name in ("r", "R"):
            a.cycle_repeat()
        elif name in ("s", "S"):
            a.set_shuffle(not a.shuffle)
        elif name in ("q", "w", "e", "Q", "W", "E", "F2", "F3", "F4"):
            i = {"q": 0, "w": 1, "e": 2, "F2": 0, "F3": 1, "F4": 2}[name.lower() if len(name) == 1 else name]
            self._flash_key("cue%d" % (i + 1))
            if shift:
                a.cue_set(i)
            else:
                a.cue_press(i)
        elif name in ("o", "O"):
            a.open_folder_dialog()
        elif name in ("d", "D"):
            a.open_cd()
        elif name in ("j", "J"):
            a.eject()
        elif name == "p":
            self._flash_key("power")
            a.toggle_power()
        elif name in ("h", "question"):
            a.show_help()
        else:
            return False
        return True


def _launch(argv):
    try:
        Gio.Subprocess.new(argv, Gio.SubprocessFlags.NONE)
    except GLib.Error as ex:
        print("Konnte nicht starten:", " ".join(argv), ex, file=sys.stderr)


HELP = """<b><big>thisismade cdp-2 – Bedienung</big></b>

<b>Laden</b>
• <b>OPEN</b>: Ordner laden (Unterordner werden mitgelesen)
• <b>FILES</b>: einzelne Dateien oder Playlists (.m3u) laden
• <b>CD</b>: Audio-CD aus dem Laufwerk lesen
• Dateien oder Ordner einfach auf den Player ziehen
• <b>EJECT</b>: Disc auswerfen · Rechtsklick auf freie Fläche: Menü

<b>Laufwerk</b>
• <b>▶❚❚</b> Play/Pause · <b>■</b> Stopp · <b>⏮ ⏭</b> Titel zurück/vor
  (⏮ nach mehr als 3 s: zurück zum Titelanfang)
• Klick auf die Disc: Play/Pause · Disc mit der Maus drehen: scratchen/spulen
• Mausrad über der Disc: ±2 s

<b>Ziffernblock</b>
• Titelnummer tippen, dann <b>ENTER</b> → springt zum Titel
• <b>TIME</b>: vergangene Zeit ↔ Restzeit · gedrückt halten: Key Lock an/aus
• <b>CLR</b>: Eingabe löschen; ohne Eingabe: Wiederholen umschalten
• <b>CLR</b> gedrückt halten: Zufall an/aus

<b>MEMORY A · B · C</b>
• Leere Taste: Merkpunkt an der aktuellen Stelle setzen (LED leuchtet)
• Belegte Taste: dorthin springen und spielen
• Gedrückt halten: Merkpunkt neu setzen · Rechtsklick oder Shift+Klick: löschen
• Merkpunkte werden pro Titel gespeichert

<b>SHUTTLE</b> Schieber nach links/rechts ziehen: Rück-/Vorlauf, je weiter, desto schneller (bis 16×)

<b>TEMPO</b> Fader ziehen (hoch = schneller) oder Mausrad, Shift = fein, Doppelklick = 100 %.
Bereich 50–150 %. <b>KEY LOCK</b> aus = Tempo und Tonhöhe ändern sich gemeinsam (Varispeed),
KEY LOCK an = nur das Tempo ändert sich, die Tonhöhe bleibt (Time Stretch).

<b>VOLUME</b> Drehregler ziehen oder Mausrad · <b>REPEAT</b> aus/alle/einer · <b>SHUFFLE</b> Zufall

<b>Display</b> TRACK = aktueller Titel · TOTAL = Anzahl Titel · TIME = Minuten:Sekunden.
Rechts leuchten REPEAT, SHUFFLE, KEY LOCK, PAUSE und REMAIN (Restzeit). Klick aufs Display: Zeitmodus.

<b>Oben</b> <b>OUTPUT</b> öffnet die GNOME-Klangeinstellungen (Ausgabegerät) · <b>HELP</b> diese Hilfe ·
<b>POWER</b> Standby, gedrückt halten = Beenden · <b>MEDIA</b>-LED: mit der GNOME-Mediensteuerung verbunden

<b>Tastatur</b>
<tt>Leertaste</tt> Play/Pause · <tt>Esc</tt> Stopp · <tt>N</tt>/<tt>B</tt> oder Bild↓/Bild↑ Titel
<tt>←/→</tt> ±5 s (Shift ±30 s) · <tt>↑/↓</tt> Lautstärke · <tt>0–9</tt> + <tt>Enter</tt> Titelwahl
<tt>+</tt>/<tt>-</tt> Tempo ±1 · <tt>#</tt> Tempo 100 · <tt>M</tt> Key Lock
<tt>Q W E</tt> Memory A–C (Shift = setzen) · <tt>T</tt> Zeitmodus · <tt>R</tt> Wiederholen · <tt>S</tt> Zufall
<tt>O</tt> Ordner · <tt>Strg+O</tt> Dateien · <tt>D</tt> Audio-CD · <tt>J</tt> Auswerfen · <tt>P</tt> Power
<tt>Strg +/−/0</tt> Größe · <tt>F1</tt>/<tt>H</tt> Hilfe · <tt>Strg+Q</tt> Beenden
Fenster verschieben: freie Fläche ziehen · Größe ändern: rechte untere Ecke ziehen

<b>GNOME</b> Medientasten, Sperrbildschirm und die Mediensteuerung im Benachrichtigungsbereich
funktionieren über MPRIS. Während der Wiedergabe wird der Ruhezustand verhindert.
"""


SELFTEST = os.environ.get("TMPLAYER_SELFTEST")


def main(argv=None):
    app = PlayerApp()
    app.exit_code = 0
    rc = app.run(argv if argv is not None else sys.argv)
    return rc or app.exit_code
