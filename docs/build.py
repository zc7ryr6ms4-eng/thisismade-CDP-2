"""Erzeugt die drei Seiten der thisismade-Website im gleichen Design.

index.html      thisismade cdp-2 (Startseite)
compressor.html thisismade Compressor (VST3/AU)
cdp-1.html      thisismade CDP-1 (erste Version, Archiv)
"""
import json

GH = "https://github.com/zc7ryr6ms4-eng/"

EXTRA_CSS = """
nav li a[aria-current=page]{color:var(--ink);background:rgba(255,255,255,.07)}
.steps{margin:0;padding-left:22px;color:var(--dim);font-size:15px;display:grid;gap:6px}
.steps code,.hint code,.flist code{font:13px ui-monospace,"SF Mono",Menlo,Consolas,monospace;color:#d9dedc;overflow-wrap:anywhere}
.tbl{overflow-x:auto;margin-top:32px;border:1px solid var(--line);border-radius:14px}
table{border-collapse:collapse;width:100%;font-size:15px}
th,td{padding:12px 16px;text-align:left;border-bottom:1px solid var(--line)}
th{font-weight:500;color:var(--dim);font-size:14px}
tr:last-child td{border-bottom:0}
td.num{text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums}
.chain{margin-top:28px;display:flex;flex-wrap:wrap;gap:8px;align-items:center;color:var(--dim);font-size:14px}
.chain span{border:1px solid var(--line);border-radius:18px;padding:6px 12px;color:var(--ink);background:var(--panel);white-space:nowrap}
.chain i{font-style:normal;color:var(--accent)}
.banner{margin:0 0 22px;padding:12px 16px;border:1px solid var(--accent);border-radius:12px;color:var(--ink);font-size:15px}
.banner a{color:var(--accent)}
"""

ICONS = {
    "win": '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M3 5.5 10.5 4.4v7H3zM11.5 4.3 21 3v8.4h-9.5zM3 12.5h7.5v7.1L3 18.5zM11.5 12.5H21V21l-9.5-1.3z"/></svg>',
    "mac": '<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M16.4 12.6c0-2.4 2-3.5 2-3.6-1.1-1.6-2.8-1.8-3.4-1.8-1.4-.1-2.8.9-3.5.9s-1.8-.9-3-.9C7 7.2 5.5 8.1 4.7 9.6c-1.7 2.9-.4 7.1 1.2 9.4.8 1.1 1.7 2.4 2.9 2.4s1.6-.8 3-.8 1.8.8 3 .8 2-1.1 2.8-2.3c.9-1.3 1.2-2.5 1.2-2.6 0 0-2.4-.9-2.4-3.9zM14.1 5.5c.6-.8 1.1-1.8 1-2.9-.9 0-2.1.6-2.7 1.4-.6.7-1.1 1.8-1 2.8 1 .1 2-.5 2.7-1.3z"/></svg>',
    "lin": '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" stroke-width="1.6"/><circle cx="12" cy="12" r="3" fill="none" stroke="currentColor" stroke-width="1.6"/><circle cx="19.5" cy="9" r="1.8" fill="currentColor"/><circle cx="6.5" cy="17" r="1.8" fill="currentColor"/><circle cx="8" cy="5.6" r="1.8" fill="currentColor"/></svg>',
}

NAV = [("index.html", "cdp-2"), ("compressor.html", "Compressor"), ("cdp-1.html", "CDP-1")]


def head(title):
    return f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="style.css">
</head>
<body>
"""


def nav(current, repo):
    items = "".join(
        f'<li{" class=\"keep\"" if href == current else ""}><a href="{href}"'
        f'{" aria-current=\"page\"" if href == current else ""}>{label}</a></li>'
        for href, label in NAV)
    items += f'<li><a href="#download">Download</a></li>'
    items += f'<li><a href="{GH}{repo}" target="_blank" rel="noopener">GitHub</a></li>'
    return f"""<header class="hero" id="top">
  <nav aria-label="Hauptnavigation">
    <a class="mark" href="index.html">[thisismade<b>.de</b></a>
    <ul>{items}</ul>
  </nav>"""


def hero_text(h1, sub, lead, cta, note):
    return f"""
  <div class="hero-text">
    <div>
      <h1>{h1} <span>{sub}</span></h1>
      <p class="lead">{lead}</p>
    </div>
    <div class="cta">
      <a class="btn main" id="heroBtn" href="#download">{cta}</a>
      <span class="note" id="heroNote">{note}</span>
    </div>
  </div>
</header>
"""


def showcase(img, w, h, alt, title, paras, extra=""):
    ps = "".join(f"<p>{p}</p>" for p in paras)
    return f"""
<section class="band player" id="player">
  <div class="wrap">
    <img class="shot" src="{img}" width="{w}" height="{h}" alt="{alt}">
    <div>
      <h2><span class="br">[</span>{title}</h2>
      {ps}{extra}
    </div>
  </div>
</section>
"""


def downloads(intro, more, banner=""):
    return f"""
<section class="band dl" id="download">
  <div class="wrap">
    <h2><span class="br">[</span>Download</h2>
    {banner}<p class="hint">{intro}</p>
    <div class="grid" id="osGrid"></div>
    {f"<p class=\"more\">{more}</p>" if more else ""}
  </div>
</section>
"""


def features(intro, items, after=""):
    fl = "".join(f"<div><h4>{t}</h4><p>{d}</p></div>" for t, d in items)
    return f"""
<section class="band feat" id="funktionen">
  <div class="wrap">
    <h2><span class="br">[</span>Funktionen</h2>
    <p>{intro}</p>
    <div class="flist">{fl}</div>{after}
  </div>
</section>
"""


def footer(name, repo):
    return f"""
<footer>
  <span>© 2026 thisismade · {name} · BSD-3-Clause</span>
  <span><a href="{GH}{repo}" target="_blank" rel="noopener">Quellcode auf GitHub</a> · <a href="{GH}{repo}/issues" target="_blank" rel="noopener">Fehler melden</a></span>
</footer>
"""


SCRIPT = """
<script>
{
  const icons = %ICONS%;
  const systems = %SYSTEMS%;
  const ua = navigator.userAgent || "";
  const mine = /Windows/i.test(ua) ? "win" : /Mac OS X|Macintosh/i.test(ua) ? "mac" : /Linux|X11/i.test(ua) && !/Android/i.test(ua) ? "lin" : "";
  const grid = document.getElementById("osGrid");
  if (systems.length === 1) grid.classList.add("one");
  grid.innerHTML = systems.map(s => `
    <article class="os${s.id === mine ? " mine" : ""}" id="os-${s.id}">
      <h3>${icons[s.id]}${s.name}</h3>
      <p class="req">${s.req}</p>
      <span class="tag">Für dein System</span>
      <ul class="files">${s.files.map((f, i) => `
        <li><a class="${i === 0 ? "first" : ""}" href="${f[0]}" target="_blank" rel="noopener">
          <span>${f[1]}</span><small>${f[2]}</small></a></li>`).join("")}
      </ul>
      ${s.cmd ? `<div class="cmd"><code>${s.cmd}</code><button class="copy" type="button" data-cmd="${s.cmd}">Kopieren</button></div>` : ""}
      ${s.steps ? `<ol class="steps">${s.steps.map(x => `<li>${x}</li>`).join("")}</ol>` : ""}
      <p class="hint">${s.hint}</p>
    </article>`).join("");
  const heroAuto = %HEROAUTO%;
  const s = systems.length === 1 ? systems[0] : systems.find(x => x.id === mine);
  if (s && heroAuto) {
    const btn = document.getElementById("heroBtn");
    btn.href = s.files[0][0];
    btn.target = "_blank";
    btn.rel = "noopener";
    btn.textContent = heroAuto + " " + s.name;
    document.getElementById("heroNote").innerHTML = %VERSION% + " · " + s.files[0][2] + (systems.length > 1 ? ' · <a href="#download">andere Systeme</a>' : "");
  }
  grid.addEventListener("click", async e => {
    const b = e.target.closest(".copy");
    if (!b) return;
    try {
      await navigator.clipboard.writeText(b.dataset.cmd);
      b.textContent = "Kopiert";
    } catch (err) {
      const r = document.createRange();
      r.selectNodeContents(b.previousElementSibling);
      const sel = getSelection();
      sel.removeAllRanges();
      sel.addRange(r);
      b.textContent = "Markiert";
    }
    setTimeout(() => { b.textContent = "Kopieren"; }, 1800);
  });
}
</script>
</body>
</html>
"""


def script(systems, hero_auto, version):
    return (SCRIPT.replace("%ICONS%", json.dumps(ICONS))
            .replace("%SYSTEMS%", json.dumps(systems, ensure_ascii=False))
            .replace("%HEROAUTO%", json.dumps(hero_auto))
            .replace("%VERSION%", json.dumps(version)))


UNSIGNED = ("Die Installer sind nicht kostenpflichtig signiert. Windows zeigt beim ersten Start „Der Computer wurde "
            "durch Windows geschützt“ → <em>Weitere Informationen → Trotzdem ausführen</em>; auf dem Mac in den "
            "Systemeinstellungen unter Datenschutz &amp; Sicherheit auf „Dennoch öffnen“ klicken.")

# ------------------------------------------------------------------ cdp-2
R2 = GH + "thisismade-CDP-2/releases/latest/download/"
RAW2 = "https://raw.githubusercontent.com/zc7ryr6ms4-eng/thisismade-CDP-2/main/"
cdp2_sys = [
    {"id": "lin", "name": "Ubuntu", "req": "ab Ubuntu 24.04 · GNOME",
     "files": [[R2 + "thisismade-cdp-2_1.0.0_all.deb", "Debian-Paket", "29 KB"]],
     "cmd": "wget -qO- " + RAW2 + "install.sh | bash",
     "hint": "Doppelt anklicken öffnet das App-Zentrum. Oder im Terminal: installiert den Player samt allem, was er braucht."},
]
cdp_feats = [
    ("Drehende Disc", "Klick spielt oder pausiert, Drehen mit der Maus scratcht durch den Titel."),
    ("Tempo und Key Lock", "50 bis 150 Prozent. Mit Key Lock bleibt die Tonhöhe, ohne ändert sie sich mit."),
    ("Memory A · B · C", "Drei Cue-Punkte pro Titel, gespeichert. Gedrückt halten setzt neu."),
    ("Shuttle", "Vor- und Rücklauf bis 16-fach, je weiter der Schieber, desto schneller."),
    ("Rotes Display", "Titel als Laufschrift, Zeit, Restzeit, Auflösung, Tempo, Lautstärke und Pegel L/R."),
    ("Mediensteuerung", "Medientasten, Sperrbildschirm und die Mediensteuerung von GNOME."),
]
page = (head("thisismade cdp-2") + nav("index.html", "thisismade-CDP-2")
        + hero_text("cdp-2", "CD-Player-Software",
                    "Ein Musikplayer, der sich wie ein CD-Deck bedient: drehende Disc, rotes Display, Tempo mit Key Lock, "
                    "Memory-Cues und Shuttle. Für Ubuntu Linux.",
                    "Herunterladen", "Version 1.0.0 · .deb · kostenlos · BSD-Lizenz")
        + showcase("player.png", 1256, 724,
                   "Die Gerätefront von thisismade cdp-2: weiße Front mit drehender Disc, rotem Display, Ziffernblock, "
                   "Laufwerkstasten, Lautstärkeregler und Tempo-Fader",
                   "Ein Gerät auf dem Bildschirm",
                   ["Die Disc dreht sich mit, solange Musik läuft, und lässt sich mit der Maus scratchen. Das Display "
                    "zeigt Titel, Spielzeit, Auflösung und Pegel.",
                    "Alles wird bedient wie am echten Deck: Titelnummer tippen und ENTER, Cue-Punkte auf A, B und C, "
                    "Tempo am Fader."])
        + downloads("Das .deb-Paket kommt direkt aus dem GitHub-Release von thisismade cdp-2.",
                    'Ältere Version: <a href="cdp-1.html">thisismade CDP-1</a>.')
        + features("Spielt Ordner, Einzeldateien, Playlists und Audio-CDs. Formate: MP3, FLAC, WAV, AIFF, AAC/M4A, "
                   "ALAC und mehr.", cdp_feats)
        + footer("thisismade cdp-2", "thisismade-CDP-2")
        + script(cdp2_sys, "Herunterladen für", "Version 1.0.0"))
open("index.html", "w").write(page)

# ------------------------------------------------------------------ CDP-1
R1 = GH + "thisismade-CDP-1/releases/latest/download/"
RAW1 = "https://raw.githubusercontent.com/zc7ryr6ms4-eng/thisismade-CDP-1/main/"
cdp1_sys = [
    {"id": "lin", "name": "Ubuntu", "req": "ab Ubuntu 24.04 · GNOME",
     "files": [[R1 + "thisismade-cd-player_1.0.0_all.deb", "Debian-Paket", "27 KB"]],
     "cmd": "wget -qO- " + RAW1 + "install.sh | bash",
     "hint": "Doppelt anklicken öffnet das App-Zentrum. Oder im Terminal installieren."},
]
banner = ('<p class="banner">Das ist die erste Version. Die aktuelle Version mit neuem Design, Titelanzeige und '
          'Auflösung ist <a href="index.html">thisismade cdp-2</a>.</p>')
page = (head("thisismade CDP-1") + nav("cdp-1.html", "thisismade-CDP-1")
        + hero_text("CDP-1", "die erste Version",
                    "Der „Thisismade CD Player“: die erste Fassung der CD-Player-Software mit weißer Front, roten "
                    "Anzeigen und allen Funktionen eines CD-Decks. Für Ubuntu Linux.",
                    "Version 1 herunterladen", "Version 1.0.0 · .deb · Archiv · BSD-Lizenz")
        + showcase("cdp1.jpg", 1200, 692,
                   "Die Gerätefront von Thisismade CDP-1: weiße Front mit Disc, rotem Display und Bedienfeld",
                   "Wo alles anfing",
                   ["Weiße Front, silberne Disc mit Cover-Druck, rote Sieben-Segment-Anzeige und Pegel L/R.",
                    "Gleiche Bedienung wie heute: Ziffernblock mit ENTER, Memory A, B und C, Shuttle, Tempo-Fader "
                    "mit Key Lock."])
        + downloads("Das .deb-Paket kommt aus dem GitHub-Release von thisismade CDP-1.", "", banner)
        + features("Spielt Ordner, Einzeldateien, Playlists und Audio-CDs.", cdp_feats)
        + footer("thisismade CDP-1", "thisismade-CDP-1")
        + script(cdp1_sys, "Version 1 für", "Version 1.0.0"))
open("cdp-1.html", "w").write(page)

# ------------------------------------------------------------------ Compressor
RC = GH + "thisismade-compressor-VST3"
ACT = RC + "/actions/workflows/build.yml"
comp_sys = [
    {"id": "win", "name": "Windows", "req": "VST3 · 64 Bit",
     "files": [[ACT, "Build-Artefakt „thisismade-Windows“", "VST3"],
               [RC, "Quellcode", "CMake"]],
     "steps": ["Den neuesten erfolgreichen Build öffnen.",
               "Unter <em>Artifacts</em> „thisismade-Windows“ laden (GitHub-Anmeldung nötig).",
               "<code>thisismade.vst3</code> nach <code>C:\\Program Files\\Common Files\\VST3\\</code> kopieren."],
     "hint": "Danach in der DAW nach neuen Plugins suchen lassen."},
    {"id": "mac", "name": "macOS", "req": "VST3 und AU · Apple Silicon und Intel",
     "files": [[ACT, "Installer „thisismade-macOS-Installer“", ".pkg"],
               [ACT, "Build-Artefakt „thisismade-macOS“", "VST3 · AU"]],
     "steps": ["Den neuesten erfolgreichen Build öffnen.",
               "Unter <em>Artifacts</em> „thisismade-macOS-Installer“ laden und die .pkg öffnen.",
               "Der Installer legt VST3 und AU in <code>/Library/Audio/Plug-Ins</code>."],
     "hint": "Nicht signiert: Systemeinstellungen → Datenschutz &amp; Sicherheit → „Dennoch öffnen“."},
    {"id": "lin", "name": "Linux", "req": "VST3 und Standalone · z. B. Ubuntu mit REAPER",
     "files": [[ACT, "Build-Artefakt „thisismade-Linux“", "VST3"],
               [RC + "/archive/refs/heads/main.zip", "Quellcode als .zip", "zum Selberbauen"]],
     "cmd": "./build-linux.sh",
     "hint": "Im entpackten Quellcode ausführen: baut VST3 und Standalone, testet und kopiert nach <code>~/.vst3</code>."},
]
comp_feats = [
    ("Limiter", "LIMIT IN, Threshold +4 bis +15 dBu, Recovery 50 ms bis a2, Attack fast oder slow."),
    ("Kompressor", "Threshold −20 bis +10 dBu, Ratio 1,5:1 bis 6:1, Recovery bis a2, Gain 0 bis 20 dB."),
    ("Gerastert wie das Original", "Jeder Regler rastet in den Schritten der Hardware ein, pro Kanal A und B."),
    ("Auto Gain", "Gleicht die Ausgangslautheit über etwa 3 s an den Eingang an, für faire A/B-Vergleiche."),
    ("Stereo Link", "Koppelt beide Sidechains; Kanal A steuert dann beide Kanäle."),
    ("Zeigerinstrumente", "Gain-Reduction-Meter je Kanal mit Nadelträgheit und LIMIT-LED."),
]
measures = [
    ("Limiter, Sprung 10 → 20 dBu", "< 0,1 dB Änderung", "0,10 dB"),
    ("Attack Kompressor (fast)", "3 ms", "2,8 ms bis 90 %"),
    ("THD, Sektionen aus, +9 dBu", "< 0,075 %", "0,034 %"),
    ("THD, 6:1, +20 dB Gain, Thr −18", "< 0,2 %", "0,11 %"),
    ("THD, Limiter, hoher Pegel", "< 0,45 %", "0,11 %"),
    ("Ratio, 10 dB über Threshold", "1,5 / 2 / 3 / 4 / 6", "1,50 / 2,00 / 3,03 / 4,01 / 6,03"),
]
rows = "".join(f"<tr><td>{a}</td><td class=\"num\">{b}</td><td class=\"num\">{c}</td></tr>" for a, b, c in measures)
table = (f'<div class="tbl"><table><thead><tr><th>Messung</th><th class="num">Hardware-Angabe</th><th class="num">thisismade</th></tr>'
         f'</thead><tbody>{rows}</tbody></table></div>'
         '<p class="hint" style="margin-top:12px">Gemessen mit <code>tests/dsp_test.cpp</code> gegen die veröffentlichten '
         'Daten der Hardware.</p>')
chain = ('<div class="chain"><span>Eingangsübertrager</span><i>→</i><span>Diodenbrücken-Kompressor</span><i>→</i>'
         '<span>Make-up Gain</span><i>→</i><span>Limiter</span><i>→</i><span>Ausgangsübertrager</span><i>→</i>'
         '<span>Auto Gain</span></div>')
page = (head("thisismade Compressor") + nav("compressor.html", "thisismade-compressor-VST3")
        + hero_text("Compressor", "Diode-Bridge-Limiter",
                    "Stereo-Kompressor und Limiter mit Diodenbrücke als VST3, AU und Standalone, nach dem Vorbild "
                    "des 33609. Alle Regler der Frontplatte, gerastet wie beim Original, dazu Auto Gain.",
                    "Herunterladen", "Version 1.0.0 · VST3 · AU · Standalone")
        + showcase("compressor.jpg", 1200, 416,
                   "Bedienoberfläche des thisismade Compressor mit zwei Kanälen, Drehreglern und zwei Zeigerinstrumenten",
                   "Zwei Kanäle, ein Klang",
                   ["Rückgekoppelter Kompressor mit weichem Knie, Limiter und zwei Übertragern, alles mit zweifachem "
                    "Oversampling. Auch mit ausgeschalteten Sektionen färbt das Plugin den Klang wie die Hardware; "
                    "BYPASS nimmt alles heraus.",
                    "a1 und a2 regeln automatisch: kurze Spitzen erholen sich schnell, länger anhaltendes Material "
                    "langsam."], chain)
        + downloads("Die fertigen Plugins baut GitHub bei jeder Änderung. Sie liegen als Artefakte am jeweiligen "
                    "Build und lassen sich mit einem GitHub-Konto laden.",
                    "Unabhängige Nachbildung, nicht mit AMS Neve verbunden. „33609“ beschreibt nur die Hardware, die als "
                    "Vorbild dient.")
        + features("Pro Kanal A und B dieselben Regler wie an der Hardware, gerastet in deren Schritten.", comp_feats,
                   table)
        + footer("thisismade Compressor", "thisismade-compressor-VST3")
        + script(comp_sys, "", "Version 1.0.0"))
open("compressor.html", "w").write(page)

# gemeinsames Stylesheet um Unterseiten-Regeln ergänzen
css = open("style.css").read()
if "aria-current" not in css:
    open("style.css", "w").write(css + EXTRA_CSS)
print("ok")
