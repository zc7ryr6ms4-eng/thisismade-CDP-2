"""MPRIS2-Schnittstelle: GNOME-Mediensteuerung, Medientasten, Sperrbildschirm."""
from gi.repository import Gio, GLib

BUS_NAME = "org.mpris.MediaPlayer2.thisismade_cdp2"
PATH = "/org/mpris/MediaPlayer2"
ROOT_IFACE = "org.mpris.MediaPlayer2"
PLAYER_IFACE = "org.mpris.MediaPlayer2.Player"

XML = """
<node>
  <interface name="org.mpris.MediaPlayer2">
    <method name="Raise"/>
    <method name="Quit"/>
    <property name="CanQuit" type="b" access="read"/>
    <property name="CanRaise" type="b" access="read"/>
    <property name="CanSetFullscreen" type="b" access="read"/>
    <property name="Fullscreen" type="b" access="read"/>
    <property name="HasTrackList" type="b" access="read"/>
    <property name="Identity" type="s" access="read"/>
    <property name="DesktopEntry" type="s" access="read"/>
    <property name="SupportedUriSchemes" type="as" access="read"/>
    <property name="SupportedMimeTypes" type="as" access="read"/>
  </interface>
  <interface name="org.mpris.MediaPlayer2.Player">
    <method name="Next"/>
    <method name="Previous"/>
    <method name="Pause"/>
    <method name="PlayPause"/>
    <method name="Stop"/>
    <method name="Play"/>
    <method name="Seek"><arg direction="in" name="Offset" type="x"/></method>
    <method name="SetPosition">
      <arg direction="in" name="TrackId" type="o"/>
      <arg direction="in" name="Position" type="x"/>
    </method>
    <method name="OpenUri"><arg direction="in" name="Uri" type="s"/></method>
    <signal name="Seeked"><arg name="Position" type="x"/></signal>
    <property name="PlaybackStatus" type="s" access="read"/>
    <property name="LoopStatus" type="s" access="readwrite"/>
    <property name="Rate" type="d" access="readwrite"/>
    <property name="Shuffle" type="b" access="readwrite"/>
    <property name="Metadata" type="a{sv}" access="read"/>
    <property name="Volume" type="d" access="readwrite"/>
    <property name="Position" type="x" access="read"/>
    <property name="MinimumRate" type="d" access="read"/>
    <property name="MaximumRate" type="d" access="read"/>
    <property name="CanGoNext" type="b" access="read"/>
    <property name="CanGoPrevious" type="b" access="read"/>
    <property name="CanPlay" type="b" access="read"/>
    <property name="CanPause" type="b" access="read"/>
    <property name="CanSeek" type="b" access="read"/>
    <property name="CanControl" type="b" access="read"/>
  </interface>
</node>
"""

MIME = ["audio/mpeg", "audio/flac", "audio/x-flac", "audio/ogg", "audio/x-vorbis+ogg",
        "audio/opus", "audio/x-wav", "audio/wav", "audio/aac", "audio/mp4", "audio/x-m4a",
        "audio/x-aiff", "audio/x-ms-wma", "audio/x-ape", "audio/x-wavpack",
        "audio/x-matroska", "audio/x-mpegurl", "x-content/audio-cdda"]

LOOP = {0: "None", 1: "Playlist", 2: "Track"}
LOOP_R = {v: k for k, v in LOOP.items()}


class Mpris:
    """ctl ist das App-Objekt; es muss die unten benutzten Methoden anbieten."""

    def __init__(self, ctl, desktop_entry):
        self.ctl = ctl
        self.desktop_entry = desktop_entry
        self.conn = None
        self._reg = []
        self.info = Gio.DBusNodeInfo.new_for_xml(XML)
        self._owner = Gio.bus_own_name(Gio.BusType.SESSION, BUS_NAME,
                                       Gio.BusNameOwnerFlags.NONE,
                                       self._on_bus, None, None)

    @property
    def connected(self):
        return self.conn is not None

    def _on_bus(self, conn, _name):
        self.conn = conn
        for iface in self.info.interfaces:
            rid = conn.register_object(PATH, iface, self._call, self._get, self._set)
            self._reg.append(rid)
        self.ctl.on_mpris_ready()

    def close(self):
        if self.conn:
            for rid in self._reg:
                self.conn.unregister_object(rid)
        Gio.bus_unown_name(self._owner)

    # --------------------------------------------------------------- Methoden
    def _call(self, _conn, _sender, _path, iface, method, params, inv):
        c = self.ctl
        args = params.unpack()
        if method == "Raise":
            c.mpris_raise()
        elif method == "Quit":
            GLib.idle_add(c.quit_app)
        elif method == "Next":
            c.next_track()
        elif method == "Previous":
            c.prev_track(force=True)
        elif method == "Pause":
            c.pause()
        elif method == "PlayPause":
            c.play_pause()
        elif method == "Stop":
            c.stop()
        elif method == "Play":
            c.play()
        elif method == "Seek":
            c.seek_relative(args[0] * 1000)
        elif method == "SetPosition":
            if args[0] == self._trackid():
                c.seek_to(args[1] * 1000)
        elif method == "OpenUri":
            c.open_uris([args[0]])
        inv.return_value(None)

    def _trackid(self):
        return "/io/github/thisismade/cdp2/track/%d" % max(0, self.ctl.index)

    # --------------------------------------------------------------- Eigenschaften
    def _props(self, iface):
        c = self.ctl
        if iface == ROOT_IFACE:
            return {
                "CanQuit": GLib.Variant("b", True),
                "CanRaise": GLib.Variant("b", True),
                "CanSetFullscreen": GLib.Variant("b", False),
                "Fullscreen": GLib.Variant("b", False),
                "HasTrackList": GLib.Variant("b", False),
                "Identity": GLib.Variant("s", "thisismade cdp-2"),
                "DesktopEntry": GLib.Variant("s", self.desktop_entry),
                "SupportedUriSchemes": GLib.Variant("as", ["file", "cdda"]),
                "SupportedMimeTypes": GLib.Variant("as", MIME),
            }
        has = c.has_tracks()
        status = {"playing": "Playing", "paused": "Paused"}.get(c.engine.state, "Stopped")
        return {
            "PlaybackStatus": GLib.Variant("s", status),
            "LoopStatus": GLib.Variant("s", LOOP[c.repeat]),
            "Rate": GLib.Variant("d", c.varispeed / 100.0),
            "Shuffle": GLib.Variant("b", c.shuffle),
            "Metadata": GLib.Variant("a{sv}", self._metadata()),
            "Volume": GLib.Variant("d", c.level / 100.0),
            "Position": GLib.Variant("x", int(c.engine.position() // 1000)),
            "MinimumRate": GLib.Variant("d", c.VS_MIN / 100.0),
            "MaximumRate": GLib.Variant("d", c.VS_MAX / 100.0),
            "CanGoNext": GLib.Variant("b", has),
            "CanGoPrevious": GLib.Variant("b", has),
            "CanPlay": GLib.Variant("b", has),
            "CanPause": GLib.Variant("b", has),
            "CanSeek": GLib.Variant("b", has),
            "CanControl": GLib.Variant("b", True),
        }

    def _metadata(self):
        c = self.ctl
        md = {"mpris:trackid": GLib.Variant("o", self._trackid())}
        if not c.has_tracks():
            return md
        info = c.current_info()
        dur = c.engine.duration()
        if dur:
            md["mpris:length"] = GLib.Variant("x", int(dur // 1000))
        md["xesam:title"] = GLib.Variant("s", info.get("title", ""))
        if info.get("artist"):
            md["xesam:artist"] = GLib.Variant("as", [info["artist"]])
        if info.get("album"):
            md["xesam:album"] = GLib.Variant("s", info["album"])
        if info.get("uri"):
            md["xesam:url"] = GLib.Variant("s", info["uri"])
        if info.get("track"):
            md["xesam:trackNumber"] = GLib.Variant("i", int(info["track"]))
        if info.get("art_url"):
            md["mpris:artUrl"] = GLib.Variant("s", info["art_url"])
        return md

    def _get(self, _conn, _sender, _path, iface, prop):
        return self._props(iface).get(prop)

    def _set(self, _conn, _sender, _path, iface, prop, value):
        c = self.ctl
        v = value.unpack()
        if prop == "LoopStatus":
            c.set_repeat(LOOP_R.get(v, 0))
        elif prop == "Shuffle":
            c.set_shuffle(bool(v))
        elif prop == "Volume":
            c.set_level(round(max(0.0, min(1.0, v)) * 100))
        elif prop == "Rate":
            if v > 0:
                c.set_varispeed(round(v * 100))
        return True

    # --------------------------------------------------------------- Signale
    def changed(self, *names):
        if not self.conn:
            return
        props = self._props(PLAYER_IFACE)
        d = {n: props[n] for n in names if n in props}
        if not d:
            return
        self.conn.emit_signal(None, PATH, "org.freedesktop.DBus.Properties", "PropertiesChanged",
                              GLib.Variant("(sa{sv}as)", (PLAYER_IFACE, d, [])))

    def seeked(self, ns):
        if self.conn:
            self.conn.emit_signal(None, PATH, PLAYER_IFACE, "Seeked",
                                  GLib.Variant("(x)", (int(ns // 1000),)))
