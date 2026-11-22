"""Audio-Engine auf Basis von GStreamer (playbin).

Varispeed  = Tempo UND Tonhöhe ändern sich gemeinsam (wie bei einem echten CD-Player).
Time Stretch = nur das Tempo ändert sich, die Tonhöhe bleibt (scaletempo).
"""
import re
import threading

import gi

gi.require_version("Gst", "1.0")
from gi.repository import GLib, GObject, Gst  # noqa: E402

Gst.init(None)

PLAY_FLAG_AUDIO = 1 << 1
PLAY_FLAG_SOFT_VOLUME = 1 << 4

# z. B. "peak=(double){ -6.1, -5.9 }" oder "peak=(GValueArray)< -6.1, -5.9 >"
_LEVEL_RE = re.compile(r"peak=\((?:double|GValueArray)\)\s*[{<]\s*([^}>]*)[}>]")


def has_element(name):
    return Gst.ElementFactory.find(name) is not None


class Engine(GObject.Object):
    __gsignals__ = {
        "state-changed": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "tags-changed": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "duration-changed": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "eos": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "gapless-advance": (GObject.SignalFlags.RUN_FIRST, None, ()),
        "error": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        "level": (GObject.SignalFlags.RUN_FIRST, None, (float, float)),
        "seeked": (GObject.SignalFlags.RUN_FIRST, None, (GObject.TYPE_INT64,)),
    }

    def __init__(self):
        super().__init__()
        self.pb = Gst.ElementFactory.make("playbin", "tmplayer")
        if self.pb is None:
            raise RuntimeError("GStreamer 'playbin' fehlt (Paket gstreamer1.0-plugins-base).")
        self.pb.set_property("flags", PLAY_FLAG_AUDIO | PLAY_FLAG_SOFT_VOLUME)
        self.has_pitch = has_element("pitch")          # soundtouch, gst-plugins-bad
        self.has_scaletempo = has_element("scaletempo")
        self.has_level = has_element("level")
        self.stretch = False
        self.rate = 1.0
        self.state = "stopped"          # stopped | playing | paused
        self.uri = None
        self.tags = {}
        self.cover = None               # Bytes des eingebetteten Covers
        self._pending = None            # (start_ns, play) bis ASYNC_DONE
        self._next_uri = None           # für lückenlose Wiedergabe
        self._next_lock = threading.Lock()
        self._gapless_switch = False
        self._pitch = None
        self._build_filter()
        self.pb.connect("about-to-finish", self._on_about_to_finish)
        bus = self.pb.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self._on_message)

    # ------------------------------------------------------------ Filterkette
    def _build_filter(self):
        parts = []
        if self.has_scaletempo and (self.stretch or self.has_pitch):
            parts.append("scaletempo")
            parts.append("audioconvert")
        if self.has_pitch:
            parts.append("pitch name=pitch")
            parts.append("audioconvert")
        if self.has_level:
            parts.append("level name=lvl interval=40000000 post-messages=true")
        parts.append("audioconvert")
        bin_ = Gst.parse_bin_from_description(" ! ".join(parts), True)
        self._pitch = bin_.get_by_name("pitch")
        self.pb.set_property("audio-filter", bin_)
        self._apply_pitch()

    def _apply_pitch(self):
        if self._pitch is not None:
            # scaletempo hält die Tonhöhe; für Varispeed wird sie hier wieder mitgezogen.
            self._pitch.set_property("pitch", 1.0 if self.stretch else self.rate)

    # ------------------------------------------------------------ Steuerung
    def load(self, uri, play=True, start_ns=0):
        self.pb.set_state(Gst.State.READY)
        with self._next_lock:
            self._next_uri = None
        self.uri = uri
        self.tags = {}
        self.cover = None
        self.pb.set_property("uri", uri)
        self._pending = (start_ns, play)
        self.pb.set_state(Gst.State.PAUSED)
        self.emit("tags-changed")

    def set_next_uri(self, uri):
        """Nächster Titel für lückenlose Wiedergabe (nur bei Rate 1.0)."""
        with self._next_lock:
            self._next_uri = uri

    def play(self):
        if self.uri is None:
            return
        if self._pending is not None:          # lädt gerade → danach spielen
            self._pending = (self._pending[0], True)
            return
        if self.state == "stopped":
            self.load(self.uri, play=True)
            return
        self.pb.set_state(Gst.State.PLAYING)
        self._set_state("playing")

    def pause(self):
        if self._pending is not None:
            self._pending = (self._pending[0], False)
            return
        if self.state == "playing":
            self.pb.set_state(Gst.State.PAUSED)
            self._set_state("paused")

    def toggle(self):
        if self.state == "playing":
            self.pause()
        else:
            self.play()

    def stop(self):
        self.pb.set_state(Gst.State.READY)
        self._pending = None
        self._set_state("stopped")

    def unload(self):
        self.pb.set_state(Gst.State.NULL)
        self.uri = None
        self._set_state("stopped")

    def _set_state(self, s):
        if s != self.state:
            self.state = s
            self.emit("state-changed")

    # ------------------------------------------------------------ Zeit
    def position(self):
        if self.state == "stopped":
            return 0
        ok, pos = self.pb.query_position(Gst.Format.TIME)
        return pos if ok and pos >= 0 else 0

    def duration(self):
        if self.uri is None:
            return 0
        ok, dur = self.pb.query_duration(Gst.Format.TIME)
        return dur if ok and dur > 0 else 0

    def seek(self, ns, accurate=True):
        if self.uri is None:
            return
        if self._pending is not None:          # lädt gerade → Startposition merken
            self._pending = (max(0, int(ns)), self._pending[1])
            return
        if self.state == "stopped":
            self.load(self.uri, play=False, start_ns=ns)
            return
        dur = self.duration()
        ns = max(0, ns)
        if dur:
            ns = min(ns, dur - Gst.MSECOND * 50)
        flags = Gst.SeekFlags.FLUSH | (Gst.SeekFlags.ACCURATE if accurate else Gst.SeekFlags.KEY_UNIT)
        self.pb.seek(self.rate, Gst.Format.TIME, flags, Gst.SeekType.SET, ns, Gst.SeekType.NONE, -1)
        self.emit("seeked", ns)

    # ------------------------------------------------------------ Varispeed
    def set_rate(self, rate):
        rate = max(0.25, min(4.0, rate))
        if abs(rate - self.rate) < 1e-4:
            return
        self.rate = rate
        self._apply_pitch()
        if self.state != "stopped" and self._pending is None:
            pos = self.position()
            self.pb.seek(self.rate, Gst.Format.TIME, Gst.SeekFlags.FLUSH | Gst.SeekFlags.ACCURATE,
                         Gst.SeekType.SET, pos, Gst.SeekType.NONE, -1)

    def set_stretch(self, on):
        if on == self.stretch:
            return
        self.stretch = on
        if self.has_pitch:
            self._apply_pitch()        # Filterkette bleibt, nur Tonhöhe umschalten
            return
        # Ohne soundtouch: Kette neu bauen (geht nur im READY-Zustand)
        was, pos = self.state, self.position()
        self.pb.set_state(Gst.State.READY)
        self._build_filter()
        if was != "stopped":
            self._pending = (pos, was == "playing")
            self.pb.set_state(Gst.State.PAUSED)

    def resolution(self):
        """z. B. '44.1 kHz · 16 bit · FLAC' bzw. '44.1 kHz · 320 kbps · MP3'."""
        rate = bits = None
        try:
            pad = self.pb.emit("get-audio-pad", 0)
            caps = pad.get_current_caps() if pad else None
            if caps and caps.get_size():
                st = caps.get_structure(0)
                ok, r = st.get_int("rate")
                rate = r if ok else None
                fmt = st.get_string("format") or ""
                if fmt.startswith(("S16", "U16")):
                    bits = 16
                elif fmt.startswith(("S24", "U24")):
                    bits = 24
                elif fmt.startswith(("S32", "U32")):
                    bits = 32
                elif fmt.startswith(("S8", "U8")):
                    bits = 8
        except (TypeError, AttributeError):
            pass
        parts = []
        if rate:
            parts.append(("%.1f" % (rate / 1000)).rstrip("0").rstrip(".") + " kHz")
        codec = (self.tags.get("codec") or "").upper()
        lossy = any(k in codec for k in ("MPEG", "MP3", "AAC", "VORBIS", "OPUS", "WMA"))
        br = self.tags.get("bitrate")
        if lossy and br:
            parts.append("%d kbps" % round(br / 1000))
        elif bits:
            parts.append("%d bit" % bits)
        if self.uri:
            if self.uri.startswith("cdda://"):
                parts.append("CD")
            else:
                ext = self.uri.rsplit(".", 1)[-1].upper() if "." in self.uri[-6:] else ""
                if ext:
                    parts.append(ext)
        return " · ".join(parts)

    def set_volume(self, v):
        self.pb.set_property("volume", max(0.0, min(1.0, v)))

    # ------------------------------------------------------------ Bus
    def _on_about_to_finish(self, _pb):
        # läuft im Streaming-Thread
        with self._next_lock:
            nxt = self._next_uri
            self._next_uri = None
        if nxt and abs(self.rate - 1.0) < 1e-4:
            self.pb.set_property("uri", nxt)
            self._gapless_switch = True
            self._gapless_uri = nxt

    def _on_message(self, _bus, msg):
        t = msg.type
        if t == Gst.MessageType.ASYNC_DONE and self._pending is not None:
            start, play = self._pending
            self._pending = None
            if start > 0 or abs(self.rate - 1.0) > 1e-4:
                self.pb.seek(self.rate, Gst.Format.TIME,
                             Gst.SeekFlags.FLUSH | Gst.SeekFlags.ACCURATE,
                             Gst.SeekType.SET, start, Gst.SeekType.NONE, -1)
            if play:
                self.pb.set_state(Gst.State.PLAYING)
                self._set_state("playing")
            else:
                self._set_state("paused")
            self.emit("duration-changed")
        elif t == Gst.MessageType.STREAM_START:
            if self._gapless_switch:
                self._gapless_switch = False
                self.uri = self._gapless_uri
                self.tags = {}
                self.cover = None
                self.emit("gapless-advance")
                self.emit("tags-changed")
        elif t == Gst.MessageType.EOS:
            self.emit("eos")
        elif t == Gst.MessageType.ERROR:
            err, dbg = msg.parse_error()
            self.pb.set_state(Gst.State.READY)
            self._pending = None
            self._set_state("stopped")
            self.emit("error", err.message if err else "Fehler")
        elif t == Gst.MessageType.TAG:
            self._read_tags(msg.parse_tag())
        elif t == Gst.MessageType.DURATION_CHANGED:
            self.emit("duration-changed")
        elif t == Gst.MessageType.ELEMENT:
            s = msg.get_structure()
            if s is not None and s.get_name() == "level":
                self._read_level(s)

    def _read_tags(self, tl):
        changed = False
        for key, tag in (("title", Gst.TAG_TITLE), ("artist", Gst.TAG_ARTIST),
                         ("album", Gst.TAG_ALBUM), ("track", Gst.TAG_TRACK_NUMBER),
                         ("codec", Gst.TAG_AUDIO_CODEC), ("bitrate", Gst.TAG_BITRATE),
                         ("genre", Gst.TAG_GENRE)):
            if tag in (Gst.TAG_TRACK_NUMBER, Gst.TAG_BITRATE):
                ok, val = tl.get_uint(tag)
            else:
                ok, val = tl.get_string(tag)
            if ok and val and self.tags.get(key) != val:
                self.tags[key] = val
                changed = True
        if self.cover is None:
            for tag in (Gst.TAG_IMAGE, Gst.TAG_PREVIEW_IMAGE):
                ok, sample = tl.get_sample(tag)
                if ok and sample is not None:
                    buf = sample.get_buffer()
                    ok, info = buf.map(Gst.MapFlags.READ)
                    if ok:
                        self.cover = bytes(info.data)
                        buf.unmap(info)
                        changed = True
                        break
        if changed:
            self.emit("tags-changed")

    def _read_level(self, s):
        vals = None
        try:
            v = s.get_value("peak")
            vals = [float(x) for x in (v.values if hasattr(v, "values") else v)]
        except (TypeError, ValueError, AttributeError):
            pass
        if not vals:
            # GValueArray lässt sich in PyGObject nicht immer direkt lesen → aus Text parsen.
            m = _LEVEL_RE.search(s.to_string())
            if not m:
                return
            try:
                vals = [float(x) for x in m.group(1).split(",") if x.strip()]
            except ValueError:
                return
        if not vals:
            return
        l = vals[0]
        r = vals[1] if len(vals) > 1 else l

        def norm(db):  # -48 dB … 0 dB → 0 … 1
            return max(0.0, min(1.0, (db + 48.0) / 48.0))

        self.emit("level", norm(l), norm(r))


# ---------------------------------------------------------------- Audio-CD
def probe_cd(callback, device=None):
    """Ermittelt im Hintergrund die Anzahl der Titel einer Audio-CD.
    callback(anzahl_oder_0, fehlermeldung_oder_None) im Hauptthread."""

    def work():
        if not has_element("cdparanoiasrc") and not has_element("cdiocddasrc"):
            GLib.idle_add(callback, 0, "Kein CD-Plugin (cdparanoia) installiert")
            return
        pb = Gst.ElementFactory.make("playbin", None)
        pb.set_property("uri", "cdda://1")
        pb.set_property("audio-sink", Gst.ElementFactory.make("fakesink", None))
        if device:
            pb.connect("source-setup", lambda _p, src: src.set_property("device", device))
        pb.set_state(Gst.State.PAUSED)
        res, _s, _p = pb.get_state(15 * Gst.SECOND)
        n = 0
        if res != Gst.StateChangeReturn.FAILURE:
            fmt = Gst.Format.get_by_nick("track")
            ok, cnt = pb.query_duration(fmt)
            if ok and cnt > 0:
                n = int(cnt)
        pb.set_state(Gst.State.NULL)
        GLib.idle_add(callback, n, None if n else "Keine Audio-CD gefunden")

    threading.Thread(target=work, daemon=True).start()
