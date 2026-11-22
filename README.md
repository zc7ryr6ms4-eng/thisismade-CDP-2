# thisismade cdp-2

![thisismade cdp-2](data/screenshot.png)

Ein Musikplayer für **Ubuntu/GNOME**, der wie ein professionelles CD-Deck funktioniert:
drehende Disc zum Scratchen, rotes LED-Display mit Pegelanzeige, Tempo-Fader mit Key Lock,
drei Memory-Cues, Shuttle-Suchlauf, Ziffernblock für die direkte Titelwahl, Wiederholen und Zufall.

## Installieren

Unter [**Releases**](../../releases/latest) liegt das fertige Paket:

| Paket | So installierst du es |
|---|---|
| `thisismade-cdp-2_*_all.deb` | doppelt anklicken (App-Zentrum) oder `sudo apt install ./thisismade-cdp-2_*_all.deb` |

Oder alles mit einem Befehl – lädt die neueste Version und installiert sie samt Abhängigkeiten:

```bash
wget -qO- https://raw.githubusercontent.com/zc7ryr6ms4-eng/thisismade-CDP-2/main/install.sh | bash
```

Danach: **thisismade cdp-2** in der GNOME-Übersicht, oder `thisismade-cdp-2 ~/Musik` im Terminal.
Entfernen: `sudo apt remove thisismade-cdp-2`.

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
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-gstreamer-1.0 \
     gstreamer1.0-plugins-good gstreamer1.0-plugins-bad gstreamer1.0-libav
python3 -m tmplayer ~/Musik        # direkt starten
bash build-deb.sh                  # .deb nach dist/ bauen
```

Jeder Push wird auf GitHub Actions mit echtem GTK4 und GStreamer getestet
(Abspielen, Tempo, Cue, Screenshot); ein Tag `v*` baut das .deb und veröffentlicht ein Release.

## Ältere Version

Version 1 („Thisismade CD Player“) mit Linux-, macOS- und Windows-11-Fassung liegt als Archiv unter
[thisismade-CDP-1](https://github.com/zc7ryr6ms4-eng/thisismade-CDP-1).

## Projektaufbau

* `tmplayer/` – Linux-Version (Python, GTK4, GStreamer)
* `build-deb.sh` – .deb-Paket für Ubuntu
* `install.sh` – Ein-Befehl-Installer

Lizenz: BSD 3-Clause (siehe LICENSE)
