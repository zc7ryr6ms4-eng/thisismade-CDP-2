//! Gerätefront im minimalistischen Industrie-Stil: Weiß, Orange, feine Linien.
//!
//! Flache Flächen, Punktraster, kleine technische Beschriftungen mit Nummern,
//! runde Tasten. Gleiches Layout und gleiche Klickflächen wie face.rs.
//! (1:1-Port von tmplayer/face_minimal.py)

use crate::face::*;
use cairo::{Context, FontSlant, FontWeight};

const BODY: Rgb = (0.955, 0.955, 0.95);
const LINE: Rgb = (0.74, 0.74, 0.75);
const DOT: Rgb = (0.80, 0.80, 0.81);
const TXT_M: Rgb = (0.12, 0.12, 0.13);
const TXT_DIM: Rgb = (0.50, 0.50, 0.52);
const KEY: Rgb = (0.985, 0.985, 0.98);
const KEY_HI: Rgb = (0.90, 0.90, 0.90);
const ORANGE: Rgb = (1.0, 0.40, 0.0);
const ORANGE_DIM: Rgb = (0.86, 0.80, 0.75);
const SEG_ON: Rgb = (1.0, 0.13, 0.08);
const SEG_OFF: Rgb = (0.20, 0.04, 0.035);
const MONO: &str = "monospace";

fn mono(cr: &Context, s: &str, x: f64, y: f64, size: f64, color: Rgb, align: Align) {
    cr.select_font_face(MONO, FontSlant::Normal, FontWeight::Normal);
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

fn stroke(cr: &Context, color: Rgb, w: f64) {
    rgb(cr, color);
    cr.set_line_width(w);
    let _ = cr.stroke();
}

fn line(cr: &Context, x0: f64, y0: f64, x1: f64, y1: f64, color: Rgb, w: f64) {
    cr.new_path();
    cr.move_to(x0, y0);
    cr.line_to(x1, y1);
    stroke(cr, color, w);
}

/// Flache runde Taste; gedrückt = orange.
fn round_key(cr: &Context, cx: f64, cy: f64, r: f64, pressed: bool, fill: Rgb) {
    circle(cr, cx, cy, r);
    rgb(cr, if pressed { ORANGE } else { fill });
    let _ = cr.fill_preserve();
    stroke(cr, if pressed { ORANGE } else { LINE }, 1.0);
}

#[allow(clippy::too_many_arguments)]
fn square_key(cr: &Context, x: f64, y: f64, w: f64, h: f64, pressed: bool, fill: Rgb, r: f64) {
    rrect(cr, x, y, w, h, r);
    rgb(cr, if pressed { ORANGE } else { fill });
    let _ = cr.fill_preserve();
    stroke(cr, if pressed { ORANGE } else { LINE }, 1.0);
}

fn led(cr: &Context, x: f64, y: f64, on: bool) {
    cr.rectangle(x - 3.0, y - 3.0, 6.0, 6.0);
    rgb(cr, if on { ORANGE } else { ORANGE_DIM });
    let _ = cr.fill();
}

// ----------------------------------------------------------------- Gesamtbild
pub fn draw(cr: &Context, st: &DrawState) {
    draw_static(cr);
    draw_dynamic(cr, st);
}

pub fn draw_static(cr: &Context) {
    // Gehäuse: eine flache Platte
    rrect(cr, 0.0, 6.0, DEV_W, DEV_H, 14.0);
    rgba(cr, (0.0, 0.0, 0.0), 0.18);
    let _ = cr.fill();
    rrect(cr, 0.0, 0.0, DEV_W, DEV_H, 14.0);
    rgb(cr, BODY);
    let _ = cr.fill_preserve();
    stroke(cr, (0.80, 0.80, 0.81), 1.2);

    // Punktraster auf der linken Hälfte
    let (dcx, dcy) = DISC_C;
    for j in (13..(DEV_H as i64 - 8)).step_by(16) {
        for i in (13..600i64).step_by(16) {
            let (fi, fj) = (i as f64, j as f64);
            if (fi - dcx).powi(2) + (fj - dcy).powi(2) < (WELL_R + 10.0).powi(2) {
                continue;
            }
            circle(cr, fi, fj, 1.1);
            rgb(cr, DOT);
            let _ = cr.fill();
        }
    }

    // Trennlinie und Raster-Linien des Bedienfelds
    line(cr, 610.0, 14.0, 610.0, DEV_H - 14.0, LINE, 1.0);
    line(cr, 620.0, 255.0, DEV_W - 14.0, 255.0, LINE, 1.0);
    line(cr, 620.0, 392.0, DEV_W - 14.0, 392.0, LINE, 1.0);
    line(cr, 620.0, 578.0, 1075.0, 578.0, LINE, 1.0);
    line(cr, 1075.0, 255.0, 1075.0, DEV_H - 14.0, LINE, 1.0);

    // Name und Modell
    text(cr, "thisismade", 30.0, 44.0, 24.0, TXT_M, Align::Left, true);
    mono(cr, "CDP-2 / COMPACT DISC PLAYER", 31.0, 62.0, 10.0, TXT_DIM, Align::Left);
    rrect(cr, 520.0, 34.0, 54.0, 14.0, 7.0);
    stroke(cr, ORANGE, 1.0);
    mono(cr, "AUDIO", 547.0, 45.0, 9.0, ORANGE, Align::Center);

    // Teller: flache Mulde mit Rillen
    let (cx, cy) = DISC_C;
    circle(cr, cx, cy, WELL_R);
    rgb(cr, (0.90, 0.90, 0.895));
    let _ = cr.fill_preserve();
    stroke(cr, LINE, 1.0);
    for rr in (80..(WELL_R as i64 - 6)).step_by(18) {
        circle(cr, cx, cy, rr as f64);
        stroke(cr, (0.84, 0.84, 0.84), 1.0);
    }
    for k in 0..12 {
        let a = 2.0 * std::f64::consts::PI * k as f64 / 12.0;
        line(
            cr,
            cx + a.cos() * (WELL_R - 10.0),
            cy + a.sin() * (WELL_R - 10.0),
            cx + a.cos() * (WELL_R - 2.0),
            cy + a.sin() * (WELL_R - 2.0),
            TXT_DIM,
            1.0,
        );
    }

    // Display
    let (x, y, w, h) = DISPLAY;
    rrect(cr, x - 4.0, y - 4.0, w + 8.0, h + 8.0, 8.0);
    rgb(cr, (0.06, 0.05, 0.045));
    let _ = cr.fill_preserve();
    stroke(cr, (0.55, 0.55, 0.56), 1.0);

    // Nummerierte Beschriftungen
    for (t, tx, ty) in [
        ("01  NUMBER", 630.0, 266.0),
        ("02  VOLUME", 1086.0, 268.0),
        ("03  MEMORY", 630.0, 406.0),
        ("04  SHUTTLE", 890.0, 406.0),
        ("05  TRANSPORT", 630.0, 476.0),
        ("06  TEMPO", 1086.0, 406.0),
        ("07  MODE", 630.0, 588.0),
    ] {
        mono(cr, t, tx, ty, 9.0, TXT_DIM, Align::Left);
    }
}

pub fn draw_dynamic(cr: &Context, st: &DrawState) {
    let p = &st.pressed;
    let on = st.power_on;

    // obere Textknöpfe
    for (rid, t, x) in TOP_BTNS {
        let pr = p.contains(rid);
        rrect(cr, x, TOP_Y, TOP_W, TOP_H - 2.0, 12.0);
        rgb(cr, if pr { ORANGE } else { BODY });
        let _ = cr.fill_preserve();
        stroke(cr, if pr || rid == "power" { ORANGE } else { LINE }, 1.0);
        let col = if pr {
            BODY
        } else if rid == "power" {
            ORANGE
        } else {
            TXT_M
        };
        mono(cr, &t.to_lowercase(), x + TOP_W / 2.0, TOP_Y + 16.0, 10.0, col, Align::Center);
    }
    led(cr, 1146.0, 31.0, st.bt_led && on);
    mono(cr, "mpris", 1155.0, 35.0, 8.0, TXT_DIM, Align::Left);

    // Disc
    if st.disc_loaded {
        disc(cr, st);
    } else {
        let _ = cr.save();
        cr.translate(DISC_C.0, DISC_C.1);
        cr.rotate(st.disc_angle);
        spindle(cr);
        let _ = cr.restore();
        mono(cr, "no disc", DISC_C.0, DISC_C.1 + 70.0, 13.0, TXT_M, Align::Center);
        mono(cr, "open / files / drop", DISC_C.0, DISC_C.1 + 90.0, 10.0, TXT_DIM, Align::Center);
    }

    display(cr, st, SEG_ON, SEG_OFF, (1.0, 0.62, 0.14), (0.20, 0.11, 0.03));

    // Ziffernblock: runde Tasten
    for (lab, x, y) in KEYS {
        let kid = format!("key_{lab}");
        let (cx, cy) = (x + KEY_W / 2.0, y + KEY_H / 2.0 + 6.0);
        let pr = p.contains(&kid);
        round_key(cr, cx, cy, 19.0, pr, if lab == "T" || lab == "C" { KEY_HI } else { KEY });
        let t = match lab {
            "T" => "time",
            "C" => "clr",
            other => other,
        };
        let one = t.chars().count() == 1;
        mono(
            cr,
            t,
            cx,
            cy + if one { 5.0 } else { 3.5 },
            if one { 15.0 } else { 10.0 },
            if pr { BODY } else { TXT_M },
            Align::Center,
        );
    }
    let (x, y, w, h) = ENTER;
    let pe = p.contains("enter");
    square_key(cr, x, y + 12.0, w, h - 14.0, pe, KEY_HI, 10.0);
    mono(
        cr,
        "enter",
        x + w / 2.0,
        y + 12.0 + (h - 14.0) / 2.0 + 4.0,
        11.0,
        if pe { BODY } else { ORANGE },
        Align::Center,
    );

    knob(cr, st.level_norm);

    // Memory A/B/C
    for (i, (rid, t, x)) in MEM.iter().enumerate() {
        let pr = p.contains(*rid);
        square_key(cr, *x, MEM_Y + 2.0, MEM_W, MEM_H - 6.0, pr, KEY, 8.0);
        mono(cr, &t.to_lowercase(), x + 16.0, MEM_Y + 28.0, 15.0, if pr { BODY } else { TXT_M }, Align::Left);
        led(cr, x + MEM_W - 14.0, MEM_Y + 19.0, st.cue_set[i] && on);
    }

    // Shuttle: Linie mit orangem Schieber
    let (x, y, w, h) = SHUTTLE;
    let cy = y + h / 2.0 + 2.0;
    line(cr, x, cy, x + w, cy, LINE, 2.0);
    for k in -3i32..4 {
        let kx = x + w / 2.0 + k as f64 * w / 7.0;
        line(cr, kx, cy - 6.0, kx, cy + 6.0, if k != 0 { TXT_DIM } else { ORANGE }, 1.0);
    }
    mono(cr, "rew", x, y + h + 12.0, 9.0, TXT_DIM, Align::Left);
    mono(cr, "ff", x + w, y + h + 12.0, 9.0, TXT_DIM, Align::Right);
    let jx = x + w / 2.0 + st.jog * JOG_TRAVEL;
    cr.rectangle(jx - 10.0, cy - 12.0, 20.0, 24.0);
    rgb(cr, ORANGE);
    let _ = cr.fill();

    fader(cr, st.varispeed_norm);

    // Laufwerk
    for (rid, x, w) in TRANSPORT {
        let pr = p.contains(rid);
        let play = rid == "play";
        square_key(cr, x, TR_Y + 6.0, w, TR_H - 12.0, pr, if play { ORANGE } else { KEY }, 12.0);
        let col = if pr || play { BODY } else { TXT_M };
        icon(cr, rid, x + w / 2.0, TR_Y + TR_H / 2.0, col);
    }

    // Modus-Tasten
    for (rid, t, x) in SMALL {
        let ledv: Option<bool> = match rid {
            "vs_display" => Some(st.stretch),
            "repeat" => Some(st.repeat > 0),
            "shuffle" => Some(st.shuffle),
            _ => None,
        };
        let pr = p.contains(rid);
        rrect(cr, x, SMALL_Y + 12.0, SMALL_W, SMALL_H - 8.0, 13.0);
        rgb(cr, if pr { ORANGE } else { BODY });
        let _ = cr.fill_preserve();
        stroke(cr, if pr { ORANGE } else { LINE }, 1.0);
        mono(
            cr,
            &t.to_lowercase(),
            x + SMALL_W / 2.0 - if ledv.is_some() { 6.0 } else { 0.0 },
            SMALL_Y + 29.0,
            9.0,
            if pr { BODY } else { TXT_M },
            Align::Center,
        );
        if let Some(v) = ledv {
            led(cr, x + SMALL_W - 12.0, SMALL_Y + 25.0, v && on);
        }
    }

    if !on {
        rrect(cr, 0.0, 0.0, DEV_W, DEV_H, 14.0);
        rgba(cr, (0.0, 0.0, 0.0), 0.12);
        let _ = cr.fill();
    }
}

fn spindle(cr: &Context) {
    circle(cr, 0.0, 0.0, 26.0);
    rgb(cr, (0.86, 0.86, 0.86));
    let _ = cr.fill_preserve();
    stroke(cr, LINE, 1.0);
    circle(cr, 0.0, 0.0, 7.0);
    rgb(cr, ORANGE);
    let _ = cr.fill();
}

fn clip_chars(s: &str, n: usize) -> String {
    s.chars().take(n).collect()
}

fn disc(cr: &Context, st: &DrawState) {
    let (cx, cy) = DISC_C;
    let _ = cr.save();
    cr.translate(cx, cy);
    cr.rotate(st.disc_angle);
    circle(cr, 0.0, 2.0, DISC_R);
    rgba(cr, (0.0, 0.0, 0.0), 0.10);
    let _ = cr.fill();
    circle(cr, 0.0, 0.0, DISC_R);
    rgb(cr, (0.995, 0.995, 0.99));
    let _ = cr.fill_preserve();
    stroke(cr, LINE, 1.0);
    if let Some(cover) = st.cover.as_ref() {
        let _ = cr.save();
        circle(cr, 0.0, 0.0, DISC_R - 2.0);
        cr.clip();
        let (cw, ch) = (cover.width() as f64, cover.height() as f64);
        let s = 2.0 * (DISC_R - 2.0) / cw.min(ch);
        cr.scale(s, s);
        let _ = cr.set_source_surface(cover, -cw / 2.0, -ch / 2.0);
        let _ = cr.paint();
        let _ = cr.restore();
    } else {
        let ink = (0.10, 0.10, 0.11);
        for rr in [DISC_R - 14.0, HUB_R + 30.0] {
            circle(cr, 0.0, 0.0, rr);
            stroke(cr, (0.80, 0.80, 0.81), 1.0);
        }
        let lines = &st.disc_lines;
        if let Some(first) = lines.first() {
            text(cr, &clip_chars(first, 22).to_lowercase(), -150.0, -120.0, 22.0, ink, Align::Left, true);
        }
        for (i, ln) in lines.iter().skip(1).take(4).enumerate() {
            mono(
                cr,
                &clip_chars(ln, 30).to_lowercase(),
                -150.0,
                -96.0 + i as f64 * 15.0,
                10.0,
                (0.30, 0.30, 0.32),
                Align::Left,
            );
        }
        mono(cr, "thisismade / cdp-2", -150.0, 170.0, 10.0, ink, Align::Left);
        // orange Markierung, zeigt die Drehung
        cr.rectangle(DISC_R - 40.0, -5.0, 24.0, 10.0);
        rgb(cr, ORANGE);
        let _ = cr.fill();
    }
    circle(cr, 0.0, 0.0, HUB_R);
    rgb(cr, (0.93, 0.93, 0.93));
    let _ = cr.fill_preserve();
    stroke(cr, LINE, 1.0);
    spindle(cr);
    let _ = cr.restore();
}

fn knob(cr: &Context, value: f64) {
    // mittig im Kasten "02 VOLUME" (x 1075…1186, y 255…392), samt Skala
    let (cx, cy) = (1131.0, 331.0);
    let r = 33.0;
    for i in 0..31 {
        let a = (225.0 - 9.0 * i as f64).to_radians();
        let r0 = r + 5.0;
        let r1 = r + if i % 5 == 0 { 12.0 } else { 8.0 };
        let lit = i as f64 / 30.0 <= value + 1e-6;
        line(
            cr,
            cx + a.cos() * r0,
            cy - a.sin() * r0,
            cx + a.cos() * r1,
            cy - a.sin() * r1,
            if lit { ORANGE } else { LINE },
            if i % 5 == 0 { 1.4 } else { 1.0 },
        );
    }
    circle(cr, cx, cy, r);
    rgb(cr, KEY);
    let _ = cr.fill_preserve();
    stroke(cr, LINE, 1.0);
    let a = (225.0 - 270.0 * value.clamp(0.0, 1.0)).to_radians();
    line(
        cr,
        cx + a.cos() * 10.0,
        cy - a.sin() * 10.0,
        cx + a.cos() * (r - 6.0),
        cy - a.sin() * (r - 6.0),
        ORANGE,
        3.0,
    );
}

fn fader(cr: &Context, value: f64) {
    let x = FADER_X;
    let (y0, y1) = (FADER_Y0 + 4.0, FADER_Y1 - 10.0);
    line(cr, x, y0, x, y1, LINE, 2.0);
    for i in 0..11 {
        let y = y1 - i as f64 * (y1 - y0) / 10.0;
        line(
            cr,
            x + 18.0,
            y,
            x + if i % 5 == 0 { 30.0 } else { 24.0 },
            y,
            if i == 5 { ORANGE } else { TXT_DIM },
            1.0,
        );
    }
    mono(cr, "+", x - 26.0, y0 + 8.0, 11.0, TXT_DIM, Align::Left);
    mono(cr, "-", x - 26.0, y1 + 2.0, 11.0, TXT_DIM, Align::Left);
    let cy = y1 - value.clamp(0.0, 1.0) * (y1 - y0);
    cr.rectangle(x - 16.0, cy - 9.0, 32.0, 18.0);
    rgb(cr, (0.16, 0.16, 0.17));
    let _ = cr.fill();
    cr.rectangle(x - 16.0, cy - 1.0, 32.0, 2.0);
    rgb(cr, ORANGE);
    let _ = cr.fill();
}
