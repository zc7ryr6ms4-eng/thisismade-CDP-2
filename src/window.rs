//! Fenster: Zeichnen, Maus, Mausrad, Tastatur, Drag & Drop (Port von PlayerWindow).

use crate::app::{launch, Act, App, APP_ID, APP_NAME, SCRUB_NS_PER_TURN};
use crate::design;
use crate::engine::PlayState;
use crate::face::{self, now, pyround, CANVAS_H, CANVAS_W, DISC_C, JOG_TRAVEL, MARGIN_TOP, MARGIN_X};
use gtk::prelude::*;
use gtk::{gdk, gio, glib};
use std::f64::consts::PI;
use std::rc::Rc;
use std::time::Duration;

fn cursor_for(rid: Option<&str>) -> &'static str {
    match rid {
        Some("disc") => "grab",
        Some("jog") => "ew-resize",
        Some("resize") => "se-resize",
        Some("varispeed") | Some("level") => "ns-resize",
        Some("main_display") => "pointer",
        Some("sync") => "help",
        Some(_) => "pointer",
        None => "default",
    }
}

impl App {
    pub fn build_window(self: &Rc<Self>) {
        let win = gtk::ApplicationWindow::builder().application(&self.gapp).title(APP_NAME).build();
        win.set_decorated(false);
        win.add_css_class("tmplayer");
        win.set_icon_name(Some(APP_ID));
        *self.win.borrow_mut() = Some(win.clone());
        let mut z = self.zoom.get();
        if z <= 0.0 {
            z = self.auto_zoom();
        }
        win.set_default_size((CANVAS_W * z) as i32, (CANVAS_H * z) as i32);

        let area = gtk::DrawingArea::new();
        area.set_focusable(true);
        win.set_child(Some(&area));
        *self.area.borrow_mut() = Some(area.clone());
        let a = self.clone();
        area.set_draw_func(move |_area, cr, w, h| a.draw(cr, w, h));

        let drag = gtk::GestureDrag::new();
        drag.set_button(0);
        let a = self.clone();
        drag.connect_drag_begin(move |g, x, y| a.on_begin(g, x, y));
        let a = self.clone();
        drag.connect_drag_update(move |g, ox, oy| a.on_update(g, ox, oy));
        let a = self.clone();
        drag.connect_drag_end(move |_g, ox, oy| a.on_end(ox, oy));
        area.add_controller(drag);

        let scroll = gtk::EventControllerScroll::new(gtk::EventControllerScrollFlags::BOTH_AXES);
        let a = self.clone();
        scroll.connect_scroll(move |c, dx, dy| {
            a.on_scroll(c, dx, dy);
            glib::Propagation::Stop
        });
        area.add_controller(scroll);

        let motion = gtk::EventControllerMotion::new();
        let a = self.clone();
        motion.connect_motion(move |_c, x, y| {
            a.mouse.set((x, y));
            let (dx, dy) = a.to_dev(x, y);
            let rid = face::hit(dx, dy);
            if let Some(ar) = a.area.borrow().as_ref() {
                ar.set_cursor_from_name(Some(cursor_for(rid.as_deref())));
            }
        });
        area.add_controller(motion);

        let keys = gtk::EventControllerKey::new();
        let a = self.clone();
        keys.connect_key_pressed(move |_c, keyval, _code, state| {
            if a.on_key(keyval, state) {
                glib::Propagation::Stop
            } else {
                glib::Propagation::Proceed
            }
        });
        win.add_controller(keys);

        let drop = gtk::DropTarget::new(gdk::FileList::static_type(), gdk::DragAction::COPY);
        let a = self.clone();
        drop.connect_drop(move |_t, value, _x, _y| match value.get::<gdk::FileList>() {
            Ok(fl) => {
                let files = fl.files();
                if files.is_empty() {
                    false
                } else {
                    a.open_gfiles(&files);
                    true
                }
            }
            Err(_) => false,
        });
        area.add_controller(drop);

        let menu = gio::Menu::new();
        let sec = gio::Menu::new();
        sec.append(Some("Ordner laden …"), Some("app.open-folder"));
        sec.append(Some("Dateien laden …"), Some("app.open-files"));
        sec.append(Some("Audio-CD lesen"), Some("app.open-cd"));
        sec.append(Some("Auswerfen"), Some("app.eject"));
        menu.append_section(None, &sec);
        let sec = gio::Menu::new();
        sec.append(Some("Wiederholen umschalten"), Some("app.repeat"));
        sec.append(Some("Zufall umschalten"), Some("app.shuffle"));
        sec.append(Some("Varispeed / Time Stretch"), Some("app.stretch"));
        menu.append_section(None, &sec);
        let sec = gio::Menu::new();
        sec.append(Some("Bedienung"), Some("app.help"));
        sec.append(Some(&format!("Über {APP_NAME}")), Some("app.about"));
        sec.append(Some("Beenden"), Some("app.quit"));
        menu.append_section(None, &sec);
        let pm = gtk::PopoverMenu::from_model(Some(&menu));
        pm.set_parent(&area);
        pm.set_has_arrow(false);
        *self.menu.borrow_mut() = Some(pm);

        let a = self.clone();
        area.add_tick_callback(move |w, clock| {
            a.tick(w.upcast_ref(), clock);
            glib::ControlFlow::Continue
        });
        let a = self.clone();
        win.connect_close_request(move |_| {
            a.save_settings();
            if let Some(m) = a.menu.borrow_mut().take() {
                m.unparent();
            }
            glib::Propagation::Proceed
        });
    }

    fn auto_zoom(&self) -> f64 {
        let h = gdk::Display::default()
            .and_then(|d| d.monitors().item(0))
            .and_downcast::<gdk::Monitor>()
            .map(|m| m.geometry().height() as f64);
        match h {
            Some(h) if h > 0.0 => ((h * 0.82) / CANVAS_H).clamp(0.35, 1.0),
            _ => 0.6,
        }
    }

    pub fn current_zoom(&self) -> f64 {
        match self.win.borrow().as_ref() {
            Some(w) if w.width() > 0 => w.width() as f64 / CANVAS_W,
            _ => self.zoom.get(),
        }
    }

    fn set_zoom(&self, z: f64) {
        let z = z.clamp(0.3, 2.0);
        if let Some(w) = self.win.borrow().as_ref() {
            w.set_default_size((CANVAS_W * z) as i32, (CANVAS_H * z) as i32);
        }
    }

    // ------------------------------------------------------------ Zeichnen
    fn fit(w: f64, h: f64) -> (f64, f64, f64) {
        let s = (w / CANVAS_W).min(h / CANVAS_H);
        ((s), (w - CANVAS_W * s) / 2.0, (h - CANVAS_H * s) / 2.0)
    }

    pub fn to_dev(&self, x: f64, y: f64) -> (f64, f64) {
        let (s, ox, oy) = self.fit_cache.get();
        ((x - ox) / s - MARGIN_X, (y - oy) / s - MARGIN_TOP)
    }

    fn draw(&self, cr: &cairo::Context, w: i32, h: i32) {
        let (s, ox, oy) = Self::fit(w as f64, h as f64);
        self.fit_cache.set((s, ox, oy));
        let key = (w, h);
        let need = match self.bg.borrow().as_ref() {
            Some((_, k)) => *k != key,
            None => true,
        };
        if need {
            if let Ok(surf) = cr.target().create_similar(cairo::Content::ColorAlpha, w, h) {
                if let Ok(bc) = cairo::Context::new(&surf) {
                    bc.translate(ox, oy);
                    bc.scale(s, s);
                    bc.translate(MARGIN_X, MARGIN_TOP);
                    design::draw_static(&bc);
                }
                *self.bg.borrow_mut() = Some((surf, key));
            }
        }
        if let Some((surf, _)) = self.bg.borrow().as_ref() {
            let _ = cr.set_source_surface(surf, 0.0, 0.0);
            let _ = cr.paint();
        }
        cr.translate(ox, oy);
        cr.scale(s, s);
        cr.translate(MARGIN_X, MARGIN_TOP);
        design::draw_dynamic(cr, &self.state());
    }

    fn tick(&self, widget: &gtk::Widget, clock: &gdk::FrameClock) {
        let t = clock.frame_time() as f64 / 1e6;
        let dt = match self.last_frame.get() {
            None => 0.0,
            Some(l) => (t - l).min(0.1),
        };
        self.last_frame.set(Some(t));
        let busy = self.animate(dt, t);
        if busy || self.act.borrow().is_some() {
            widget.queue_draw();
            self.idle_acc.set(0.0);
        } else {
            self.idle_acc.set(self.idle_acc.get() + dt);
            if self.idle_acc.get() > 0.25 {
                // Uhr / Blinken
                self.idle_acc.set(0.0);
                widget.queue_draw();
            }
        }
    }

    // ------------------------------------------------------------ Maus
    fn on_begin(self: &Rc<Self>, g: &gtk::GestureDrag, x: f64, y: f64) {
        let btn = g.current_button();
        let shift = g.current_event_state().contains(gdk::ModifierType::SHIFT_MASK);
        let (dx, dy) = self.to_dev(x, y);
        let rid = face::hit(dx, dy);
        if let Some(ar) = self.area.borrow().as_ref() {
            ar.grab_focus();
        }

        if btn == 3 && (rid.is_none() || rid.as_deref() == Some("disc")) {
            if let Some(m) = self.menu.borrow().as_ref() {
                m.set_pointing_to(Some(&gdk::Rectangle::new(x as i32, y as i32, 1, 1)));
                m.popup();
            }
            g.set_state(gtk::EventSequenceState::Denied);
            return;
        }
        let Some(rid) = rid else {
            self.begin_window_op(g, btn, x, y, true);
            return;
        };
        if rid == "disc" && !self.power_on.get() {
            self.begin_window_op(g, btn, x, y, true);
            return;
        }
        if rid == "resize" {
            self.begin_window_op(g, btn, x, y, false);
            return;
        }
        if !self.power_on.get() && rid != "power" {
            return;
        }

        let seq = self.act_seq.get() + 1;
        self.act_seq.set(seq);
        let mut act = Act {
            seq,
            id: rid.clone(),
            btn,
            shift,
            x,
            y,
            long_done: false,
            long_src: None,
            moved: 0.0,
            start: 0,
            jog_timer: None,
            prev_angle: 0.0,
            was_playing: false,
            scrub: 0.0,
            last_seek: 0.0,
        };

        if rid == "varispeed" || rid == "level" {
            act.start = if rid == "varispeed" { self.varispeed.get() } else { self.level.get() };
            let t = now();
            let last = self.last_knob.borrow().clone();
            if last.0 == rid && t - last.1 < 0.35 {
                if rid == "varispeed" {
                    self.set_varispeed(100, true);
                    self.flash("VAri  100", 0.6);
                }
                act.start = if rid == "varispeed" { self.varispeed.get() } else { self.level.get() };
            }
            *self.last_knob.borrow_mut() = (rid.clone(), t);
            *self.act.borrow_mut() = Some(act);
            return;
        }
        if rid == "jog" {
            self.jog_held.set(true);
            let a = self.clone();
            act.jog_timer = Some(glib::timeout_add_local(Duration::from_millis(50), move || {
                a.jog_step();
                glib::ControlFlow::Continue
            }));
            self.pressed.borrow_mut().insert("jog".into());
            *self.act.borrow_mut() = Some(act);
            return;
        }
        if rid == "disc" {
            act.prev_angle = (dy - DISC_C.1).atan2(dx - DISC_C.0);
            act.was_playing = self.engine.state() == PlayState::Playing;
            act.scrub = self.engine.position() as f64;
            act.last_seek = 0.0;
            *self.act.borrow_mut() = Some(act);
            return;
        }
        if rid == "main_display" {
            *self.act.borrow_mut() = Some(act);
            return;
        }
        // Taste
        self.pressed.borrow_mut().insert(rid.clone());
        let long = (btn == 1 && (rid == "power" || rid == "key_C" || rid == "key_T"))
            || (rid.starts_with("cue") && btn == 1 && !shift);
        if long {
            let a = self.clone();
            act.long_src =
                Some(glib::timeout_add_local_once(Duration::from_millis(650), move || a.on_long(seq)));
        }
        *self.act.borrow_mut() = Some(act);
        self.redraw();
    }

    fn begin_window_op(&self, g: &gtk::GestureDrag, btn: u32, x: f64, y: f64, mv: bool) {
        let win = self.win.borrow().clone();
        if let Some(win) = win {
            let surf = win.surface();
            let dev = g.device();
            let ts = g.current_event_time();
            if let (Some(surf), Some(dev)) = (surf, dev) {
                if let Some(top) = surf.downcast_ref::<gdk::Toplevel>() {
                    // Koordinaten des DrawingArea → Surface (Fenster ohne Dekoration: identisch)
                    if mv {
                        top.begin_move(&dev, btn as i32, x, y, ts);
                    } else {
                        top.begin_resize(gdk::SurfaceEdge::SouthEast, Some(&dev), btn as i32, x, y, ts);
                    }
                }
            }
        }
        g.set_state(gtk::EventSequenceState::Denied);
    }

    fn on_long(self: &Rc<Self>, seq: u64) {
        let rid = {
            let mut b = self.act.borrow_mut();
            match b.as_mut() {
                Some(a) if a.seq == seq => {
                    a.long_src = None;
                    a.long_done = true;
                    a.id.clone()
                }
                _ => return,
            }
        };
        if rid == "power" {
            self.quit_app();
        } else if rid == "key_C" {
            self.keypad_long("C");
        } else if rid == "key_T" {
            self.keypad_long("T");
        } else if let Some(n) = rid.strip_prefix("cue") {
            self.cue_set(n.parse::<usize>().unwrap_or(1) - 1);
        }
    }

    fn on_update(self: &Rc<Self>, g: &gtk::GestureDrag, ox: f64, oy: f64) {
        let Some(mut act) = self.act.borrow_mut().take() else { return };
        let s = self.fit_cache.get().0;
        act.moved = act.moved.max(ox.hypot(oy) / s);
        if act.id == "varispeed" || act.id == "level" {
            let k = if g.current_event_state().contains(gdk::ModifierType::SHIFT_MASK) { 0.2 } else { 1.0 };
            let delta = (-oy + ox * 0.5) / s;
            if act.id == "varispeed" {
                self.set_varispeed(pyround(act.start as f64 + delta * k * 100.0 / 180.0) as i32, false);
            } else {
                self.set_level(pyround(act.start as f64 + delta * k * 100.0 / 220.0) as i32);
            }
        } else if act.id == "jog" {
            self.jog.set((ox / s / (JOG_TRAVEL * 1.6)).clamp(-1.0, 1.0));
        } else if act.id == "disc" {
            let (dx, dy) = self.to_dev(act.x + ox, act.y + oy);
            let ang = (dy - DISC_C.1).atan2(dx - DISC_C.0);
            let d = (ang - act.prev_angle + PI).rem_euclid(2.0 * PI) - PI;
            act.prev_angle = ang;
            if act.moved > 4.0 && !self.scrubbing.get() {
                self.scrubbing.set(true);
                if act.was_playing {
                    self.engine.pause();
                }
            }
            if self.scrubbing.get() {
                self.disc_angle.set(self.disc_angle.get() + d);
                act.scrub = (act.scrub + d / (2.0 * PI) * SCRUB_NS_PER_TURN).max(0.0);
                let t = now();
                if t - act.last_seek > 0.06 {
                    act.last_seek = t;
                    self.seek_to(act.scrub as i64);
                }
                self.redraw();
            }
        }
        *self.act.borrow_mut() = Some(act);
    }

    fn on_end(self: &Rc<Self>, ox: f64, oy: f64) {
        let Some(mut act) = self.act.borrow_mut().take() else { return };
        if let Some(src) = act.long_src.take() {
            src.remove();
        }
        let rid = act.id.clone();
        self.pressed.borrow_mut().remove(&rid);
        let (dx, dy) = self.to_dev(act.x + ox, act.y + oy);
        let inside = face::hit(dx, dy).as_deref() == Some(rid.as_str());
        if rid == "jog" {
            self.jog_held.set(false);
            if let Some(t) = act.jog_timer.take() {
                t.remove();
            }
        } else if rid == "disc" {
            if self.scrubbing.get() {
                self.seek_to(act.scrub as i64);
                self.scrubbing.set(false);
                if act.was_playing {
                    self.engine.play();
                }
            } else if act.moved < 4.0 {
                self.play_pause();
            }
        } else if rid == "varispeed" || rid == "level" {
            if rid == "varispeed" && self.vs_timer.borrow().is_none() {
                self.apply_varispeed();
            }
        } else if rid == "main_display" {
            if inside {
                self.toggle_time_mode();
            }
        } else if inside && !act.long_done {
            self.activate_control(&rid, act.btn, act.shift);
        }
        self.redraw();
    }

    fn activate_control(self: &Rc<Self>, rid: &str, btn: u32, shift: bool) {
        if rid == "power" {
            self.toggle_power();
            return;
        }
        if !self.power_on.get() {
            return;
        }
        if let Some(k) = rid.strip_prefix("key_") {
            self.keypad(k);
        } else if let Some(n) = rid.strip_prefix("cue") {
            let i = n.parse::<usize>().unwrap_or(1) - 1;
            if btn == 3 || shift {
                self.cue_clear(i);
            } else {
                self.cue_press(i);
            }
        } else {
            match rid {
                "enter" => self.enter(),
                "play" => self.play_pause(),
                "stop" => self.stop(),
                "prev" => self.prev_track(false),
                "next" => self.next_track(),
                "data" => {
                    if btn == 3 {
                        self.open_cd();
                    } else {
                        self.open_folder_dialog();
                    }
                }
                "usb" => self.open_files_dialog(),
                "cd" => self.open_cd(),
                "vs_display" => self.toggle_stretch(),
                "repeat" => self.cycle_repeat(),
                "shuffle" => self.set_shuffle(!self.shuffle.get()),
                "eject" => self.eject(),
                "output" => launch(&["gnome-control-center", "sound"]),
                "sync" => self.show_help(),
                _ => {}
            }
        }
    }

    fn jog_step(&self) {
        let j = self.jog.get();
        if j.abs() > 0.08 && self.has_tracks() {
            let speed = (j * j).copysign(j) * 16.0; // bis 16-fach
            self.seek_relative(speed * 0.05 * 1e9);
        }
    }

    fn on_scroll(self: &Rc<Self>, c: &gtk::EventControllerScroll, dx: f64, dy: f64) {
        if !self.power_on.get() {
            return;
        }
        let (mx, my) = self.mouse.get();
        let (px, py) = self.to_dev(mx, my);
        let rid = face::hit(px, py);
        let mut step = -(if dy.abs() >= dx.abs() { dy } else { -dx });
        if c.unit() == gdk::ScrollUnit::Surface {
            step /= 10.0;
        }
        let or_one = |r: i64| if r != 0 { r } else if step > 0.0 { 1 } else { -1 };
        match rid.as_deref() {
            Some("varispeed") => {
                if step != 0.0 {
                    self.set_varispeed(self.varispeed.get() + or_one(pyround(step)) as i32, false);
                }
            }
            Some("disc") | Some("jog") => {
                if self.has_tracks() {
                    self.disc_angle.set(self.disc_angle.get() + step * 0.15);
                    self.seek_relative(step * 2e9);
                }
            }
            _ => {
                if step != 0.0 {
                    self.set_level(self.level.get() + or_one(pyround(step * 2.0)) as i32);
                }
            }
        }
    }

    // ------------------------------------------------------------ Tastatur
    fn flash_key(self: &Rc<Self>, rid: &str) {
        self.pressed.borrow_mut().insert(rid.to_string());
        self.redraw();
        let a = self.clone();
        let rid = rid.to_string();
        glib::timeout_add_local_once(Duration::from_millis(120), move || {
            a.pressed.borrow_mut().remove(&rid);
            a.redraw();
        });
    }

    fn on_key(self: &Rc<Self>, keyval: gdk::Key, state: gdk::ModifierType) -> bool {
        let name = keyval.name().map(|s| s.to_string()).unwrap_or_default();
        let n = name.as_str();
        let ctrl = state.contains(gdk::ModifierType::CONTROL_MASK);
        let shift = state.contains(gdk::ModifierType::SHIFT_MASK);
        if ctrl {
            match n {
                "plus" | "equal" | "KP_Add" => self.set_zoom(self.current_zoom() * 1.1),
                "minus" | "KP_Subtract" => self.set_zoom(self.current_zoom() / 1.1),
                "0" | "KP_0" => self.set_zoom(self.auto_zoom()),
                "o" => self.open_files_dialog(),
                "q" => self.quit_app(),
                _ => return false,
            }
            return true;
        }
        if !self.power_on.get() && n != "p" {
            return false;
        }
        let digit: Option<String> = if n.len() == 1 && n.chars().all(|c| c.is_ascii_digit()) {
            Some(n.to_string())
        } else if let Some(d) = n.strip_prefix("KP_").filter(|d| !d.is_empty() && d.chars().all(|c| c.is_ascii_digit())) {
            Some(d.to_string())
        } else {
            None
        };
        if let Some(d) = digit {
            self.flash_key(&format!("key_{d}"));
            self.keypad(&d);
            return true;
        }
        match n {
            "Return" | "KP_Enter" => {
                self.flash_key("enter");
                self.enter();
            }
            "space" => {
                self.flash_key("play");
                self.play_pause();
            }
            "Escape" | "period" => {
                self.flash_key("stop");
                self.stop();
            }
            "Page_Down" | "n" => {
                self.flash_key("next");
                self.next_track();
            }
            "Page_Up" | "b" => {
                self.flash_key("prev");
                self.prev_track(false);
            }
            "Right" => self.seek_relative(if shift { 30.0 } else { 5.0 } * 1e9),
            "Left" => self.seek_relative(-(if shift { 30.0 } else { 5.0 }) * 1e9),
            "Up" => self.set_level(self.level.get() + 2),
            "Down" => self.set_level(self.level.get() - 2),
            "bracketleft" | "minus" | "KP_Subtract" => self.set_varispeed(self.varispeed.get() - 1, false),
            "bracketright" | "plus" | "KP_Add" => self.set_varispeed(self.varispeed.get() + 1, false),
            "backslash" | "numbersign" => self.set_varispeed(100, true),
            "t" | "T" => {
                self.flash_key("key_T");
                self.toggle_time_mode();
            }
            "c" | "BackSpace" | "Delete" => {
                self.flash_key("key_C");
                self.entry.borrow_mut().clear();
                self.redraw();
            }
            "m" | "M" => self.toggle_stretch(),
            "r" | "R" => self.cycle_repeat(),
            "s" | "S" => self.set_shuffle(!self.shuffle.get()),
            "q" | "w" | "e" | "Q" | "W" | "E" | "F2" | "F3" | "F4" => {
                let i = match n {
                    "q" | "Q" | "F2" => 0,
                    "w" | "W" | "F3" => 1,
                    _ => 2,
                };
                self.flash_key(&format!("cue{}", i + 1));
                if shift {
                    self.cue_set(i);
                } else {
                    self.cue_press(i);
                }
            }
            "o" | "O" => self.open_folder_dialog(),
            "d" | "D" => self.open_cd(),
            "j" | "J" => self.eject(),
            "p" => {
                self.flash_key("power");
                self.toggle_power();
            }
            "h" | "question" => self.show_help(),
            _ => return false,
        }
        true
    }
}
