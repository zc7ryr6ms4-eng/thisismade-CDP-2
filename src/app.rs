//! thisismade CDP-2r – Bedienlogik (Port von tmplayer/app.py).

use crate::engine::{probe_cd, Engine, Event, PlayState};
use crate::face::{self, now, DrawState};
use crate::mpris::Mpris;
use gtk::prelude::*;
use gtk::{gdk_pixbuf, gio, glib};
use serde_json::{json, Value};
use std::cell::{Cell, RefCell};
use std::collections::{HashMap, HashSet};
use std::path::{Path, PathBuf};
use std::rc::Rc;
use std::time::Duration;

pub const APP_ID: &str = "io.github.thisismade.cdp2r";
pub const APP_NAME: &str = "thisismade CDP-2r";
pub const VERSION: &str = env!("CARGO_PKG_VERSION");
pub const CFG_NAME: &str = "thisismade-cdp-2r";
pub const VS_MIN: i32 = 50;
pub const VS_MAX: i32 = 150;

pub const AUDIO_EXT: &[&str] = &[
    "mp3", "flac", "ogg", "oga", "opus", "wav", "wave", "aif", "aiff", "aifc", "m4a", "m4b", "mp4", "aac",
    "wma", "ape", "wv", "mka", "mpc", "tta", "ac3", "dsf", "dff", "spx", "caf", "mp2",
];
pub const PLAYLIST_EXT: &[&str] = &["m3u", "m3u8"];
const COVER_NAMES: &[&str] = &["cover", "folder", "front", "album", "albumart", "albumartsmall", "artwork"];

pub const SCRUB_NS_PER_TURN: f64 = 1.8e9; // eine Disc-Umdrehung = 1,8 s
const DISC_RPS: f64 = 0.55; // sichtbare Umdrehungen pro Sekunde bei 100 %

#[derive(Clone, Debug)]
pub struct Track {
    pub uri: String,
    pub title: String,
    pub path: Option<String>,
    pub album: Option<String>,
}

#[derive(Clone, Debug, Default)]
pub struct Info {
    pub uri: String,
    pub title: String,
    pub artist: Option<String>,
    pub album: Option<String>,
    pub path: Option<String>,
    pub track: Option<u32>,
    pub codec: Option<String>,
    pub bitrate: Option<u32>,
    pub art_url: Option<String>,
}

/// Laufende Maus-Aktion (Python: SimpleNamespace act)
pub struct Act {
    pub seq: u64,
    pub id: String,
    pub btn: u32,
    pub shift: bool,
    pub x: f64,
    pub y: f64,
    pub long_done: bool,
    pub long_src: Option<glib::SourceId>,
    pub moved: f64,
    pub start: i32,
    pub jog_timer: Option<glib::SourceId>,
    pub prev_angle: f64,
    pub was_playing: bool,
    pub scrub: f64,
    pub last_seek: f64,
}

pub struct App {
    pub gapp: gtk::Application,
    pub engine: Rc<Engine>,
    pub mpris: RefCell<Option<Rc<Mpris>>>,
    pub win: RefCell<Option<gtk::ApplicationWindow>>,
    pub area: RefCell<Option<gtk::DrawingArea>>,
    pub menu: RefCell<Option<gtk::PopoverMenu>>,

    pub tracks: RefCell<Vec<Track>>,
    pub order: RefCell<Vec<usize>>,
    pub opos: Cell<usize>,
    pub index: Cell<i64>,
    next_index: Cell<Option<usize>>,
    cues: RefCell<HashMap<String, [Option<i64>; 3]>>,
    pub repeat: Cell<i32>, // 0 aus, 1 alle, 2 einer
    pub shuffle: Cell<bool>,
    pub time_mode: Cell<i32>, // 0 vergangen, 1 Rest
    pub varispeed: Cell<i32>,
    pub level: Cell<i32>,
    pub entry: RefCell<String>,
    entry_time: Cell<f64>,
    msg: RefCell<String>,
    msg_until: Cell<f64>,
    pub power_on: Cell<bool>,
    pub pressed: RefCell<HashSet<String>>,
    pub jog: Cell<f64>,
    pub jog_held: Cell<bool>,
    pub disc_angle: Cell<f64>,
    pub scrubbing: Cell<bool>,
    vu: Cell<[f64; 2]>,
    vu_target: Cell<[f64; 2]>,
    peaks: Cell<[f64; 2]>,
    peak_t: Cell<[f64; 2]>,
    cover_surface: RefCell<Option<cairo::ImageSurface>>,
    art_url: RefCell<Option<String>>,
    disc_lines: RefCell<Vec<String>>,
    inhibit: Cell<u32>,
    errors: Cell<usize>,
    pub vs_timer: RefCell<Option<glib::SourceId>>,
    settings: RefCell<Value>,
    pub zoom: Cell<f64>,
    res_t: Cell<f64>,
    res_cache: RefCell<String>,
    pub exit_code: Cell<i32>,
    pub selftest: Option<String>,
    st_levels: Cell<u32>,
    st_pos1: Cell<i64>,

    // Fenster-Zustand
    pub bg: RefCell<Option<(cairo::Surface, (i32, i32))>>,
    pub fit_cache: Cell<(f64, f64, f64)>,
    pub mouse: Cell<(f64, f64)>,
    pub act: RefCell<Option<Act>>,
    pub act_seq: Cell<u64>,
    pub last_frame: Cell<Option<f64>>,
    pub idle_acc: Cell<f64>,
    pub last_knob: RefCell<(String, f64)>,
}

// ---------------------------------------------------------------- Hilfen
#[derive(PartialEq, Eq, PartialOrd, Ord)]
enum NatPart {
    S(String),
    N(u128),
}

fn natkey(s: &str) -> Vec<NatPart> {
    let mut out = Vec::new();
    let mut cur = String::new();
    let mut digit = false;
    for ch in s.to_lowercase().chars() {
        let d = ch.is_ascii_digit();
        if d != digit {
            if digit {
                out.push(NatPart::N(cur.parse().unwrap_or(u128::MAX)));
            } else {
                out.push(NatPart::S(std::mem::take(&mut cur)));
            }
            cur.clear();
            digit = d;
        }
        cur.push(ch);
    }
    if digit {
        out.push(NatPart::N(cur.parse().unwrap_or(u128::MAX)));
        out.push(NatPart::S(String::new())); // wie Pythons re.split
    } else {
        out.push(NatPart::S(cur));
    }
    out
}

fn config_dir() -> PathBuf {
    let base = glib::user_config_dir();
    let d = base.join(CFG_NAME);
    let old = base.join("thisismade-cdp-2"); // Python-Fassung: Einstellungen übernehmen
    if !d.is_dir() && old.join("settings.json").is_file() {
        let _ = std::fs::create_dir_all(&d);
        let _ = std::fs::copy(old.join("settings.json"), d.join("settings.json"));
    }
    let _ = std::fs::create_dir_all(&d);
    d
}

fn cache_dir() -> PathBuf {
    let d = glib::user_cache_dir().join(CFG_NAME);
    let _ = std::fs::create_dir_all(&d);
    d
}

pub fn uri_to_path(uri: &str) -> Option<String> {
    if uri.starts_with("file://") {
        glib::filename_from_uri(uri).ok().map(|(p, _)| p.to_string_lossy().into_owned())
    } else {
        None
    }
}

fn path_to_uri(p: &str) -> String {
    glib::filename_to_uri(p, None).map(|s| s.to_string()).unwrap_or_else(|_| format!("file://{p}"))
}

fn ext_of(p: &Path) -> String {
    p.extension().map(|e| e.to_string_lossy().to_lowercase()).unwrap_or_default()
}

fn surface_from_bytes(data: &[u8], size: i32) -> Option<cairo::ImageSurface> {
    let res = (|| -> Result<cairo::ImageSurface, String> {
        let loader = gdk_pixbuf::PixbufLoader::new();
        loader.write(data).map_err(|e| e.to_string())?;
        loader.close().map_err(|e| e.to_string())?;
        let pb = loader.pixbuf().ok_or("kein Bild")?;
        let (w, h) = (pb.width(), pb.height());
        let s = w.min(h);
        let pb = pb.new_subpixbuf((w - s) / 2, (h - s) / 2, s, s);
        let pb = pb
            .scale_simple(size, size, gdk_pixbuf::InterpType::Bilinear)
            .ok_or("Skalieren fehlgeschlagen")?;
        let buf = pb.save_to_bufferv("png", &[]).map_err(|e| e.to_string())?;
        cairo::ImageSurface::create_from_png(&mut std::io::Cursor::new(buf)).map_err(|e| e.to_string())
    })();
    match res {
        Ok(s) => Some(s),
        Err(e) => {
            eprintln!("Cover nicht lesbar: {e}");
            None
        }
    }
}

pub fn launch(argv: &[&str]) {
    let args: Vec<&std::ffi::OsStr> = argv.iter().map(std::ffi::OsStr::new).collect();
    if let Err(e) = gio::Subprocess::newv(&args, gio::SubprocessFlags::NONE) {
        eprintln!("Konnte nicht starten: {} {e}", argv.join(" "));
    }
}

// ====================================================================== App
impl App {
    pub fn new(gapp: gtk::Application, engine: Rc<Engine>) -> Rc<App> {
        Rc::new(App {
            gapp,
            engine,
            mpris: RefCell::new(None),
            win: RefCell::new(None),
            area: RefCell::new(None),
            menu: RefCell::new(None),
            tracks: RefCell::new(Vec::new()),
            order: RefCell::new(Vec::new()),
            opos: Cell::new(0),
            index: Cell::new(-1),
            next_index: Cell::new(None),
            cues: RefCell::new(HashMap::new()),
            repeat: Cell::new(0),
            shuffle: Cell::new(false),
            time_mode: Cell::new(0),
            varispeed: Cell::new(100),
            level: Cell::new(80),
            entry: RefCell::new(String::new()),
            entry_time: Cell::new(0.0),
            msg: RefCell::new(String::new()),
            msg_until: Cell::new(0.0),
            power_on: Cell::new(true),
            pressed: RefCell::new(HashSet::new()),
            jog: Cell::new(0.0),
            jog_held: Cell::new(false),
            disc_angle: Cell::new(0.0),
            scrubbing: Cell::new(false),
            vu: Cell::new([0.0; 2]),
            vu_target: Cell::new([0.0; 2]),
            peaks: Cell::new([0.0; 2]),
            peak_t: Cell::new([0.0; 2]),
            cover_surface: RefCell::new(None),
            art_url: RefCell::new(None),
            disc_lines: RefCell::new(Vec::new()),
            inhibit: Cell::new(0),
            errors: Cell::new(0),
            vs_timer: RefCell::new(None),
            settings: RefCell::new(json!({})),
            zoom: Cell::new(0.0),
            res_t: Cell::new(-10.0),
            res_cache: RefCell::new(String::new()),
            exit_code: Cell::new(0),
            selftest: std::env::var("TMPLAYER_SELFTEST").ok().filter(|s| !s.is_empty()),
            st_levels: Cell::new(0),
            st_pos1: Cell::new(0),
            bg: RefCell::new(None),
            fit_cache: Cell::new((1.0, 0.0, 0.0)),
            mouse: Cell::new((0.0, 0.0)),
            act: RefCell::new(None),
            act_seq: Cell::new(0),
            last_frame: Cell::new(None),
            idle_acc: Cell::new(0.0),
            last_knob: RefCell::new((String::new(), 0.0)),
        })
    }

    // ------------------------------------------------------------ Lebenszyklus
    pub fn startup(self: &Rc<Self>) {
        let prov = gtk::CssProvider::new();
        prov.load_from_string(
            "window.tmplayer, window.tmplayer > widget { background: none; box-shadow: none; }",
        );
        if let Some(display) = gtk::gdk::Display::default() {
            gtk::style_context_add_provider_for_display(
                &display,
                &prov,
                gtk::STYLE_PROVIDER_PRIORITY_APPLICATION,
            );
        }
        let weak = Rc::downgrade(self);
        self.engine.set_handler(Rc::new(move |ev| {
            if let Some(a) = weak.upgrade() {
                a.on_engine(ev);
            }
        }));
        self.load_settings();
        self.engine.set_volume((self.level.get() as f64 / 100.0).powi(3));
        let stretch = self.settings.borrow().get("stretch").and_then(Value::as_bool).unwrap_or(false);
        self.engine.set_stretch(stretch);
        self.engine.set_rate(self.varispeed.get() as f64 / 100.0);

        type Cb = fn(&Rc<App>);
        let actions: [(&str, Cb); 10] = [
            ("open-folder", |a| a.open_folder_dialog()),
            ("open-files", |a| a.open_files_dialog()),
            ("open-cd", |a| a.open_cd()),
            ("repeat", |a| a.cycle_repeat()),
            ("shuffle", |a| a.set_shuffle(!a.shuffle.get())),
            ("stretch", |a| a.toggle_stretch()),
            ("eject", |a| a.eject()),
            ("help", |a| a.show_help()),
            ("about", |a| a.show_about()),
            ("quit", |a| a.quit_app()),
        ];
        for (name, cb) in actions {
            let act = gio::SimpleAction::new(name, None);
            let a = self.clone();
            act.connect_activate(move |_, _| cb(&a));
            self.gapp.add_action(&act);
        }
        self.gapp.set_accels_for_action("app.quit", &["<Ctrl>q"]);
        self.gapp.set_accels_for_action("app.open-files", &["<Ctrl>o"]);
        self.gapp.set_accels_for_action("app.help", &["F1"]);
        *self.mpris.borrow_mut() = Some(Mpris::new(self));
        let a = self.clone();
        glib::timeout_add_seconds_local(10, move || {
            a.autosave();
            glib::ControlFlow::Continue
        });
    }

    pub fn activate(self: &Rc<Self>) {
        if self.win.borrow().is_none() {
            self.build_window();
            if self.selftest.is_some() {
                let a = self.clone();
                glib::idle_add_local_once(move || a.selftest_start());
            } else {
                self.restore_session();
            }
        }
        if let Some(w) = self.win.borrow().clone() {
            w.present();
        }
    }

    pub fn open(self: &Rc<Self>, files: &[gio::File]) {
        self.activate();
        self.open_gfiles(files);
    }

    pub fn shutdown(&self) {
        if self.selftest.is_none() {
            self.save_settings();
        }
        self.engine.unload();
        if let Some(m) = self.mpris.borrow().as_ref() {
            m.close();
        }
    }

    // ------------------------------------------------------------ Selbsttest (CI)
    /// TMPLAYER_SELFTEST=<audiodatei>: spielt die Datei ohne Soundkarte ab,
    /// prüft Wiedergabe, Pegel, Tempo und speichert einen Screenshot.
    fn selftest_start(self: &Rc<Self>) {
        if let Ok(sink) = gst::ElementFactory::make("fakesink").property("sync", true).build() {
            self.engine.pb.set_property("audio-sink", &sink); // in Echtzeit, wie eine Soundkarte
        }
        let path = self.selftest.clone().unwrap_or_default();
        self.open_gfiles(&[gio::File::for_path(path)]);
        let a = self.clone();
        glib::timeout_add_local_once(Duration::from_millis(1500), move || a.selftest_tempo());
    }

    fn selftest_tempo(self: &Rc<Self>) {
        self.st_pos1.set(self.engine.position());
        self.set_varispeed(130, true);
        self.cue_set(0);
        let a = self.clone();
        glib::timeout_add_local_once(Duration::from_millis(1500), move || a.selftest_finish());
    }

    fn selftest_finish(self: &Rc<Self>) {
        let pos2 = self.engine.position();
        let pos1_s = self.st_pos1.get() as f64 / 1e9;
        let pos2_s = pos2 as f64 / 1e9;
        let cue = self.cues_now()[0].is_some();
        let res = json!({
            "state": self.engine.state().as_str(), "pos1_s": pos1_s, "pos2_s": pos2_s,
            "levels": self.st_levels.get(), "tracks": self.tracks.borrow().len(),
            "pitch": self.engine.has_pitch, "scaletempo": self.engine.has_scaletempo, "cue": cue,
            "resolution": self.engine.resolution(), "title": self.title_text(),
        });
        let out = std::env::var("TMPLAYER_SCREENSHOT").unwrap_or_else(|_| "screenshot.png".into());
        if let Ok(surf) =
            cairo::ImageSurface::create(cairo::Format::ARgb32, face::CANVAS_W as i32, face::CANVAS_H as i32)
        {
            if let Ok(cr) = cairo::Context::new(&surf) {
                cr.translate(face::MARGIN_X, face::MARGIN_TOP);
                crate::design::draw(&cr, &self.state());
            }
            surf.flush();
            match std::fs::File::create(&out) {
                Ok(mut f) => {
                    if let Err(e) = surf.write_to_png(&mut f) {
                        eprintln!("Screenshot nicht gespeichert: {e}");
                    }
                }
                Err(e) => eprintln!("Screenshot nicht gespeichert: {e}"),
            }
        }
        let ok = self.engine.state() == PlayState::Playing
            && pos1_s > 0.5
            && pos2_s > pos1_s
            && self.st_levels.get() > 5
            && self.tracks.borrow().len() == 1
            && cue;
        println!("SELFTEST {} {}", if ok { "OK" } else { "FAILED" }, res);
        self.exit_code.set(if ok { 0 } else { 1 });
        self.gapp.quit();
    }

    pub fn quit_app(self: &Rc<Self>) {
        self.flash("bYE", 0.4);
        let g = self.gapp.clone();
        glib::timeout_add_local_once(Duration::from_millis(250), move || g.quit());
    }

    pub fn on_mpris_ready(&self) {
        self.redraw();
    }

    pub fn mpris_raise(&self) {
        if let Some(w) = self.win.borrow().clone() {
            w.present();
        }
    }

    // ------------------------------------------------------------ Einstellungen
    fn settings_path() -> PathBuf {
        config_dir().join("settings.json")
    }

    fn load_settings(&self) {
        let s: Value = std::fs::read_to_string(Self::settings_path())
            .ok()
            .and_then(|t| serde_json::from_str(&t).ok())
            .filter(Value::is_object)
            .unwrap_or_else(|| json!({}));
        let num = |k: &str, d: f64| s.get(k).and_then(Value::as_f64).unwrap_or(d);
        self.level.set(num("level", 80.0) as i32);
        self.varispeed.set(num("varispeed", 100.0) as i32);
        self.repeat.set(num("repeat", 0.0) as i32);
        self.shuffle.set(s.get("shuffle").and_then(Value::as_bool).unwrap_or(false));
        self.time_mode.set(num("time_mode", 0.0) as i32);
        self.zoom.set(num("zoom", 0.0));
        let mut cues = HashMap::new();
        if let Some(obj) = s.get("cues").and_then(Value::as_object) {
            for (k, v) in obj {
                if let Some(arr) = v.as_array() {
                    if arr.len() == 3 {
                        let c = [arr[0].as_i64(), arr[1].as_i64(), arr[2].as_i64()];
                        cues.insert(k.clone(), c);
                    }
                }
            }
        }
        *self.cues.borrow_mut() = cues;
        *self.settings.borrow_mut() = s;
    }

    pub fn save_settings(&self) {
        let cues: serde_json::Map<String, Value> = self
            .cues
            .borrow()
            .iter()
            .filter(|(_, v)| v.iter().any(Option::is_some))
            .map(|(k, v)| (k.clone(), json!(v)))
            .collect();
        let uris: Vec<String> = self
            .tracks
            .borrow()
            .iter()
            .filter(|t| t.uri.starts_with("file://"))
            .take(5000)
            .map(|t| t.uri.clone())
            .collect();
        let s = json!({
            "level": self.level.get(), "varispeed": self.varispeed.get(), "repeat": self.repeat.get(),
            "shuffle": self.shuffle.get(), "time_mode": self.time_mode.get(),
            "stretch": self.engine.stretch(), "cues": cues, "zoom": self.current_zoom(),
            "uris": uris, "index": self.index.get(), "position": self.engine.position(),
        });
        let path = Self::settings_path();
        let tmp = path.with_extension("json.tmp");
        let res = std::fs::write(&tmp, s.to_string()).and_then(|_| std::fs::rename(&tmp, &path));
        if let Err(e) = res {
            eprintln!("Einstellungen nicht gespeichert: {e}");
        }
    }

    fn autosave(&self) {
        if self.engine.state() == PlayState::Playing {
            self.save_settings();
        }
    }

    fn restore_session(self: &Rc<Self>) {
        let (uris, idx, pos) = {
            let s = self.settings.borrow();
            let uris: Vec<String> = s
                .get("uris")
                .and_then(Value::as_array)
                .map(|a| a.iter().filter_map(|v| v.as_str().map(String::from)).collect())
                .unwrap_or_default();
            (
                uris,
                s.get("index").and_then(Value::as_i64).unwrap_or(0),
                s.get("position").and_then(Value::as_i64).unwrap_or(0),
            )
        };
        let uris: Vec<String> =
            uris.into_iter().filter(|u| uri_to_path(u).is_some_and(|p| Path::new(&p).exists())).collect();
        if uris.is_empty() {
            return;
        }
        self.set_tracks(uris.iter().map(|u| Self::track_for_uri(u)).collect(), false);
        if idx >= 0 && (idx as usize) < self.tracks.borrow().len() {
            self.play_index(idx as usize, false, pos);
        }
    }

    // ------------------------------------------------------------ Titel laden
    fn track_for_uri(uri: &str) -> Track {
        let p = uri_to_path(uri);
        let title = match &p {
            Some(p) => Path::new(p).file_stem().map(|s| s.to_string_lossy().into_owned()).unwrap_or_default(),
            None => uri.to_string(),
        };
        Track { uri: uri.to_string(), title, path: p, album: None }
    }

    fn scan(path: &Path, out: &mut Vec<String>) {
        if path.is_dir() {
            let Ok(rd) = std::fs::read_dir(path) else { return };
            let mut entries: Vec<String> =
                rd.filter_map(|e| e.ok()).map(|e| e.file_name().to_string_lossy().into_owned()).collect();
            entries.sort_by_cached_key(|e| natkey(e));
            let files: Vec<&String> = entries.iter().filter(|e| !e.starts_with('.')).collect();
            for e in &files {
                let full = path.join(e);
                if full.is_file() && AUDIO_EXT.contains(&ext_of(&full).as_str()) {
                    out.push(full.to_string_lossy().into_owned());
                }
            }
            for e in &files {
                let full = path.join(e);
                if full.is_dir() {
                    Self::scan(&full, out);
                }
            }
        } else if path.is_file() {
            let ext = ext_of(path);
            if AUDIO_EXT.contains(&ext.as_str()) {
                out.push(path.to_string_lossy().into_owned());
            } else if PLAYLIST_EXT.contains(&ext.as_str()) {
                let base = path.parent().map(Path::to_path_buf).unwrap_or_default();
                let Ok(bytes) = std::fs::read(path) else { return };
                for ln in String::from_utf8_lossy(&bytes).lines() {
                    let ln = ln.trim();
                    if ln.is_empty() || ln.starts_with('#') {
                        continue;
                    }
                    let ln = if ln.starts_with("file://") {
                        match uri_to_path(ln) {
                            Some(p) => p,
                            None => continue,
                        }
                    } else {
                        ln.to_string()
                    };
                    let p = Path::new(&ln);
                    let full = if p.is_absolute() { p.to_path_buf() } else { base.join(p) };
                    if full.is_file() {
                        out.push(full.to_string_lossy().into_owned());
                    }
                }
            }
        }
    }

    pub fn open_gfiles(self: &Rc<Self>, gfiles: &[gio::File]) {
        let mut paths = Vec::new();
        let mut others = Vec::new();
        for gf in gfiles {
            match gf.path() {
                Some(p) => Self::scan(&p, &mut paths),
                None => others.push(gf.uri().to_string()),
            }
        }
        let mut tracks: Vec<Track> = paths.iter().map(|p| Self::track_for_uri(&path_to_uri(p))).collect();
        for u in others {
            if u.starts_with("cdda://") {
                self.open_cd();
                return;
            }
            let un = glib::Uri::unescape_string(&u, None::<&str>).map(|s| s.to_string()).unwrap_or(u.clone());
            let base = un.rsplit('/').next().unwrap_or("").to_string();
            let title = if base.is_empty() { u.clone() } else { base };
            tracks.push(Track { uri: u, title, path: None, album: None });
        }
        if !tracks.is_empty() {
            self.set_tracks(tracks, true);
        } else {
            self.flash("no AUdio", 1.0);
        }
    }

    pub fn open_uris(self: &Rc<Self>, uris: &[String]) {
        let files: Vec<gio::File> = uris.iter().map(|u| gio::File::for_uri(u)).collect();
        self.open_gfiles(&files);
    }

    fn set_tracks(self: &Rc<Self>, tracks: Vec<Track>, autoplay: bool) {
        self.engine.stop();
        let n = tracks.len();
        *self.tracks.borrow_mut() = tracks;
        self.entry.borrow_mut().clear();
        self.make_order(None);
        self.flash(&format!("LoAd {n:3}"), 1.0);
        if autoplay {
            let first = self.order.borrow().first().copied();
            if let Some(f) = first {
                self.play_index(f, true, 0);
            }
        }
        self.mpris_changed(&["Metadata", "CanGoNext", "CanGoPrevious", "CanPlay", "CanPause", "CanSeek"]);
    }

    pub fn eject(self: &Rc<Self>) {
        self.engine.unload();
        self.tracks.borrow_mut().clear();
        self.order.borrow_mut().clear();
        self.index.set(-1);
        *self.cover_surface.borrow_mut() = None;
        self.disc_lines.borrow_mut().clear();
        self.flash("EJECt", 1.0);
        self.mpris_changed(&["Metadata", "PlaybackStatus", "CanGoNext", "CanGoPrevious", "CanPlay"]);
    }

    pub fn open_cd(self: &Rc<Self>) {
        self.flash("rEAd  cd", 15.0);
        let a = self.clone();
        glib::MainContext::default().spawn_local(async move {
            let (n, err) = gio::spawn_blocking(probe_cd).await.unwrap_or((0, Some("CD-Prüfung abgebrochen".into())));
            if n > 0 {
                let tracks = (1..=n)
                    .map(|i| Track {
                        uri: format!("cdda://{i}"),
                        title: format!("TRACK {i:02}"),
                        path: None,
                        album: Some("AUDIO CD".into()),
                    })
                    .collect();
                a.set_tracks(tracks, true);
                a.flash(&format!("cd   {n:3} tr"), 1.5);
            } else {
                a.flash("no  cd", 1.5);
                if let Some(e) = err {
                    eprintln!("{e}");
                }
            }
        });
    }

    fn make_order(&self, keep: Option<usize>) {
        let n = self.tracks.borrow().len();
        let mut order: Vec<usize> = (0..n).collect();
        if self.shuffle.get() && n > 1 {
            for i in (1..n).rev() {
                let j = glib::random_int_range(0, i as i32 + 1) as usize;
                order.swap(i, j);
            }
            if let Some(k) = keep {
                if let Some(pos) = order.iter().position(|x| *x == k) {
                    order.remove(pos);
                    order.insert(0, k);
                }
            }
        }
        let opos = keep.and_then(|k| order.iter().position(|x| *x == k)).unwrap_or(0);
        *self.order.borrow_mut() = order;
        self.opos.set(opos);
    }

    pub fn has_tracks(&self) -> bool {
        !self.tracks.borrow().is_empty() && self.index.get() >= 0
    }

    fn cur_index(&self) -> Option<usize> {
        let i = self.index.get();
        if i >= 0 && (i as usize) < self.tracks.borrow().len() {
            Some(i as usize)
        } else {
            None
        }
    }

    // ------------------------------------------------------------ Transport
    pub fn play_index(self: &Rc<Self>, i: usize, play: bool, start_ns: i64) {
        let uri = match self.tracks.borrow().get(i) {
            Some(t) => t.uri.clone(),
            None => return,
        };
        self.index.set(i as i64);
        let pos = self.order.borrow().iter().position(|x| *x == i);
        if let Some(p) = pos {
            self.opos.set(p);
        }
        self.engine.load(&uri, play, start_ns);
        self.prepare_next();
        self.update_disc();
        self.mpris_changed(&["Metadata", "PlaybackStatus"]);
    }

    fn next_in_order(&self, wrap: bool) -> Option<usize> {
        let order = self.order.borrow();
        if order.is_empty() {
            return None;
        }
        let mut p = self.opos.get() + 1;
        if p >= order.len() {
            if !wrap {
                return None;
            }
            p = 0;
        }
        Some(order[p])
    }

    fn prev_in_order(&self) -> Option<usize> {
        let order = self.order.borrow();
        if order.is_empty() {
            return None;
        }
        let p = if self.opos.get() == 0 { order.len() - 1 } else { self.opos.get() - 1 };
        Some(order[p])
    }

    fn prepare_next(&self) {
        let nxt = if self.repeat.get() == 2 {
            self.cur_index()
        } else {
            self.next_in_order(self.repeat.get() == 1)
        };
        self.next_index.set(nxt);
        let uri = nxt.and_then(|n| self.tracks.borrow().get(n).map(|t| t.uri.clone()));
        self.engine.set_next_uri(uri);
    }

    pub fn play(self: &Rc<Self>) {
        if !self.power_on.get() {
            return;
        }
        if !self.has_tracks() {
            let first = self.order.borrow().first().copied();
            match first {
                Some(f) if !self.tracks.borrow().is_empty() => self.play_index(f, true, 0),
                _ => self.flash("no  dISC", 1.0),
            }
            return;
        }
        self.engine.play();
    }

    pub fn pause(&self) {
        self.engine.pause();
    }

    pub fn play_pause(self: &Rc<Self>) {
        if self.engine.state() == PlayState::Playing {
            self.pause();
        } else {
            self.play();
        }
    }

    pub fn stop(&self) {
        self.engine.stop();
        self.redraw();
    }

    pub fn next_track(self: &Rc<Self>) {
        if self.tracks.borrow().is_empty() {
            return;
        }
        if let Some(n) = self.next_in_order(true) {
            self.play_index(n, true, 0);
        }
    }

    pub fn prev_track(self: &Rc<Self>, force: bool) {
        if self.tracks.borrow().is_empty() {
            return;
        }
        if !force && self.engine.position() as f64 > 3e9 {
            self.seek_to(0);
            return;
        }
        if let Some(p) = self.prev_in_order() {
            self.play_index(p, true, 0);
        }
    }

    pub fn seek_to(&self, ns: i64) {
        self.engine.seek(ns);
    }

    pub fn seek_relative(&self, delta_ns: f64) {
        self.engine.seek((self.engine.position() as f64 + delta_ns) as i64);
    }

    fn jump_to_track(self: &Rc<Self>, n: usize) {
        if n >= 1 && n <= self.tracks.borrow().len() {
            self.play_index(n - 1, true, 0);
        } else {
            self.flash(&format!("Err  {n:3}"), 1.0);
        }
    }

    // ------------------------------------------------------------ Modi
    pub fn set_repeat(&self, r: i32) {
        self.repeat.set(r.rem_euclid(3));
        self.flash(["rEP  oFF", "rEP  ALL", "rEP  onE"][self.repeat.get() as usize], 1.0);
        if self.has_tracks() {
            self.prepare_next();
        }
        self.mpris_changed(&["LoopStatus"]);
    }

    pub fn cycle_repeat(&self) {
        self.set_repeat(self.repeat.get() + 1);
    }

    pub fn set_shuffle(&self, on: bool) {
        self.shuffle.set(on);
        self.make_order(self.cur_index());
        if self.has_tracks() {
            self.prepare_next();
        }
        self.flash(if on { "SHUF  on" } else { "SHUF  oFF" }, 1.0);
        self.mpris_changed(&["Shuffle"]);
    }

    pub fn toggle_time_mode(&self) {
        self.time_mode.set(1 - self.time_mode.get());
        self.flash(if self.time_mode.get() == 0 { "ELAPSEd" } else { "rEnAIn" }, 0.8);
    }

    pub fn toggle_stretch(&self) {
        self.engine.set_stretch(!self.engine.stretch());
        self.flash(if self.engine.stretch() { "LoCK  on" } else { "LoCK  oFF" }, 1.0);
    }

    pub fn set_varispeed(self: &Rc<Self>, v: i32, immediate: bool) {
        let v = v.clamp(VS_MIN, VS_MAX);
        if v == self.varispeed.get() {
            return;
        }
        self.varispeed.set(v);
        self.redraw();
        if immediate {
            self.apply_varispeed();
        } else if self.vs_timer.borrow().is_none() {
            let a = self.clone();
            let id = glib::timeout_add_local_once(Duration::from_millis(110), move || a.apply_varispeed());
            *self.vs_timer.borrow_mut() = Some(id);
        }
    }

    pub fn apply_varispeed(&self) {
        // Die Quelle ist entweder schon abgelaufen oder läuft harmlos noch einmal.
        let _ = self.vs_timer.borrow_mut().take();
        self.engine.set_rate(self.varispeed.get() as f64 / 100.0);
        self.mpris_changed(&["Rate"]);
    }

    pub fn set_level(&self, v: i32) {
        let v = v.clamp(0, 100);
        if v != self.level.get() {
            self.level.set(v);
            self.engine.set_volume((v as f64 / 100.0).powi(3));
            self.mpris_changed(&["Volume"]);
            self.redraw();
        }
    }

    pub fn toggle_power(&self) {
        self.power_on.set(!self.power_on.get());
        if !self.power_on.get() {
            self.engine.pause();
        } else {
            self.flash("HELLo", 0.6);
        }
        self.redraw();
    }

    // ------------------------------------------------------------ Cue
    fn cues_now(&self) -> [Option<i64>; 3] {
        let Some(i) = self.cur_index() else { return [None; 3] };
        let uri = self.tracks.borrow()[i].uri.clone();
        *self.cues.borrow_mut().entry(uri).or_insert([None; 3])
    }

    fn set_cue_value(&self, i: usize, v: Option<i64>) {
        let Some(idx) = self.cur_index() else { return };
        let uri = self.tracks.borrow()[idx].uri.clone();
        self.cues.borrow_mut().entry(uri).or_insert([None; 3])[i] = v;
    }

    pub fn cue_press(self: &Rc<Self>, i: usize) {
        if !self.has_tracks() {
            self.flash("no  dISC", 1.0);
            return;
        }
        match self.cues_now()[i] {
            None => self.cue_set(i),
            Some(ns) => {
                self.seek_to(ns);
                if self.engine.state() != PlayState::Playing {
                    self.play();
                }
                self.flash(&format!("CUE {}", i + 1), 0.6);
            }
        }
    }

    pub fn cue_set(&self, i: usize) {
        if !self.has_tracks() {
            return;
        }
        self.set_cue_value(i, Some(self.engine.position()));
        self.flash(&format!("CUE {}  SEt", i + 1), 0.8);
    }

    pub fn cue_clear(&self, i: usize) {
        if self.has_tracks() {
            self.set_cue_value(i, None);
            self.flash(&format!("CUE {}  CLr", i + 1), 0.8);
        }
    }

    // ------------------------------------------------------------ Ziffernblock
    pub fn keypad(&self, k: &str) {
        let t = now();
        if k.len() == 1 && k.chars().all(|c| c.is_ascii_digit()) {
            if t - self.entry_time.get() > 4.0 {
                self.entry.borrow_mut().clear();
            }
            let mut e = self.entry.borrow_mut();
            e.push_str(k);
            let len = e.chars().count();
            if len > 3 {
                *e = e.chars().skip(len - 3).collect();
            }
            drop(e);
            self.entry_time.set(t);
        } else if k == "T" {
            self.toggle_time_mode();
        } else if k == "C" {
            let has = !self.entry.borrow().is_empty();
            if has {
                self.entry.borrow_mut().clear();
            } else {
                self.cycle_repeat();
            }
        }
        self.redraw();
    }

    pub fn keypad_long(&self, k: &str) {
        if k == "C" {
            self.set_shuffle(!self.shuffle.get());
        } else if k == "T" {
            self.toggle_stretch();
        }
    }

    pub fn enter(self: &Rc<Self>) {
        let entry = self.entry.borrow().clone();
        if !entry.is_empty() && now() - self.entry_time.get() < 4.0 {
            self.entry.borrow_mut().clear();
            self.jump_to_track(entry.parse().unwrap_or(0));
        } else {
            self.entry.borrow_mut().clear();
            self.play_pause();
        }
        self.redraw();
    }

    // ------------------------------------------------------------ Engine-Events
    fn on_engine(self: &Rc<Self>, ev: Event) {
        match ev {
            Event::StateChanged => self.on_state(),
            Event::TagsChanged => {
                self.update_disc();
                self.mpris_changed(&["Metadata"]);
            }
            Event::DurationChanged => self.mpris_changed(&["Metadata"]),
            Event::Eos => self.on_eos(),
            Event::GaplessAdvance => self.on_gapless(),
            Event::Error(t) => self.on_error(&t),
            Event::Level(l, r) => {
                self.vu_target.set([l, r]);
                self.st_levels.set(self.st_levels.get() + 1);
            }
            Event::Seeked(ns) => {
                let m = self.mpris.borrow().clone();
                if let Some(m) = m {
                    m.seeked(ns);
                }
            }
        }
    }

    fn on_state(&self) {
        let playing = self.engine.state() == PlayState::Playing;
        if playing && self.inhibit.get() == 0 {
            if let Some(w) = self.win.borrow().clone() {
                let c = self.gapp.inhibit(Some(&w), gtk::ApplicationInhibitFlags::SUSPEND, Some("Musikwiedergabe"));
                self.inhibit.set(c);
            }
        } else if !playing && self.inhibit.get() != 0 {
            self.gapp.uninhibit(self.inhibit.get());
            self.inhibit.set(0);
        }
        if playing {
            self.errors.set(0);
        }
        self.mpris_changed(&["PlaybackStatus", "Metadata"]);
        self.redraw();
    }

    fn on_eos(self: &Rc<Self>) {
        if self.repeat.get() == 2 {
            self.seek_to(0);
            self.engine.play();
            return;
        }
        match self.next_in_order(self.repeat.get() == 1) {
            None => {
                self.engine.stop();
                let first = self.order.borrow().first().copied();
                if let Some(f) = first {
                    self.play_index(f, false, 0);
                    self.engine.stop();
                }
                self.flash("End", 1.2);
            }
            Some(n) => self.play_index(n, true, 0),
        }
    }

    fn on_gapless(&self) {
        if let Some(n) = self.next_index.get() {
            self.index.set(n as i64);
            let pos = self.order.borrow().iter().position(|x| *x == n);
            if let Some(p) = pos {
                self.opos.set(p);
            }
        }
        self.prepare_next();
        self.update_disc();
        self.mpris_changed(&["Metadata"]);
    }

    fn on_error(self: &Rc<Self>, text: &str) {
        eprintln!("Wiedergabefehler: {text}");
        self.flash("Err", 1.2);
        self.errors.set(self.errors.get() + 1);
        if self.errors.get() < self.tracks.borrow().len() {
            if let Some(n) = self.next_in_order(self.repeat.get() == 1) {
                let a = self.clone();
                glib::timeout_add_local_once(Duration::from_millis(400), move || a.play_index(n, true, 0));
            }
        }
    }

    // ------------------------------------------------------------ Disc-Aufdruck
    pub fn current_info(&self) -> Option<Info> {
        if !self.has_tracks() {
            return None;
        }
        let i = self.cur_index()?;
        let t = self.tracks.borrow()[i].clone();
        let tg = self.engine.tags();
        Some(Info {
            uri: t.uri,
            title: tg.title.unwrap_or(t.title),
            artist: tg.artist,
            album: tg.album.or(t.album),
            path: t.path,
            track: tg.track,
            codec: tg.codec,
            bitrate: tg.bitrate,
            art_url: self.art_url.borrow().clone(),
        })
    }

    fn update_disc(&self) {
        let Some(info) = self.current_info() else { return };
        let mut lines: Vec<String> = vec![info.title.clone()];
        for v in [&info.artist, &info.album].into_iter().flatten() {
            if !v.is_empty() {
                lines.push(v.clone());
            }
        }
        lines.push(format!("TRACK {:02} / {:02}", self.index.get() + 1, self.tracks.borrow().len()));
        if let Some(codec) = info.codec.as_ref().filter(|c| !c.is_empty()) {
            let br = match info.bitrate {
                Some(b) if b > 0 => format!(" {} KBPS", b / 1000),
                _ => String::new(),
            };
            lines.push(format!("{codec}{br}"));
        }
        *self.disc_lines.borrow_mut() = lines
            .into_iter()
            .filter(|x| !x.is_empty())
            .map(|x| x.to_uppercase().chars().take(30).collect())
            .collect();

        let mut data = self.engine.cover();
        let mut url: Option<String> = None;
        if let Some(d) = data.as_ref() {
            let h = glib::compute_checksum_for_data(glib::ChecksumType::Md5, d)
                .map(|s| s.chars().take(16).collect::<String>())
                .unwrap_or_default();
            let fname = cache_dir().join(format!("cover-{h}.img"));
            if !fname.exists() {
                let _ = std::fs::write(&fname, d);
            }
            url = Some(path_to_uri(&fname.to_string_lossy()));
        } else if let Some(p) = info.path.as_ref() {
            if let Some(dir) = Path::new(p).parent() {
                if let Ok(rd) = std::fs::read_dir(dir) {
                    let mut names: Vec<String> =
                        rd.filter_map(|e| e.ok()).map(|e| e.file_name().to_string_lossy().into_owned()).collect();
                    names.sort();
                    for e in names {
                        let ep = Path::new(&e);
                        let b = ep.file_stem().map(|s| s.to_string_lossy().to_lowercase()).unwrap_or_default();
                        let ext = ext_of(ep);
                        if ["jpg", "jpeg", "png", "webp"].contains(&ext.as_str()) && COVER_NAMES.contains(&b.as_str())
                        {
                            let full = dir.join(&e);
                            url = Some(path_to_uri(&full.to_string_lossy()));
                            data = std::fs::read(&full).ok();
                            break;
                        }
                    }
                }
            }
        }
        if url != *self.art_url.borrow() {
            *self.art_url.borrow_mut() = url;
            *self.cover_surface.borrow_mut() = data.as_deref().and_then(|d| surface_from_bytes(d, 640));
        }
        self.redraw();
    }

    // ------------------------------------------------------------ Anzeige
    pub fn flash(&self, text: &str, secs: f64) {
        *self.msg.borrow_mut() = text.to_string();
        self.msg_until.set(now() + secs);
        self.redraw();
    }

    pub fn redraw(&self) {
        if let Some(a) = self.area.borrow().as_ref() {
            a.queue_draw();
        }
    }

    pub fn mpris_changed(&self, names: &[&str]) {
        let m = self.mpris.borrow().clone();
        if let Some(m) = m {
            m.changed(names);
        }
    }

    fn msg_active(&self) -> bool {
        !self.msg.borrow().is_empty() && now() < self.msg_until.get()
    }

    fn display_main(&self) -> String {
        let t = now();
        let blink = (t * 2.0) as i64 % 2 == 0;
        if self.msg_active() {
            return self.msg.borrow().clone();
        }
        let ntracks = self.tracks.borrow().len();
        if ntracks == 0 {
            return "------------".into();
        }
        let idx0 = self.index.get();
        let mut tr = format!("{:03}", if idx0 >= 0 { idx0 + 1 } else { 0 });
        let entry = self.entry.borrow().clone();
        if !entry.is_empty() && t - self.entry_time.get() < 4.0 {
            tr = if blink { format!("{entry:->3}") } else { "   ".into() };
        }
        let idx = format!("{:03}", ntracks.min(999));
        let pos = self.engine.position();
        let dur = self.engine.duration();
        let (mut tm, ss);
        if self.time_mode.get() == 1 && dur > 0 {
            let rem = (dur - pos).max(0) as f64 / 1e9;
            let total = (rem + 0.999) as i64;
            let mm = total / 60;
            ss = total % 60;
            tm = format!("-{:02}", mm.min(99));
        } else {
            let total = (pos as f64 / 1e9) as i64;
            let mm = total / 60;
            ss = total % 60;
            tm = format!("{:03}", mm.min(999));
        }
        let mut sec = format!("{ss:03}");
        if self.engine.state() == PlayState::Paused && !blink {
            tm = "   ".into();
            sec = "   ".into();
        }
        format!("{tr}{idx}{tm}{sec}")
    }

    pub fn title_text(&self) -> String {
        let Some(info) = self.current_info() else { return String::new() };
        let mut t = info.title.clone();
        if let Some(a) = info.artist.as_ref().filter(|a| !a.is_empty()) {
            t = format!("{a} – {t}");
        }
        t.to_uppercase()
    }

    fn res_text(&self) -> String {
        let t = now();
        if t - self.res_t.get() > 1.0 {
            // Caps höchstens 1× pro Sekunde abfragen
            self.res_t.set(t);
            *self.res_cache.borrow_mut() = if self.has_tracks() { self.engine.resolution() } else { String::new() };
        }
        self.res_cache.borrow().clone()
    }

    pub fn state(&self) -> DrawState {
        let cues = self.cues_now();
        let vu = self.vu.get();
        DrawState {
            pressed: self.pressed.borrow().clone(),
            disc_loaded: !self.tracks.borrow().is_empty(),
            disc_angle: self.disc_angle.get(),
            disc_lines: self.disc_lines.borrow().clone(),
            cover: self.cover_surface.borrow().clone(),
            bt_led: self.mpris.borrow().as_ref().is_some_and(|m| m.connected()),
            power_on: self.power_on.get(),
            vu_l: vu[0],
            vu_r: vu[1],
            vu_peaks: self.peaks.get(),
            main_text: self.display_main(),
            vs_text: format!("{:03}", self.varispeed.get()),
            lv_text: format!("{:03}", self.level.get()),
            stretch: self.engine.stretch(),
            cue_set: [cues[0].is_some(), cues[1].is_some(), cues[2].is_some()],
            varispeed_norm: (self.varispeed.get() - VS_MIN) as f64 / (VS_MAX - VS_MIN) as f64,
            level_norm: self.level.get() as f64 / 100.0,
            jog: self.jog.get(),
            repeat: self.repeat.get(),
            shuffle: self.shuffle.get(),
            paused: self.engine.state() == PlayState::Paused,
            remain: self.time_mode.get() == 1,
            msg_mode: self.msg_active(),
            title: self.title_text(),
            resolution: self.res_text(),
        }
    }

    /// Wird pro Frame aufgerufen. Gibt true zurück, wenn neu gezeichnet werden soll.
    pub fn animate(&self, dt: f64, t: f64) -> bool {
        let mut busy = false;
        let playing = self.engine.state() == PlayState::Playing && self.power_on.get();
        if playing && !self.scrubbing.get() {
            self.disc_angle.set(
                self.disc_angle.get()
                    + dt * 2.0 * std::f64::consts::PI * DISC_RPS * self.varispeed.get() as f64 / 100.0,
            );
            busy = true;
        }
        let (mut vu, mut peaks, mut peak_t) = (self.vu.get(), self.peaks.get(), self.peak_t.get());
        let target = self.vu_target.get();
        for i in 0..2 {
            let tgt = if playing { target[i] } else { 0.0 };
            if tgt >= vu[i] {
                vu[i] = tgt;
            } else {
                vu[i] = tgt.max(vu[i] - dt * 1.6);
            }
            if vu[i] >= peaks[i] {
                peaks[i] = vu[i];
                peak_t[i] = t;
            } else if t - peak_t[i] > 0.8 {
                peaks[i] = (peaks[i] - dt * 0.7).max(0.0);
            }
            if vu[i] > 0.001 || peaks[i] > 0.001 {
                busy = true;
            }
        }
        self.vu.set(vu);
        self.peaks.set(peaks);
        self.peak_t.set(peak_t);
        if !playing {
            self.vu_target.set([0.0, 0.0]);
        }
        let jog = self.jog.get();
        if !self.jog_held.get() && jog.abs() > 0.001 {
            let mut j = jog * (1.0 - dt * 14.0).max(0.0);
            if j.abs() < 0.01 {
                j = 0.0;
            }
            self.jog.set(j);
            busy = true;
        }
        busy
    }

    // ------------------------------------------------------------ Dialoge
    pub fn open_folder_dialog(self: &Rc<Self>) {
        let d = gtk::FileDialog::builder().title("Ordner laden (DATA)").build();
        let start = glib::user_special_dir(glib::UserDirectory::Music).unwrap_or_else(glib::home_dir);
        d.set_initial_folder(Some(&gio::File::for_path(start)));
        let a = self.clone();
        let win = self.win.borrow().clone();
        d.select_folder(win.as_ref(), gio::Cancellable::NONE, move |res| {
            if let Ok(f) = res {
                a.open_gfiles(&[f]);
            }
        });
    }

    pub fn open_files_dialog(self: &Rc<Self>) {
        let d = gtk::FileDialog::builder().title("Dateien laden (USB)").build();
        let flt = gtk::FileFilter::new();
        flt.set_name(Some("Audio und Playlists"));
        flt.add_mime_type("audio/*");
        let mut exts: Vec<&str> = AUDIO_EXT.iter().chain(PLAYLIST_EXT.iter()).copied().collect();
        exts.sort();
        for e in exts {
            flt.add_suffix(e);
        }
        let store = gio::ListStore::new::<gtk::FileFilter>();
        store.append(&flt);
        d.set_filters(Some(&store));
        d.set_default_filter(Some(&flt));
        let a = self.clone();
        let win = self.win.borrow().clone();
        d.open_multiple(win.as_ref(), gio::Cancellable::NONE, move |res| {
            if let Ok(model) = res {
                let files: Vec<gio::File> =
                    (0..model.n_items()).filter_map(|i| model.item(i).and_downcast::<gio::File>()).collect();
                if !files.is_empty() {
                    a.open_gfiles(&files);
                }
            }
        });
    }

    pub fn show_about(&self) {
        let mut b = gtk::AboutDialog::builder()
            .modal(true)
            .program_name(APP_NAME)
            .version(VERSION)
            .logo_icon_name(APP_ID)
            .comments("CD-Player-Software für GNOME mit Varispeed, Key Lock, Memory-Cues und Shuttle.")
            .website("https://github.com/zc7ryr6ms4-eng/thisismade-CDP-2r")
            .license_type(gtk::License::Bsd3);
        if let Some(w) = self.win.borrow().as_ref() {
            b = b.transient_for(w);
        }
        b.build().present();
    }

    pub fn show_help(&self) {
        let mut b = gtk::Window::builder()
            .title(format!("{APP_NAME} – Bedienung"))
            .modal(false)
            .default_width(560)
            .default_height(640);
        if let Some(w) = self.win.borrow().as_ref() {
            b = b.transient_for(w);
        }
        let w = b.build();
        let lab = gtk::Label::new(None);
        lab.set_markup(&crate::help_text());
        lab.set_wrap(true);
        lab.set_xalign(0.0);
        lab.set_selectable(true);
        lab.set_margin_top(18);
        lab.set_margin_bottom(18);
        lab.set_margin_start(22);
        lab.set_margin_end(22);
        let sc = gtk::ScrolledWindow::new();
        sc.set_child(Some(&lab));
        w.set_child(Some(&sc));
        w.present();
    }
}

#[cfg(test)]
mod tests {
    use super::natkey;

    #[test]
    fn natural_sort() {
        let mut v = vec!["Track 10.mp3", "track 2.mp3", "Track 1.mp3"];
        v.sort_by_key(|s| natkey(s));
        assert_eq!(v, vec!["Track 1.mp3", "track 2.mp3", "Track 10.mp3"]);
    }
}
