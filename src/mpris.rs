//! MPRIS2-Schnittstelle: GNOME-Mediensteuerung, Medientasten, Sperrbildschirm.

use crate::app::{App, APP_ID, APP_NAME, VS_MAX, VS_MIN};
use crate::engine::PlayState;
use gtk::prelude::*;
use gtk::{gio, glib};
use std::cell::{Cell, RefCell};
use std::rc::{Rc, Weak};

const BUS_NAME: &str = "org.mpris.MediaPlayer2.thisismade_cdp2r";
const PATH: &str = "/org/mpris/MediaPlayer2";
const ROOT_IFACE: &str = "org.mpris.MediaPlayer2";
const PLAYER_IFACE: &str = "org.mpris.MediaPlayer2.Player";

const XML: &str = r#"
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
"#;

const MIME: &[&str] = &[
    "audio/mpeg", "audio/flac", "audio/x-flac", "audio/ogg", "audio/x-vorbis+ogg", "audio/opus", "audio/x-wav",
    "audio/wav", "audio/aac", "audio/mp4", "audio/x-m4a", "audio/x-aiff", "audio/x-ms-wma", "audio/x-ape",
    "audio/x-wavpack", "audio/x-matroska", "audio/x-mpegurl", "x-content/audio-cdda",
];

const LOOP: [&str; 3] = ["None", "Playlist", "Track"];

pub struct Mpris {
    app: Weak<App>,
    conn: RefCell<Option<gio::DBusConnection>>,
    reg: RefCell<Vec<gio::RegistrationId>>,
    owner: Cell<Option<gio::OwnerId>>,
}

fn objpath(s: &str) -> glib::Variant {
    glib::variant::ObjectPath::try_from(s.to_string())
        .map(|p| p.to_variant())
        .unwrap_or_else(|_| glib::variant::ObjectPath::try_from("/".to_string()).unwrap().to_variant())
}

impl Mpris {
    pub fn new(app: &Rc<App>) -> Rc<Mpris> {
        let m = Rc::new(Mpris {
            app: Rc::downgrade(app),
            conn: RefCell::new(None),
            reg: RefCell::new(Vec::new()),
            owner: Cell::new(None),
        });
        let weak = Rc::downgrade(&m);
        let owner = gio::bus_own_name(
            gio::BusType::Session,
            BUS_NAME,
            gio::BusNameOwnerFlags::NONE,
            move |conn, _name| {
                if let Some(m) = weak.upgrade() {
                    m.on_bus(conn);
                }
            },
            |_conn, _name| {},
            |_conn, _name| {},
        );
        m.owner.set(Some(owner));
        m
    }

    pub fn connected(&self) -> bool {
        self.conn.borrow().is_some()
    }

    fn on_bus(self: &Rc<Self>, conn: gio::DBusConnection) {
        let info = match gio::DBusNodeInfo::for_xml(XML) {
            Ok(i) => i,
            Err(e) => {
                eprintln!("MPRIS: {e}");
                return;
            }
        };
        for name in [ROOT_IFACE, PLAYER_IFACE] {
            let Some(iface) = info.lookup_interface(name) else { continue };
            let w1 = Rc::downgrade(self);
            let w2 = Rc::downgrade(self);
            let w3 = Rc::downgrade(self);
            let res = conn
                .register_object(PATH, &iface)
                .method_call(move |_c, _sender, _path, _iface, method, params, inv| {
                    if let Some(m) = w1.upgrade() {
                        m.call(method, &params);
                    }
                    inv.return_value(None);
                })
                .property(move |_c, _sender, _path, iface, prop| {
                    w2.upgrade()
                        .and_then(|m| m.prop(iface, prop))
                        .unwrap_or_else(|| false.to_variant())
                })
                .set_property(move |_c, _sender, _path, _iface, prop, value| {
                    w3.upgrade().map(|m| m.set(prop, &value)).unwrap_or(false)
                })
                .build();
            match res {
                Ok(id) => self.reg.borrow_mut().push(id),
                Err(e) => eprintln!("MPRIS: {e}"),
            }
        }
        *self.conn.borrow_mut() = Some(conn);
        if let Some(a) = self.app.upgrade() {
            a.on_mpris_ready();
        }
    }

    pub fn close(&self) {
        if let Some(conn) = self.conn.borrow().as_ref() {
            for id in self.reg.borrow_mut().drain(..) {
                let _ = conn.unregister_object(id);
            }
        }
        if let Some(o) = self.owner.take() {
            gio::bus_unown_name(o);
        }
    }

    // --------------------------------------------------------------- Methoden
    fn call(&self, method: &str, params: &glib::Variant) {
        let Some(c) = self.app.upgrade() else { return };
        match method {
            "Raise" => c.mpris_raise(),
            "Quit" => {
                glib::idle_add_local_once(move || c.quit_app());
            }
            "Next" => c.next_track(),
            "Previous" => c.prev_track(true),
            "Pause" => c.pause(),
            "PlayPause" => c.play_pause(),
            "Stop" => c.stop(),
            "Play" => c.play(),
            "Seek" => {
                if let Some((off,)) = params.get::<(i64,)>() {
                    c.seek_relative(off as f64 * 1000.0);
                }
            }
            "SetPosition" => {
                if let Some((tid, pos)) = params.get::<(glib::variant::ObjectPath, i64)>() {
                    if tid.as_str() == self.trackid(&c) {
                        c.seek_to(pos * 1000);
                    }
                }
            }
            "OpenUri" => {
                if let Some((u,)) = params.get::<(String,)>() {
                    c.open_uris(&[u]);
                }
            }
            _ => {}
        }
    }

    fn trackid(&self, c: &App) -> String {
        format!("/io/github/thisismade/cdp2r/track/{}", c.index.get().max(0))
    }

    // --------------------------------------------------------------- Eigenschaften
    fn prop(&self, iface: &str, prop: &str) -> Option<glib::Variant> {
        let c = self.app.upgrade()?;
        if iface == ROOT_IFACE {
            return Some(match prop {
                "CanQuit" | "CanRaise" => true.to_variant(),
                "CanSetFullscreen" | "Fullscreen" | "HasTrackList" => false.to_variant(),
                "Identity" => APP_NAME.to_variant(),
                "DesktopEntry" => APP_ID.to_variant(),
                "SupportedUriSchemes" => vec!["file", "cdda"].to_variant(),
                "SupportedMimeTypes" => MIME.to_vec().to_variant(),
                _ => return None,
            });
        }
        let has = c.has_tracks();
        Some(match prop {
            "PlaybackStatus" => match c.engine.state() {
                PlayState::Playing => "Playing",
                PlayState::Paused => "Paused",
                PlayState::Stopped => "Stopped",
            }
            .to_variant(),
            "LoopStatus" => LOOP[c.repeat.get().clamp(0, 2) as usize].to_variant(),
            "Rate" => (c.varispeed.get() as f64 / 100.0).to_variant(),
            "Shuffle" => c.shuffle.get().to_variant(),
            "Metadata" => self.metadata(&c),
            "Volume" => (c.level.get() as f64 / 100.0).to_variant(),
            "Position" => (c.engine.position() / 1000).to_variant(),
            "MinimumRate" => (VS_MIN as f64 / 100.0).to_variant(),
            "MaximumRate" => (VS_MAX as f64 / 100.0).to_variant(),
            "CanGoNext" | "CanGoPrevious" | "CanPlay" | "CanPause" | "CanSeek" => has.to_variant(),
            "CanControl" => true.to_variant(),
            _ => return None,
        })
    }

    fn metadata(&self, c: &App) -> glib::Variant {
        let d = glib::VariantDict::new(None);
        d.insert_value("mpris:trackid", &objpath(&self.trackid(c)));
        if c.has_tracks() {
            if let Some(info) = c.current_info() {
                let dur = c.engine.duration();
                if dur > 0 {
                    d.insert_value("mpris:length", &(dur / 1000).to_variant());
                }
                d.insert_value("xesam:title", &info.title.to_variant());
                if let Some(a) = info.artist.filter(|s| !s.is_empty()) {
                    d.insert_value("xesam:artist", &vec![a].to_variant());
                }
                if let Some(a) = info.album.filter(|s| !s.is_empty()) {
                    d.insert_value("xesam:album", &a.to_variant());
                }
                if !info.uri.is_empty() {
                    d.insert_value("xesam:url", &info.uri.to_variant());
                }
                if let Some(n) = info.track.filter(|n| *n > 0) {
                    d.insert_value("xesam:trackNumber", &(n as i32).to_variant());
                }
                if let Some(u) = info.art_url {
                    d.insert_value("mpris:artUrl", &u.to_variant());
                }
            }
        }
        d.end()
    }

    fn set(&self, prop: &str, value: &glib::Variant) -> bool {
        let Some(c) = self.app.upgrade() else { return false };
        match prop {
            "LoopStatus" => {
                let v = value.str().unwrap_or("None");
                c.set_repeat(LOOP.iter().position(|x| *x == v).unwrap_or(0) as i32);
            }
            "Shuffle" => {
                if let Some(b) = value.get::<bool>() {
                    c.set_shuffle(b);
                }
            }
            "Volume" => {
                if let Some(v) = value.get::<f64>() {
                    c.set_level(crate::face::pyround(v.clamp(0.0, 1.0) * 100.0) as i32);
                }
            }
            "Rate" => {
                if let Some(v) = value.get::<f64>() {
                    if v > 0.0 {
                        c.set_varispeed(crate::face::pyround(v * 100.0) as i32, false);
                    }
                }
            }
            _ => {}
        }
        true
    }

    // --------------------------------------------------------------- Signale
    pub fn changed(&self, names: &[&str]) {
        let conn = self.conn.borrow().clone();
        let Some(conn) = conn else { return };
        let d = glib::VariantDict::new(None);
        let mut any = false;
        for n in names {
            if let Some(v) = self.prop(PLAYER_IFACE, n) {
                d.insert_value(n, &v);
                any = true;
            }
        }
        if !any {
            return;
        }
        let args = glib::Variant::tuple_from_iter([
            PLAYER_IFACE.to_variant(),
            d.end(),
            Vec::<String>::new().to_variant(),
        ]);
        let _ = conn.emit_signal(None, PATH, "org.freedesktop.DBus.Properties", "PropertiesChanged", Some(&args));
    }

    pub fn seeked(&self, ns: i64) {
        let conn = self.conn.borrow().clone();
        if let Some(conn) = conn {
            let _ = conn.emit_signal(None, PATH, PLAYER_IFACE, "Seeked", Some(&(ns / 1000,).to_variant()));
        }
    }
}
