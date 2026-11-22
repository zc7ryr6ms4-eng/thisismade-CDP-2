# Im Ubuntu Snap Store veröffentlichen

Der Build auf GitHub lädt das Snap automatisch in den Snap Store hoch, sobald der
Zugangsschlüssel hinterlegt ist:

* **Release veröffentlicht** → Kanal **stable** (für alle sichtbar)
* **Push auf main** → Kanal **edge** (zum Testen: `sudo snap install thisismade-cdp-2 --edge`)

## Einmalige Einrichtung (ca. 10 Minuten)

1. **Konto anlegen:** https://snapcraft.io/account → mit einem Ubuntu-One-Konto anmelden
   und die Entwicklervereinbarung bestätigen.
2. **Namen reservieren:** https://snapcraft.io/register-snap → `thisismade-cdp-2` eintragen.
3. **Zugangsschlüssel erzeugen** (auf deinem Ubuntu-Rechner):
   ```bash
   sudo snap install snapcraft --classic
   snapcraft export-login --snaps thisismade-cdp-2 --acls package_access,package_push,package_update,package_release snapcraft-login.txt
   ```
   Melde dich mit deinem Snapcraft-Konto an. Danach liegt der Schlüssel in `snapcraft-login.txt`.
4. **Schlüssel bei GitHub hinterlegen:** Repository → **Settings → Secrets and variables → Actions →
   New repository secret**
   * Name: `SNAPCRAFT_STORE_CREDENTIALS`
   * Secret: kompletter Inhalt von `snapcraft-login.txt`

   Danach `snapcraft-login.txt` löschen – der Schlüssel erlaubt Uploads in deinem Namen.
5. **Veröffentlichen:** ein neues Release anlegen (oder unter **Actions → Build & Release →
   Run workflow** mit dem Tag eines bestehenden Releases starten).

Beim ersten Hochladen prüft der Snap Store das Paket automatisch. Wird eine manuelle Prüfung
verlangt (z. B. für die Schnittstellen `mpris` oder `optical-drive`), schreibt Canonical das
in die Upload-Übersicht auf https://snapcraft.io/thisismade-cdp-2/releases.

Nach der Freigabe installiert man den Player mit:
```bash
sudo snap install thisismade-cdp-2
```
