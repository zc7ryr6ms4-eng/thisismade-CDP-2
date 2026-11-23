//! Audio-Engine auf Basis von GStreamer (playbin).
//!
//! Varispeed  = Tempo UND Tonhöhe ändern sich gemeinsam (wie bei einem echten CD-Player).
//! Time Stretch = nur das Tempo ändert sich, die Tonhöhe bleibt (scaletempo).

use gst::prelude::*;
use gtk::glib;
use std::cell::{Cell, RefCell};
use std::rc::Rc;
use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};
use std::sync::{Arc, Mutex};

pub const MSECOND: i64 = 1_000_000;

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum PlayState {
    Stopped,
    Playing,
    Paused,
}

impl PlayState {
    pub fn as_str(self) -> &'static str {
        match self {
            PlayState::Stopped => "stopped",
            PlayState::Playing => "playing",
            PlayState::Paused => "paused",
        }
    }
}

pub enum Event {
    StateChanged,
    TagsChanged,
    DurationChanged,
    Eos,
    GaplessAdvance,
    Error(String),
    Level(f64, f64),
    Seeked(i64),
}

#[derive(Default, Clone, Debug)]
pub struct Tags {
    pub title: Option<String>,
    pub artist: Option<String>,
    pub album: Option<String>,
    pub track: Option<u32>,
    pub codec: Option<String>,
    pub bitrate: Option<u32>,
    pub genre: Option<String>,
}

pub fn has_element(name: &str) -> bool {
    gst::ElementFactory::find(name).is_some()
}

pub struct Engine {
    pub pb: gst::Element,
    pub has_pitch: bool,
    pub has_scaletempo: bool,
    pub has_level: bool,
    stretch: Cell<bool>,
    rate: Cell<f64>,
    state: Cell<PlayState>,
    uri: RefCell<Option<String>>,
    tags: RefCell<Tags>,
    cover: RefCell<Option<Vec<u8>>>,
    pending: Cell<Option<(i64, bool)>>, // (start_ns, play) bis ASYNC_DONE
    next_uri: Arc<Mutex<Option<String>>>, // für lückenlose Wiedergabe
    gapless_uri: Arc<Mutex<Option<String>>>,
    gapless_switch: Arc<AtomicBool>,
    rate_bits: Arc<AtomicU64>,
    pitch: RefCell<Option<gst::Element>>,
    handler: RefCell<Option<Rc<dyn Fn(Event)>>>,
    bus_watch: RefCell<Option<gst::bus::BusWatchGuard>>,
}

impl Engine {
    pub fn new() -> Result<Rc<Engine>, String> {
        let pb = gst::ElementFactory::make("playbin")
            .name("tmplayer")
            .build()
            .map_err(|_| "GStreamer 'playbin' fehlt (Paket gstreamer1.0-plugins-base).".to_string())?;
        pb.set_property_from_str("flags", "audio+soft-volume");
        let eng = Rc::new(Engine {
            pb: pb.clone(),
            has_pitch: has_element("pitch"), // soundtouch, gst-plugins-bad
            has_scaletempo: has_element("scaletempo"),
            has_level: has_element("level"),
            stretch: Cell::new(false),
            rate: Cell::new(1.0),
            state: Cell::new(PlayState::Stopped),
            uri: RefCell::new(None),
            tags: RefCell::new(Tags::default()),
            cover: RefCell::new(None),
            pending: Cell::new(None),
            next_uri: Arc::new(Mutex::new(None)),
            gapless_uri: Arc::new(Mutex::new(None)),
            gapless_switch: Arc::new(AtomicBool::new(false)),
            rate_bits: Arc::new(AtomicU64::new(1.0f64.to_bits())),
            pitch: RefCell::new(None),
            handler: RefCell::new(None),
            bus_watch: RefCell::new(None),
        });
        eng.build_filter();

        // about-to-finish läuft im Streaming-Thread
        let next = eng.next_uri.clone();
        let gu = eng.gapless_uri.clone();
        let gs = eng.gapless_switch.clone();
        let rb = eng.rate_bits.clone();
        pb.connect("about-to-finish", false, move |args| {
            let nxt = next.lock().ok().and_then(|mut g| g.take());
            let rate = f64::from_bits(rb.load(Ordering::SeqCst));
            if let Some(n) = nxt {
                if (rate - 1.0).abs() < 1e-4 {
                    if let Ok(p) = args[0].get::<gst::Element>() {
                        p.set_property("uri", n.as_str());
                    }
                    if let Ok(mut g) = gu.lock() {
                        *g = Some(n);
                    }
                    gs.store(true, Ordering::SeqCst);
                }
            }
            None
        });

        let bus = pb.bus().ok_or_else(|| "GStreamer-Bus fehlt".to_string())?;
        let weak = Rc::downgrade(&eng);
        let guard = bus
            .add_watch_local(move |_bus, msg| {
                if let Some(e) = weak.upgrade() {
                    e.on_message(msg);
                }
                glib::ControlFlow::Continue
            })
            .map_err(|e| e.to_string())?;
        *eng.bus_watch.borrow_mut() = Some(guard);
        Ok(eng)
    }

    pub fn set_handler(&self, h: Rc<dyn Fn(Event)>) {
        *self.handler.borrow_mut() = Some(h);
    }

    fn emit(&self, e: Event) {
        let h = self.handler.borrow().clone();
        if let Some(h) = h {
            h(e);
        }
    }

    // ------------------------------------------------------------ Zugriff
    pub fn state(&self) -> PlayState {
        self.state.get()
    }
    pub fn stretch(&self) -> bool {
        self.stretch.get()
    }
    pub fn tags(&self) -> Tags {
        self.tags.borrow().clone()
    }
    pub fn cover(&self) -> Option<Vec<u8>> {
        self.cover.borrow().clone()
    }

    // ------------------------------------------------------------ Filterkette
    fn build_filter(&self) {
        let mut parts: Vec<&str> = Vec::new();
        if self.has_scaletempo && (self.stretch.get() || self.has_pitch) {
            parts.push("scaletempo");
            parts.push("audioconvert");
        }
        if self.has_pitch {
            parts.push("pitch name=pitch");
            parts.push("audioconvert");
        }
        if self.has_level {
            parts.push("level name=lvl interval=40000000 post-messages=true");
        }
        parts.push("audioconvert");
        match gst::parse::bin_from_description(&parts.join(" ! "), true) {
            Ok(bin) => {
                *self.pitch.borrow_mut() = bin.by_name("pitch");
                self.pb.set_property("audio-filter", bin.upcast_ref::<gst::Element>());
            }
            Err(e) => eprintln!("Filterkette nicht gebaut: {e}"),
        }
        self.apply_pitch();
    }

    fn apply_pitch(&self) {
        if let Some(p) = self.pitch.borrow().as_ref() {
            // scaletempo hält die Tonhöhe; für Varispeed wird sie hier wieder mitgezogen.
            let v = if self.stretch.get() { 1.0 } else { self.rate.get() };
            p.set_property("pitch", v as f32);
        }
    }

    // ------------------------------------------------------------ Steuerung
    pub fn load(&self, uri: &str, play: bool, start_ns: i64) {
        let _ = self.pb.set_state(gst::State::Ready);
        if let Ok(mut g) = self.next_uri.lock() {
            *g = None;
        }
        *self.uri.borrow_mut() = Some(uri.to_string());
        *self.tags.borrow_mut() = Tags::default();
        *self.cover.borrow_mut() = None;
        self.pb.set_property("uri", uri);
        self.pending.set(Some((start_ns, play)));
        let _ = self.pb.set_state(gst::State::Paused);
        self.emit(Event::TagsChanged);
    }

    /// Nächster Titel für lückenlose Wiedergabe (nur bei Rate 1.0).
    pub fn set_next_uri(&self, uri: Option<String>) {
        if let Ok(mut g) = self.next_uri.lock() {
            *g = uri;
        }
    }

    pub fn play(&self) {
        let uri = self.uri.borrow().clone();
        let Some(uri) = uri else { return };
        if let Some((s, _)) = self.pending.get() {
            // lädt gerade → danach spielen
            self.pending.set(Some((s, true)));
            return;
        }
        if self.state.get() == PlayState::Stopped {
            self.load(&uri, true, 0);
            return;
        }
        let _ = self.pb.set_state(gst::State::Playing);
        self.set_play_state(PlayState::Playing);
    }

    pub fn pause(&self) {
        if let Some((s, _)) = self.pending.get() {
            self.pending.set(Some((s, false)));
            return;
        }
        if self.state.get() == PlayState::Playing {
            let _ = self.pb.set_state(gst::State::Paused);
            self.set_play_state(PlayState::Paused);
        }
    }

    pub fn stop(&self) {
        let _ = self.pb.set_state(gst::State::Ready);
        self.pending.set(None);
        self.set_play_state(PlayState::Stopped);
    }

    pub fn unload(&self) {
        let _ = self.pb.set_state(gst::State::Null);
        *self.uri.borrow_mut() = None;
        self.set_play_state(PlayState::Stopped);
    }

    fn set_play_state(&self, s: PlayState) {
        if s != self.state.get() {
            self.state.set(s);
            self.emit(Event::StateChanged);
        }
    }

    // ------------------------------------------------------------ Zeit
    pub fn position(&self) -> i64 {
        if self.state.get() == PlayState::Stopped {
            return 0;
        }
        self.pb
            .query_position::<gst::ClockTime>()
            .map(|t| t.nseconds() as i64)
            .unwrap_or(0)
    }

    pub fn duration(&self) -> i64 {
        if self.uri.borrow().is_none() {
            return 0;
        }
        self.pb
            .query_duration::<gst::ClockTime>()
            .map(|t| t.nseconds() as i64)
            .filter(|d| *d > 0)
            .unwrap_or(0)
    }

    fn do_seek(&self, ns: i64) {
        let _ = self.pb.seek(
            self.rate.get(),
            gst::SeekFlags::FLUSH | gst::SeekFlags::ACCURATE,
            gst::SeekType::Set,
            gst::ClockTime::from_nseconds(ns.max(0) as u64),
            gst::SeekType::None,
            gst::ClockTime::NONE,
        );
    }

    pub fn seek(&self, ns: i64) {
        let uri = self.uri.borrow().clone();
        let Some(uri) = uri else { return };
        if let Some((_, p)) = self.pending.get() {
            // lädt gerade → Startposition merken
            self.pending.set(Some((ns.max(0), p)));
            return;
        }
        if self.state.get() == PlayState::Stopped {
            self.load(&uri, false, ns);
            return;
        }
        let dur = self.duration();
        let mut ns = ns.max(0);
        if dur > 0 {
            ns = ns.min(dur - MSECOND * 50).max(0);
        }
        self.do_seek(ns);
        self.emit(Event::Seeked(ns));
    }

    // ------------------------------------------------------------ Varispeed
    pub fn set_rate(&self, rate: f64) {
        let rate = rate.clamp(0.25, 4.0);
        if (rate - self.rate.get()).abs() < 1e-4 {
            return;
        }
        self.rate.set(rate);
        self.rate_bits.store(rate.to_bits(), Ordering::SeqCst);
        self.apply_pitch();
        if self.state.get() != PlayState::Stopped && self.pending.get().is_none() {
            let pos = self.position();
            self.do_seek(pos);
        }
    }

    pub fn set_stretch(&self, on: bool) {
        if on == self.stretch.get() {
            return;
        }
        self.stretch.set(on);
        if self.has_pitch {
            self.apply_pitch(); // Filterkette bleibt, nur Tonhöhe umschalten
            return;
        }
        // Ohne soundtouch: Kette neu bauen (geht nur im READY-Zustand)
        let was = self.state.get();
        let pos = self.position();
        let _ = self.pb.set_state(gst::State::Ready);
        self.build_filter();
        if was != PlayState::Stopped {
            self.pending.set(Some((pos, was == PlayState::Playing)));
            let _ = self.pb.set_state(gst::State::Paused);
        }
    }

    /// z. B. „44.1 kHz · 16 bit · FLAC“ bzw. „44.1 kHz · 320 kbps · MP3“.
    pub fn resolution(&self) -> String {
        let mut rate: Option<i32> = None;
        let mut bits: Option<u32> = None;
        let pad = self.pb.emit_by_name::<Option<gst::Pad>>("get-audio-pad", &[&0i32]);
        if let Some(caps) = pad.and_then(|p| p.current_caps()) {
            if let Some(st) = caps.structure(0) {
                rate = st.get::<i32>("rate").ok();
                let fmt = st.get::<&str>("format").unwrap_or("");
                let pre = |a: &str, b: &str| fmt.starts_with(a) || fmt.starts_with(b);
                bits = if pre("S16", "U16") {
                    Some(16)
                } else if pre("S24", "U24") {
                    Some(24)
                } else if pre("S32", "U32") {
                    Some(32)
                } else if pre("S8", "U8") {
                    Some(8)
                } else {
                    None
                };
            }
        }
        let mut parts: Vec<String> = Vec::new();
        if let Some(r) = rate.filter(|r| *r != 0) {
            let s = format!("{:.1}", r as f64 / 1000.0);
            let s = s.trim_end_matches('0').trim_end_matches('.');
            parts.push(format!("{s} kHz"));
        }
        let tags = self.tags.borrow();
        let codec = tags.codec.clone().unwrap_or_default().to_uppercase();
        let lossy = ["MPEG", "MP3", "AAC", "VORBIS", "OPUS", "WMA"].iter().any(|k| codec.contains(k));
        let br = tags.bitrate.unwrap_or(0);
        if lossy && br > 0 {
            parts.push(format!("{} kbps", (br as f64 / 1000.0).round_ties_even() as i64));
        } else if let Some(b) = bits {
            parts.push(format!("{b} bit"));
        }
        if let Some(uri) = self.uri.borrow().as_ref() {
            if uri.starts_with("cdda://") {
                parts.push("CD".into());
            } else {
                let chars: Vec<char> = uri.chars().collect();
                let tail: String = chars[chars.len().saturating_sub(6)..].iter().collect();
                if tail.contains('.') {
                    let ext = uri.rsplit('.').next().unwrap_or("").to_uppercase();
                    if !ext.is_empty() {
                        parts.push(ext);
                    }
                }
            }
        }
        parts.join(" · ")
    }

    pub fn set_volume(&self, v: f64) {
        self.pb.set_property("volume", v.clamp(0.0, 1.0));
    }

    // ------------------------------------------------------------ Bus
    fn on_message(&self, msg: &gst::Message) {
        use gst::MessageView as MV;
        match msg.view() {
            MV::AsyncDone(_) => {
                if let Some((start, play)) = self.pending.get() {
                    self.pending.set(None);
                    if start > 0 || (self.rate.get() - 1.0).abs() > 1e-4 {
                        self.do_seek(start);
                    }
                    if play {
                        let _ = self.pb.set_state(gst::State::Playing);
                        self.set_play_state(PlayState::Playing);
                    } else {
                        self.set_play_state(PlayState::Paused);
                    }
                    self.emit(Event::DurationChanged);
                }
            }
            MV::StreamStart(_) => {
                if self.gapless_switch.swap(false, Ordering::SeqCst) {
                    let u = self.gapless_uri.lock().ok().and_then(|mut g| g.take());
                    *self.uri.borrow_mut() = u;
                    *self.tags.borrow_mut() = Tags::default();
                    *self.cover.borrow_mut() = None;
                    self.emit(Event::GaplessAdvance);
                    self.emit(Event::TagsChanged);
                }
            }
            MV::Eos(_) => self.emit(Event::Eos),
            MV::Error(err) => {
                let _ = self.pb.set_state(gst::State::Ready);
                self.pending.set(None);
                self.set_play_state(PlayState::Stopped);
                self.emit(Event::Error(err.error().message().to_string()));
            }
            MV::Tag(t) => {
                let tl = t.tags();
                self.read_tags(&tl);
            }
            MV::DurationChanged(_) => self.emit(Event::DurationChanged),
            MV::Element(el) => {
                if let Some(s) = el.structure() {
                    if s.name() == "level" {
                        self.read_level(&s.to_string());
                    }
                }
            }
            _ => {}
        }
    }

    fn read_tags(&self, tl: &gst::TagListRef) {
        fn upd(slot: &mut Option<String>, v: Option<String>, changed: &mut bool) {
            if let Some(v) = v {
                if !v.is_empty() && slot.as_deref() != Some(v.as_str()) {
                    *slot = Some(v);
                    *changed = true;
                }
            }
        }
        fn updn(slot: &mut Option<u32>, v: Option<u32>, changed: &mut bool) {
            if let Some(v) = v {
                if v != 0 && *slot != Some(v) {
                    *slot = Some(v);
                    *changed = true;
                }
            }
        }
        let mut changed = false;
        {
            let mut tg = self.tags.borrow_mut();
            upd(&mut tg.title, tl.get::<gst::tags::Title>().map(|v| v.get().to_string()), &mut changed);
            upd(&mut tg.artist, tl.get::<gst::tags::Artist>().map(|v| v.get().to_string()), &mut changed);
            upd(&mut tg.album, tl.get::<gst::tags::Album>().map(|v| v.get().to_string()), &mut changed);
            updn(&mut tg.track, tl.get::<gst::tags::TrackNumber>().map(|v| v.get()), &mut changed);
            upd(&mut tg.codec, tl.get::<gst::tags::AudioCodec>().map(|v| v.get().to_string()), &mut changed);
            updn(&mut tg.bitrate, tl.get::<gst::tags::Bitrate>().map(|v| v.get()), &mut changed);
            upd(&mut tg.genre, tl.get::<gst::tags::Genre>().map(|v| v.get().to_string()), &mut changed);
        }
        if self.cover.borrow().is_none() {
            let samples = [
                tl.get::<gst::tags::Image>().map(|v| v.get()),
                tl.get::<gst::tags::PreviewImage>().map(|v| v.get()),
            ];
            for sample in samples.into_iter().flatten() {
                if let Some(buf) = sample.buffer() {
                    if let Ok(map) = buf.map_readable() {
                        *self.cover.borrow_mut() = Some(map.as_slice().to_vec());
                        changed = true;
                        break;
                    }
                }
            }
        }
        if changed {
            self.emit(Event::TagsChanged);
        }
    }

    fn read_level(&self, text: &str) {
        let vals = parse_peak(text);
        if vals.is_empty() {
            return;
        }
        let l = vals[0];
        let r = if vals.len() > 1 { vals[1] } else { l };
        // -48 dB … 0 dB → 0 … 1
        let norm = |db: f64| {
            let v = (db + 48.0) / 48.0;
            if v.is_nan() {
                0.0
            } else {
                v.clamp(0.0, 1.0)
            }
        };
        self.emit(Event::Level(norm(l), norm(r)));
    }
}

/// z. B. „peak=(double){ -6.1, -5.9 }“ oder „peak=(GValueArray)< -6.1, -5.9 >“
fn parse_peak(s: &str) -> Vec<f64> {
    let Some(i) = s.find("peak=(") else { return Vec::new() };
    let rest = &s[i + 6..];
    let Some(close) = rest.find(')') else { return Vec::new() };
    let ty = &rest[..close];
    if ty != "double" && ty != "GValueArray" {
        return Vec::new();
    }
    let rest = rest[close + 1..].trim_start();
    if !(rest.starts_with('{') || rest.starts_with('<')) {
        return Vec::new();
    }
    let body = &rest[1..];
    let Some(end) = body.find(['}', '>']) else { return Vec::new() };
    let mut out = Vec::new();
    for part in body[..end].split(',') {
        let p = part.trim();
        if p.is_empty() {
            continue;
        }
        match p.parse::<f64>() {
            Ok(v) => out.push(v),
            Err(_) => return Vec::new(),
        }
    }
    out
}

// ---------------------------------------------------------------- Audio-CD
/// Ermittelt die Anzahl der Titel einer Audio-CD (blockierend, im Hintergrund aufrufen).
pub fn probe_cd() -> (u32, Option<String>) {
    if !has_element("cdparanoiasrc") && !has_element("cdiocddasrc") {
        return (0, Some("Kein CD-Plugin (cdparanoia) installiert".into()));
    }
    let Ok(pb) = gst::ElementFactory::make("playbin").build() else {
        return (0, Some("GStreamer 'playbin' fehlt".into()));
    };
    pb.set_property("uri", "cdda://1");
    if let Ok(fs) = gst::ElementFactory::make("fakesink").build() {
        pb.set_property("audio-sink", &fs);
    }
    let _ = pb.set_state(gst::State::Paused);
    let (res, _, _) = pb.state(gst::ClockTime::from_seconds(15));
    let mut n = 0u32;
    if res.is_ok() {
        let fmt: gst::Format = unsafe {
            glib::translate::from_glib(gst::ffi::gst_format_get_by_nick(c"track".as_ptr()))
        };
        if let Some(v) = pb.query_duration_generic(fmt) {
            let c = v.value();
            if c > 0 {
                n = c as u32;
            }
        }
    }
    let _ = pb.set_state(gst::State::Null);
    (n, if n > 0 { None } else { Some("Keine Audio-CD gefunden".into()) })
}

#[cfg(test)]
mod tests {
    use super::parse_peak;

    #[test]
    fn peak_formats() {
        assert_eq!(parse_peak("level, peak=(double){ -6.5, -5.25 };"), vec![-6.5, -5.25]);
        assert_eq!(parse_peak("level, peak=(GValueArray)< -1, -2 >, rms=x"), vec![-1.0, -2.0]);
        assert!(parse_peak("level, rms=(double){ 1 }").is_empty());
    }
}
