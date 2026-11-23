//! thisismade CDP-2r – CD-Player-Software für Ubuntu/GNOME in Rust.
//!
//! Rust-Fassung des thisismade cdp-2 (GTK4 + GStreamer), Look und Bedienung unverändert.

mod app;
mod design;
mod engine;
mod face;
mod mpris;
mod window;

use app::{App, APP_ID, APP_NAME};
use gtk::prelude::*;
use gtk::{gio, glib};

pub fn help_text() -> String {
    format!(
        r#"<b><big>{APP_NAME} – Bedienung</big></b>

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
"#
    )
}

fn main() -> std::process::ExitCode {
    if let Err(e) = gst::init() {
        eprintln!("GStreamer konnte nicht gestartet werden: {e}");
        return std::process::ExitCode::FAILURE;
    }
    glib::set_application_name(APP_NAME);
    let gapp = gtk::Application::builder()
        .application_id(APP_ID)
        .flags(gio::ApplicationFlags::HANDLES_OPEN)
        .build();
    let engine = match engine::Engine::new() {
        Ok(e) => e,
        Err(e) => {
            eprintln!("{e}");
            return std::process::ExitCode::FAILURE;
        }
    };
    let app = App::new(gapp.clone(), engine);

    let a = app.clone();
    gapp.connect_startup(move |_| a.startup());
    let a = app.clone();
    gapp.connect_activate(move |_| a.activate());
    let a = app.clone();
    gapp.connect_open(move |_, files, _hint| a.open(files));
    let a = app.clone();
    gapp.connect_shutdown(move |_| a.shutdown());

    let rc = gapp.run();
    let code = app.exit_code.get();
    if rc != glib::ExitCode::SUCCESS {
        return std::process::ExitCode::FAILURE;
    }
    if code != 0 {
        return std::process::ExitCode::from(code as u8);
    }
    std::process::ExitCode::SUCCESS
}
