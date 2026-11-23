# thisismade CDP-2r

![thisismade CDP-2r](data/screenshot.png)

Die **Rust-Fassung** des [thisismade cdp-2](https://github.com/zc7ryr6ms4-eng/thisismade-CDP-2) für **Ubuntu/GNOME**.
Gleicher Look und gleiche Bedienung wie das Original, jetzt als ein einziges natives Programm
(Rust, GTK4, GStreamer, Cairo) ohne Python.

Ein Musikplayer, der wie ein professionelles CD-Deck funktioniert:
drehende Disc zum Scratchen, rotes LED-Display mit Pegelanzeige, Tempo-Fader mit Key Lock,
drei Memory-Cues, Shuttle-Suchlauf, Ziffernblock für die direkte Titelwahl, Wiederholen und Zufall.

## Installieren

Unter [**Releases**](../../releases/latest) liegt das fertige Paket:

| Paket | So installierst du es |
|---|---|
| `thisismade-cdp-2r_*_amd64.deb` | doppelt anklicken (App-Zentrum) oder `sudo apt install ./thisismade-cdp-2r_*_amd64.deb` |

Oder mit einem Befehl:

```bash
wget -qO- https://raw.githubusercontent.com/zc7ryr6ms4-eng/thisismade-CDP-2r/main/install.sh | bash
```

Danach: **thisismade CDP-2r** in der GNOME-Übersicht, oder `thisismade-cdp-2r ~/Musik` im Terminal.
Entfernen: `sudo apt remove thisismade-cdp-2r`.

Die Rust-Fassung lässt sich neben der Python-Fassung installieren (eigene App-ID `io.github.thisismade.cdp2r`).
Beim ersten Start übernimmt sie die Einstellungen, Memory-Cues und die letzte Playlist des cdp-2.

## Funktionen

- **Laden:** OPEN (Ordner inkl. Unterordner), FILES (Dateien, .m3u-Playlists), CD (Audio-CD), Drag & Drop
- **Laufwerk:** Play/Pause, Stop, Titel vor/zurück, Klick auf die Disc = Play/Pause, Disc drehen = scratchen
- **Tempo:** 50–150 %; **Key Lock** aus = Tempo + Tonhöhe (Varispeed), an = nur Tempo (Time Stretch)
- **Memory A/B/C:** Merkpunkte setzen, anspringen, löschen – pro Titel gespeichert
- **Shuttle:** Rück-/Vorlauf bis 16-fach
- **Ziffernblock:** Titelnummer + ENTER, TIME (Restzeit), CLR
- **Display:** Titel, Anzahl, Zeit, Tempo, Lautstärke, Pegel L/R, Statusanzeigen
- **GNOME:** Medientasten, Sperrbildschirm und Mediensteuerung (MPRIS), kein Ruhezustand während der Wiedergabe
- Lückenlose Wiedergabe, Cover-Art auf der Disc, setzt beim nächsten Start an der letzten Stelle fort

Alle Tastenkürzel: im Player **F1** oder **HELP**.

Formate: alles, was GStreamer abspielt – MP3, FLAC, OGG, Opus, WAV, AIFF, M4A/AAC, WMA, APE, WavPack u. a.

## Aus dem Quellcode

```bash
sudo apt install cargo libgtk-4-dev libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev \
     gstreamer1.0-plugins-good gstreamer1.0-plugins-bad gstreamer1.0-libav
cargo run --release -- ~/Musik     # direkt starten
bash build-deb.sh                  # .deb nach dist/ bauen
```

Benötigt Ubuntu 24.04 oder neuer (GTK ≥ 4.14) und Rust ≥ 1.80.

Jeder Push wird auf GitHub Actions mit echtem GTK4 und GStreamer gebaut und getestet
(Abspielen, Tempo, Cue, Screenshot); ein Tag `v*` veröffentlicht ein Release mit dem .deb.

## Projektaufbau

* `src/engine.rs` – Audio-Engine (GStreamer playbin, Varispeed/Time Stretch, Pegel, Audio-CD)
* `src/face.rs` – Layout, Klickflächen, Display, 7-Segment-Ziffern
* `src/design.rs` – Gerätefront (Cairo)
* `src/app.rs` – Bedienlogik, Playlist, Cues, Einstellungen
* `src/window.rs` – Fenster, Maus, Tastatur, Drag & Drop
* `src/mpris.rs` – GNOME-Mediensteuerung (MPRIS2 über D-Bus)
* `build-deb.sh` – .deb-Paket für Ubuntu · `install.sh` – Ein-Befehl-Installer

Lizenz: BSD 3-Clause (siehe LICENSE)
