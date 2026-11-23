//! Grundlagen der Gerätefront des thisismade cdp-2: Layout, Klickflächen, Display.
//!
//! Das eigentliche Design steht in design.rs (face_minimal).
//!
//! Koordinaten sind Geräteeinheiten: die Front ist DEV_W x DEV_H groß,
//! (0, 0) ist ihre linke obere Ecke.

use cairo::{Context, FontSlant, FontWeight};
use gtk::glib;
use std::collections::HashSet;
use std::f64::consts::PI;
use std::sync::OnceLock;

pub type Rgb = (f64, f64, f64);

pub const DEV_W: f64 = 1200.0;
pub const DEV_H: f64 = 660.0;
pub const MARGIN_X: f64 = 28.0;
pub const MARGIN_TOP: f64 = 24.0;
pub const MARGIN_BOTTOM: f64 = 40.0;
pub const CANVAS_W: f64 = DEV_W + 2.0 * MARGIN_X;
pub const CANVAS_H: f64 = DEV_H + MARGIN_TOP + MARGIN_BOTTOM;

pub const FONT: &str = "Inter";

// Farben
pub const TXT: Rgb = (0.22, 0.22, 0.24);
pub const VFD_ON: Rgb = (1.0, 0.13, 0.08);
pub const VFD_OFF: Rgb = (0.20, 0.04, 0.035);

// ----------------------------------------------------------------- Layout
pub const DISC_C: (f64, f64) = (320.0, 360.0);
pub const WELL_R: f64 = 272.0;
pub const DISC_R: f64 = 250.0;
pub const HUB_R: f64 = 62.0;

pub const DISPLAY: (f64, f64, f64, f64) = (630.0, 70.0, 540.0, 170.0);
pub const TOP_BTNS: [(&str, &str, f64); 6] = [
    ("data", "OPEN", 700.0),
    ("usb", "FILES", 772.0),
    ("cd", "CD", 844.0),
    ("output", "OUTPUT", 916.0),
    ("sync", "HELP", 988.0),
    ("power", "POWER", 1060.0),
];
pub const TOP_W: f64 = 64.0;
pub const TOP_Y: f64 = 18.0;
pub const TOP_H: f64 = 26.0;

pub const KEYS: [(&str, f64, f64); 12] = [
    ("1", 630.0, 270.0),
    ("2", 690.0, 270.0),
    ("3", 750.0, 270.0),
    ("4", 810.0, 270.0),
    ("5", 870.0, 270.0),
    ("T", 930.0, 270.0),
    ("6", 630.0, 326.0),
    ("7", 690.0, 326.0),
    ("8", 750.0, 326.0),
    ("9", 810.0, 326.0),
    ("0", 870.0, 326.0),
    ("C", 930.0, 326.0),
];
pub const KEY_W: f64 = 50.0;
pub const KEY_H: f64 = 44.0;
pub const ENTER: (f64, f64, f64, f64) = (990.0, 270.0, 70.0, 100.0);
pub const KNOB_C: (f64, f64) = (1120.0, 318.0);
pub const KNOB_R: f64 = 48.0;
pub const MEM: [(&str, &str, f64); 3] = [("cue1", "A", 630.0), ("cue2", "B", 712.0), ("cue3", "C", 794.0)];
pub const MEM_Y: f64 = 412.0;
pub const MEM_W: f64 = 72.0;
pub const MEM_H: f64 = 44.0;
pub const SHUTTLE: (f64, f64, f64, f64) = (890.0, 412.0, 170.0, 44.0);
pub const JOG_TRAVEL: f64 = 55.0;
pub const FADER_X: f64 = 1120.0;
pub const FADER_Y0: f64 = 446.0;
pub const FADER_Y1: f64 = 626.0;
pub const TRANSPORT: [(&str, f64, f64); 4] =
    [("prev", 630.0, 90.0), ("next", 730.0, 90.0), ("stop", 830.0, 90.0), ("play", 930.0, 130.0)];
pub const TR_Y: f64 = 482.0;
pub const TR_H: f64 = 82.0;
pub const SMALL: [(&str, &str, f64); 4] = [
    ("vs_display", "KEY LOCK", 630.0),
    ("repeat", "REPEAT", 742.0),
    ("shuffle", "SHUFFLE", 854.0),
    ("eject", "EJECT", 966.0),
];
pub const SMALL_Y: f64 = 590.0;
pub const SMALL_W: f64 = 94.0;
pub const SMALL_H: f64 = 34.0;

/// Alles, was die Front zum Zeichnen braucht.
#[derive(Default)]
pub struct DrawState {
    pub pressed: HashSet<String>,
    pub disc_loaded: bool,
    pub disc_angle: f64,
    pub disc_lines: Vec<String>,
    pub cover: Option<cairo::ImageSurface>,
    pub bt_led: bool,
    pub power_on: bool,
    pub vu_l: f64,
    pub vu_r: f64,
    pub vu_peaks: [f64; 2],
    pub main_text: String,
    pub vs_text: String,
    pub lv_text: String,
    pub stretch: bool,
    pub cue_set: [bool; 3],
    pub varispeed_norm: f64,
    pub level_norm: f64,
    pub jog: f64,
    pub repeat: i32,
    pub shuffle: bool,
    pub paused: bool,
    pub remain: bool,
    pub msg_mode: bool,
    pub title: String,
    pub resolution: String,
}

enum Shape {
    Rect(f64, f64, f64, f64),
    Circle(f64, f64, f64),
}

fn hit_regions() -> Vec<(String, Shape)> {
    let mut r = Vec::new();
    for (rid, _t, x) in TOP_BTNS {
        r.push((rid.to_string(), Shape::Rect(x - 2.0, TOP_Y - 4.0, TOP_W + 4.0, TOP_H + 8.0)));
    }
    for (lab, x, y) in KEYS {
        r.push((format!("key_{lab}"), Shape::Rect(x - 3.0, y - 3.0, KEY_W + 6.0, KEY_H + 6.0)));
    }
    r.push(("enter".into(), Shape::Rect(ENTER.0, ENTER.1, ENTER.2, ENTER.3)));
    r.push(("level".into(), Shape::Circle(KNOB_C.0, KNOB_C.1, KNOB_R + 8.0)));
    for (rid, _t, x) in MEM {
        r.push((rid.to_string(), Shape::Rect(x - 3.0, MEM_Y - 3.0, MEM_W + 6.0, MEM_H + 6.0)));
    }
    let (x, y, w, h) = SHUTTLE;
    r.push(("jog".into(), Shape::Rect(x - 4.0, y - 18.0, w + 8.0, h + 22.0)));
    r.push((
        "varispeed".into(),
        Shape::Rect(FADER_X - 40.0, FADER_Y0 - 24.0, 80.0, FADER_Y1 - FADER_Y0 + 40.0),
    ));
    for (rid, x, w) in TRANSPORT {
        r.push((rid.to_string(), Shape::Rect(x - 3.0, TR_Y - 3.0, w + 6.0, TR_H + 6.0)));
    }
    for (rid, _t, x) in SMALL {
        r.push((rid.to_string(), Shape::Rect(x - 3.0, SMALL_Y - 3.0, SMALL_W + 6.0, SMALL_H + 6.0)));
    }
    let (dx, dy, dw, dh) = DISPLAY;
    r.push(("main_display".into(), Shape::Rect(dx, dy, dw, dh)));
    r.push(("disc".into(), Shape::Circle(DISC_C.0, DISC_C.1, DISC_R)));
    r.push((
        "resize".into(),
        Shape::Rect(DEV_W - 36.0, DEV_H - 36.0, 36.0 + MARGIN_X, 36.0 + MARGIN_BOTTOM),
    ));
    r
}

pub fn hit(x: f64, y: f64) -> Option<String> {
    static REGIONS: OnceLock<Vec<(String, Shape)>> = OnceLock::new();
    for (rid, shape) in REGIONS.get_or_init(hit_regions) {
        let inside = match *shape {
            Shape::Rect(rx, ry, rw, rh) => rx <= x && x <= rx + rw && ry <= y && y <= ry + rh,
            Shape::Circle(cx, cy, r) => (x - cx).powi(2) + (y - cy).powi(2) <= r * r,
        };
        if inside {
            return Some(rid.clone());
        }
    }
    None
}

/// Python-`round()` (halbe Werte zur geraden Zahl)
pub fn pyround(x: f64) -> i64 {
    x.round_ties_even() as i64
}

pub fn now() -> f64 {
    glib::monotonic_time() as f64 / 1e6
}

// ----------------------------------------------------------------- Helfer
#[derive(Clone, Copy, PartialEq, Eq)]
pub enum Align {
    Left,
    Center,
    Right,
}

pub fn rrect(cr: &Context, x: f64, y: f64, w: f64, h: f64, r: f64) {
    let r = r.min(w / 2.0).min(h / 2.0);
    cr.new_sub_path();
    cr.arc(x + w - r, y + r, r, -PI / 2.0, 0.0);
    cr.arc(x + w - r, y + h - r, r, 0.0, PI / 2.0);
    cr.arc(x + r, y + h - r, r, PI / 2.0, PI);
    cr.arc(x + r, y + r, r, PI, 3.0 * PI / 2.0);
    cr.close_path();
}

pub fn circle(cr: &Context, cx: f64, cy: f64, r: f64) {
    cr.new_sub_path();
    cr.arc(cx, cy, r, 0.0, 2.0 * PI);
    cr.close_path();
}

pub fn rgb(cr: &Context, c: Rgb) {
    cr.set_source_rgba(c.0, c.1, c.2, 1.0);
}

pub fn rgba(cr: &Context, c: Rgb, a: f64) {
    cr.set_source_rgba(c.0, c.1, c.2, a);
}

pub fn advance(cr: &Context, s: &str) -> f64 {
    cr.text_extents(s).map(|e| e.x_advance()).unwrap_or(0.0)
}

pub fn text_font(cr: &Context, family: &str, s: &str, x: f64, y: f64, size: f64, color: Rgb, align: Align, bold: bool) {
    cr.select_font_face(
        family,
        FontSlant::Normal,
        if bold { FontWeight::Bold } else { FontWeight::Normal },
    );
    cr.set_font_size(size);
    let adv = advance(cr, s);
    let x = match align {
        Align::Center => x - adv / 2.0,
        Align::Right => x - adv,
        Align::Left => x,
    };
    rgb(cr, color);
    cr.move_to(x, y);
    let _ = cr.show_text(s);
}

pub fn text(cr: &Context, s: &str, x: f64, y: f64, size: f64, color: Rgb, align: Align, bold: bool) {
    text_font(cr, FONT, s, x, y, size, color, align, bold);
}

// ----------------------------------------------------------------- 7 Segmente
fn seg(c: char) -> Option<&'static str> {
    Some(match c {
        '0' => "abcdef",
        '1' => "bc",
        '2' => "abged",
        '3' => "abgcd",
        '4' => "fgbc",
        '5' => "afgcd",
        '6' => "afgedc",
        '7' => "abc",
        '8' => "abcdefg",
        '9' => "abcdfg",
        '-' => "g",
        ' ' => "",
        '_' => "d",
        'A' => "abcefg",
        'b' => "cdefg",
        'C' => "adef",
        'c' => "deg",
        'd' => "bcdeg",
        'E' => "adefg",
        'F' => "aefg",
        'G' => "acdef",
        'H' => "bcefg",
        'h' => "cefg",
        'I' => "ef",
        'i' => "e",
        'J' => "bcde",
        'L' => "def",
        'n' => "ceg",
        'o' => "cdeg",
        'O' => "abcdef",
        'P' => "abefg",
        'q' => "abcfg",
        'r' => "eg",
        'S' => "afgcd",
        't' => "defg",
        'U' => "bcdef",
        'V' => "bcdef",
        'u' => "cde",
        'y' => "bcdfg",
        'Y' => "bcdfg",
        '=' => "dg",
        _ => return None,
    })
}

fn seg_char(ch: char) -> &'static str {
    let up = ch.to_uppercase().next().unwrap_or(ch);
    let lo = ch.to_lowercase().next().unwrap_or(ch);
    seg(ch).or_else(|| seg(up)).or_else(|| seg(lo)).unwrap_or("")
}

#[allow(clippy::too_many_arguments)]
pub fn digit(cr: &Context, x: f64, y: f64, w: f64, h: f64, ch: char, on_col: Rgb, off_col: Rgb) {
    let t = (w * 0.17).max(2.0);
    let sk = 0.08;
    let hh = h / 2.0;
    let lit = seg_char(ch);
    let p = |px: f64, py: f64| (x + px + (h - py) * sk, y + py);
    let hseg = |px: f64, py: f64, l: f64| {
        vec![
            (px, py),
            (px + t / 2.0, py - t / 2.0),
            (px + l - t / 2.0, py - t / 2.0),
            (px + l, py),
            (px + l - t / 2.0, py + t / 2.0),
            (px + t / 2.0, py + t / 2.0),
        ]
    };
    let vseg = |px: f64, py: f64, l: f64| {
        vec![
            (px, py),
            (px + t / 2.0, py + t / 2.0),
            (px + t / 2.0, py + l - t / 2.0),
            (px, py + l),
            (px - t / 2.0, py + l - t / 2.0),
            (px - t / 2.0, py + t / 2.0),
        ]
    };
    let g = 1.0;
    let segs = [
        ('a', hseg(t / 2.0 + g, t / 2.0, w - t - 2.0 * g)),
        ('g', hseg(t / 2.0 + g, hh, w - t - 2.0 * g)),
        ('d', hseg(t / 2.0 + g, h - t / 2.0, w - t - 2.0 * g)),
        ('f', vseg(t / 2.0, t / 2.0 + g, hh - t / 2.0 - 2.0 * g)),
        ('e', vseg(t / 2.0, hh + g, hh - t / 2.0 - 2.0 * g)),
        ('b', vseg(w - t / 2.0, t / 2.0 + g, hh - t / 2.0 - 2.0 * g)),
        ('c', vseg(w - t / 2.0, hh + g, hh - t / 2.0 - 2.0 * g)),
    ];
    for (name, pts) in segs.iter() {
        cr.new_path();
        for (i, (px, py)) in pts.iter().enumerate() {
            let (xx, yy) = p(*px, *py);
            if i == 0 {
                cr.move_to(xx, yy);
            } else {
                cr.line_to(xx, yy);
            }
        }
        cr.close_path();
        rgb(cr, if lit.contains(*name) { on_col } else { off_col });
        let _ = cr.fill();
    }
}

#[allow(clippy::too_many_arguments)]
pub fn digits(cr: &Context, text: &str, x: f64, y: f64, w: f64, h: f64, pitch: f64, on_col: Rgb, off_col: Rgb) {
    for (i, c) in text.chars().enumerate() {
        digit(cr, x + i as f64 * pitch, y, w, h, c, on_col, off_col);
    }
}

// ----------------------------------------------------------------- Bauteile
pub fn icon(cr: &Context, kind: &str, cx: f64, cy: f64, color: Rgb) {
    rgb(cr, color);
    match kind {
        "prev" => {
            cr.rectangle(cx - 12.0, cy - 9.0, 3.0, 18.0);
            let _ = cr.fill();
            for dx in [0.0, 11.0] {
                cr.move_to(cx + 2.0 + dx, cy - 9.0);
                cr.line_to(cx - 8.0 + dx, cy);
                cr.line_to(cx + 2.0 + dx, cy + 9.0);
                cr.close_path();
                let _ = cr.fill();
            }
        }
        "next" => {
            for dx in [0.0, 11.0] {
                cr.move_to(cx - 13.0 + dx, cy - 9.0);
                cr.line_to(cx - 3.0 + dx, cy);
                cr.line_to(cx - 13.0 + dx, cy + 9.0);
                cr.close_path();
                let _ = cr.fill();
            }
            cr.rectangle(cx + 9.0, cy - 9.0, 3.0, 18.0);
            let _ = cr.fill();
        }
        "stop" => {
            cr.rectangle(cx - 8.0, cy - 8.0, 16.0, 16.0);
            let _ = cr.fill();
        }
        "play" => {
            cr.move_to(cx - 18.0, cy - 10.0);
            cr.line_to(cx - 4.0, cy);
            cr.line_to(cx - 18.0, cy + 10.0);
            cr.close_path();
            let _ = cr.fill();
            cr.rectangle(cx + 4.0, cy - 10.0, 4.0, 20.0);
            let _ = cr.fill();
            cr.rectangle(cx + 12.0, cy - 10.0, 4.0, 20.0);
            let _ = cr.fill();
        }
        _ => {}
    }
}

pub fn display(cr: &Context, st: &DrawState, on_col: Rgb, off_col: Rgb, hot_on: Rgb, hot_off: Rgb) {
    let (x, y, w, _h) = DISPLAY;
    let on = st.power_on;
    let l = |c: bool| if c && on { on_col } else { off_col };
    let (dw, dh, pitch) = (26.0, 46.0, 34.0);
    let main: Vec<char> = if !on {
        vec![' '; 12]
    } else {
        format!("{}            ", st.main_text).chars().take(12).collect()
    };
    let sub = |a: usize, b: usize| -> String { main[a..b].iter().collect() };
    if on && st.msg_mode {
        digits(cr, &sub(0, 12), x + 18.0, y + 38.0, dw, dh, pitch, on_col, off_col);
    } else {
        text(cr, "TRACK", x + 18.0, y + 26.0, 10.0, l(true), Align::Left, false);
        text(cr, "TOTAL", x + 136.0, y + 26.0, 10.0, l(true), Align::Left, false);
        text(cr, "TIME", x + 254.0, y + 26.0, 10.0, l(true), Align::Left, false);
        digits(cr, &sub(0, 3), x + 18.0, y + 38.0, dw, dh, pitch, on_col, off_col);
        digits(cr, &sub(3, 6), x + 136.0, y + 38.0, dw, dh, pitch, on_col, off_col);
        digits(cr, &sub(6, 9), x + 254.0, y + 38.0, dw, dh, pitch, on_col, off_col);
        for dy in [14.0, 32.0] {
            circle(cr, x + 362.0 + (46.0 - dy) * 0.08, y + 38.0 + dy, 3.0);
            rgb(cr, l(true));
            let _ = cr.fill();
        }
        digits(cr, &sub(10, 12), x + 372.0, y + 38.0, dw, dh, pitch, on_col, off_col);
    }
    // Titel (Laufschrift bei langen Namen) und Auflösung
    if on && !st.msg_mode {
        title_line(cr, st, x, y, w, l(true));
    }
    // Anzeigen rechts
    let ind = [
        (if st.repeat != 2 { "REPEAT" } else { "REPEAT 1" }, st.repeat > 0),
        ("SHUFFLE", st.shuffle),
        ("KEY LOCK", st.stretch),
        ("PAUSE", st.paused),
        ("REMAIN", st.remain),
    ];
    for (i, (t, a)) in ind.iter().enumerate() {
        text(cr, t, x + w - 14.0, y + 26.0 + i as f64 * 15.0, 10.0, l(*a), Align::Right, false);
    }
    // untere Zeile: Tempo, Lautstärke, Pegel
    let by = y + 126.0;
    text(cr, "TEMPO", x + 18.0, by - 6.0, 10.0, l(true), Align::Left, false);
    digits(cr, if on { &st.vs_text } else { "   " }, x + 18.0, by, 15.0, 26.0, 20.0, on_col, off_col);
    text(cr, "%", x + 84.0, by + 25.0, 12.0, l(true), Align::Left, false);
    text(cr, "VOL", x + 110.0, by - 6.0, 10.0, l(true), Align::Left, false);
    digits(cr, if on { &st.lv_text } else { "   " }, x + 110.0, by, 15.0, 26.0, 20.0, on_col, off_col);
    let mx = x + 200.0;
    let n: i64 = 30;
    for (row, val) in [st.vu_l, st.vu_r].iter().enumerate() {
        let yy = by + 2.0 + row as f64 * 15.0;
        text(cr, ["L", "R"][row], mx, yy + 9.0, 10.0, l(true), Align::Left, false);
        let v = if on { *val } else { 0.0 };
        let lit = pyround(v.clamp(0.0, 1.0) * n as f64);
        let pv = if on { st.vu_peaks[row] } else { 0.0 };
        let pk = pyround(pv.clamp(0.0, 1.0) * n as f64);
        for i in 0..n {
            cr.rectangle(mx + 14.0 + i as f64 * 10.5, yy, 8.0, 10.0);
            let hot = i >= n - 5;
            let col = if hot { hot_on } else { on_col };
            let off = if hot { hot_off } else { off_col };
            rgb(cr, if i < lit || (pk != 0 && i == pk - 1) { col } else { off });
            let _ = cr.fill();
        }
    }
}

fn title_line(cr: &Context, st: &DrawState, x: f64, y: f64, w: f64, col: Rgb) {
    let title = st.title.as_str();
    let res = st.resolution.as_str();
    let ty = y + 101.0;
    cr.select_font_face(FONT, FontSlant::Normal, FontWeight::Bold);
    cr.set_font_size(11.0);
    let rw = if res.is_empty() { 0.0 } else { advance(cr, res) };
    if !res.is_empty() {
        rgb(cr, col);
        cr.move_to(x + w - 14.0 - rw, ty);
        let _ = cr.show_text(res);
    }
    if title.is_empty() {
        return;
    }
    let box_x = x + 18.0;
    let box_w = w - 32.0 - rw - if res.is_empty() { 0.0 } else { 16.0 };
    let tw = advance(cr, title);
    let _ = cr.save();
    cr.rectangle(box_x, ty - 12.0, box_w, 16.0);
    cr.clip();
    rgb(cr, col);
    if tw <= box_w {
        cr.move_to(box_x, ty);
        let _ = cr.show_text(title);
    } else {
        let gap = 50.0;
        let off = (now() * 28.0).rem_euclid(tw + gap);
        for k in [0.0, 1.0] {
            cr.move_to(box_x - off + k * (tw + gap), ty);
            let _ = cr.show_text(title);
        }
    }
    let _ = cr.restore();
}
