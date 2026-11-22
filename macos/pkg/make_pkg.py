#!/usr/bin/env python3
"""Erzeugt ein macOS-Installationspaket (.pkg, Flat-Package/xar) ohne macOS-Werkzeuge.

Das Paket hat keinen Payload; sein postinstall-Skript bringt den Quellcode mit,
installiert bei Bedarf Apples Command Line Tools, kompiliert die App und legt sie
nach /Applications.

    python3 make_pkg.py <macos-ordner> <ausgabe.pkg>
"""
import gzip
import hashlib
import io
import os
import struct
import sys
import time
import zlib
from xml.sax.saxutils import escape

PKG_ID = "io.github.thisismade.cdp2.pkg"
VERSION = "1.0.0"
HERE = os.path.dirname(os.path.abspath(__file__))


# ------------------------------------------------------------------ cpio (odc)
def cpio_odc(entries):
    """entries: Liste von (pfad, modus, daten|None). Liefert cpio-Archiv (Format odc)."""
    out = io.BytesIO()
    ino = 1
    mtime = int(time.time())
    for name, mode, data in entries + [("TRAILER!!!", 0, b"")]:
        data = data or b""
        nb = name.encode() + b"\0"
        hdr = "070707%06o%06o%06o%06o%06o%06o%06o%011o%06o%011o" % (
            0, ino if name != "TRAILER!!!" else 0, mode, 0, 80, 1, 0,
            mtime if name != "TRAILER!!!" else 0, len(nb), len(data))
        out.write(hdr.encode() + nb + data)
        ino += 1
    return out.getvalue()


def collect(root, prefix="."):
    """Ordnerinhalt als cpio-Einträge (Ordner vor ihrem Inhalt, sortiert)."""
    entries = [(prefix, 0o40755, None)]
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in ("build", "pkg", "__pycache__"))
        rel = os.path.relpath(dirpath, root).replace(os.sep, "/")
        base = prefix if rel == "." else prefix + "/" + rel
        for d in dirnames:
            entries.append((base + "/" + d, 0o40755, None))
        for f in sorted(filenames):
            if f.startswith("."):
                continue
            p = os.path.join(dirpath, f)
            with open(p, "rb") as fh:
                data = fh.read()
            mode = 0o100755 if os.access(p, os.X_OK) else 0o100644
            entries.append((base + "/" + f, mode, data))
    return entries


# ------------------------------------------------------------------ xar
class Xar:
    def __init__(self):
        self.heap = io.BytesIO()
        self.heap.write(b"\0" * 20)          # Platz für TOC-Prüfsumme (SHA1)
        self.next_id = 1

    def file_xml(self, name, data, mode="0644"):
        off = self.heap.tell()
        self.heap.write(data)
        sha = hashlib.sha1(data).hexdigest()
        fid = self.next_id
        self.next_id += 1
        return (f'<file id="{fid}"><name>{escape(name)}</name><type>file</type><mode>{mode}</mode>'
                f'<uid>0</uid><gid>0</gid><user>root</user><group>wheel</group>'
                f'<data><length>{len(data)}</length><offset>{off}</offset><size>{len(data)}</size>'
                f'<encoding style="application/octet-stream"/>'
                f'<extracted-checksum style="sha1">{sha}</extracted-checksum>'
                f'<archived-checksum style="sha1">{sha}</archived-checksum></data></file>')

    def dir_xml(self, name, children):
        fid = self.next_id
        self.next_id += 1
        return (f'<file id="{fid}"><name>{escape(name)}</name><type>directory</type><mode>0755</mode>'
                f'<uid>0</uid><gid>0</gid><user>root</user><group>wheel</group>{"".join(children)}</file>')

    def build(self, files_xml):
        ctime = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())
        toc = ('<?xml version="1.0" encoding="UTF-8"?>\n<xar><toc>'
               '<checksum style="sha1"><offset>0</offset><size>20</size></checksum>'
               f'<creation-time>{ctime}</creation-time>{"".join(files_xml)}</toc></xar>').encode()
        ztoc = zlib.compress(toc, 9)
        heap = bytearray(self.heap.getvalue())
        heap[0:20] = hashlib.sha1(ztoc).digest()
        header = struct.pack(">4sHHQQI", b"xar!", 28, 1, len(ztoc), len(toc), 1)
        return header + ztoc + bytes(heap)


# ------------------------------------------------------------------ Paket
def main(macos_dir, out):
    with open(os.path.join(HERE, "postinstall"), "rb") as f:
        post = f.read()
    entries = [(".", 0o40755, None), ("./postinstall", 0o100755, post)]
    entries += collect(macos_dir, "./src")
    scripts = gzip.compress(cpio_odc(entries), 9, mtime=0)

    package_info = f'''<?xml version="1.0" encoding="utf-8"?>
<pkg-info overwrite-permissions="true" relocatable="false" identifier="{PKG_ID}" postinstall-action="none" version="{VERSION}" format-version="2" generator-version="thisismade-make_pkg" auth="root">
    <scripts>
        <postinstall file="./postinstall"/>
    </scripts>
    <bundle-version/>
    <upgrade-bundle/>
    <update-bundle/>
    <atomic-update-bundle/>
    <strict-identifier/>
    <relocate/>
</pkg-info>
'''.encode()

    distribution = f'''<?xml version="1.0" encoding="utf-8"?>
<installer-gui-script minSpecVersion="2">
    <title>thisismade cdp-2</title>
    <welcome file="welcome.html" mime-type="text/html"/>
    <conclusion file="conclusion.html" mime-type="text/html"/>
    <options customize="never" require-scripts="false" hostArchitectures="x86_64,arm64"/>
    <domains enable_anywhere="false" enable_currentUserHome="false" enable_localSystem="true"/>
    <volume-check>
        <allowed-os-versions>
            <os-version min="13.0"/>
        </allowed-os-versions>
    </volume-check>
    <choices-outline>
        <line choice="default">
            <line choice="{PKG_ID}"/>
        </line>
    </choices-outline>
    <choice id="default"/>
    <choice id="{PKG_ID}" visible="false">
        <pkg-ref id="{PKG_ID}"/>
    </choice>
    <pkg-ref id="{PKG_ID}" version="{VERSION}" onConclusion="none" installKBytes="0">#app.pkg</pkg-ref>
</installer-gui-script>
'''.encode()

    def res(name):
        with open(os.path.join(HERE, name), "rb") as f:
            return f.read()

    x = Xar()
    files = [x.file_xml("Distribution", distribution)]
    langs = [x.dir_xml(lang, [x.file_xml("welcome.html", res("welcome.html")),
                              x.file_xml("conclusion.html", res("conclusion.html"))])
             for lang in ("de.lproj", "en.lproj", "English.lproj")]
    files.append(x.dir_xml("Resources", langs))
    files.append(x.dir_xml("app.pkg", [
        x.file_xml("PackageInfo", package_info),
        x.file_xml("Scripts", scripts)]))
    with open(out, "wb") as f:
        f.write(x.build(files))
    print("Paket geschrieben:", out, os.path.getsize(out), "Bytes")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
