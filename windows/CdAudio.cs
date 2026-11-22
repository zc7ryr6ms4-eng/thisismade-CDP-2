// Audio-CD direkt vom Laufwerk lesen (IOCTL_CDROM_READ_TOC / IOCTL_CDROM_RAW_READ).
using System.Runtime.InteropServices;
using Microsoft.Win32.SafeHandles;
using NAudio.Wave;

namespace Thisismade;

public static class CdAudio
{
    const uint GENERIC_READ = 0x80000000;
    const uint FILE_SHARE_READ = 1, FILE_SHARE_WRITE = 2, OPEN_EXISTING = 3;
    const uint IOCTL_CDROM_READ_TOC = 0x00024000;
    const uint IOCTL_CDROM_RAW_READ = 0x0002403E;
    const int SectorBytes = 2352;

    [DllImport("kernel32.dll", SetLastError = true, CharSet = CharSet.Unicode)]
    static extern SafeFileHandle CreateFile(string name, uint access, uint share, IntPtr sec, uint disp, uint flags, IntPtr tmpl);

    [DllImport("kernel32.dll", SetLastError = true)]
    static extern bool DeviceIoControl(SafeFileHandle h, uint code, byte[] inBuf, int inSize, byte[] outBuf, int outSize,
                                       out int returned, IntPtr overlapped);

    public record Track(int Number, long StartLba, long Sectors);

    static SafeFileHandle OpenDrive(char letter)
    {
        var h = CreateFile($@"\\.\{letter}:", GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE, IntPtr.Zero, OPEN_EXISTING, 0, IntPtr.Zero);
        if (h.IsInvalid) throw new IOException($"Laufwerk {letter}: nicht lesbar (Fehler {Marshal.GetLastWin32Error()})");
        return h;
    }

    /// <summary>Audio-Titel der CD im Laufwerk (Datentitel werden übersprungen).</summary>
    public static List<Track> ReadToc(char letter)
    {
        using var h = OpenDrive(letter);
        var toc = new byte[804];
        if (!DeviceIoControl(h, IOCTL_CDROM_READ_TOC, null, 0, toc, toc.Length, out _, IntPtr.Zero))
            throw new IOException("Inhaltsverzeichnis der CD nicht lesbar");
        int first = toc[2], last = toc[3];
        var starts = new List<(int num, int ctrl, long lba)>();
        for (int i = 0; i <= last - first + 1; i++)
        {
            int o = 4 + i * 8;
            int ctrl = toc[o + 1] & 0x0F;          // Control = untere 4 Bit
            int num = toc[o + 2];
            long lba = (toc[o + 5] * 60L + toc[o + 6]) * 75 + toc[o + 7] - 150;
            starts.Add((num, ctrl, lba));
        }
        var tracks = new List<Track>();
        for (int i = 0; i < starts.Count - 1; i++)
        {
            if ((starts[i].ctrl & 0x4) != 0) continue;   // Datentitel
            tracks.Add(new Track(starts[i].num, starts[i].lba, starts[i + 1].lba - starts[i].lba));
        }
        return tracks;
    }

    public static char? FindAudioCd()
    {
        foreach (var d in DriveInfo.GetDrives())
        {
            if (d.DriveType != DriveType.CDRom) continue;
            try { if (ReadToc(d.Name[0]).Count > 0) return d.Name[0]; } catch { }
        }
        return null;
    }

    /// <summary>"cdda://D/3" → WaveStream für Titel 3 auf Laufwerk D.</summary>
    public static WaveStream OpenTrack(string uri)
    {
        var parts = uri["cdda://".Length..].Split('/');
        char letter = parts[0][0];
        int num = int.Parse(parts[1]);
        var t = ReadToc(letter).First(x => x.Number == num);
        return new TrackStream(OpenDrive(letter), t);
    }

    sealed class TrackStream : WaveStream
    {
        readonly SafeFileHandle h;
        readonly Track t;
        long pos;                         // Bytes ab Titelanfang
        readonly byte[] raw = new byte[SectorBytes * 24];
        readonly byte[] info = new byte[16];

        public TrackStream(SafeFileHandle handle, Track track) { h = handle; t = track; }
        public override WaveFormat WaveFormat { get; } = new WaveFormat(44100, 16, 2);
        public override long Length => t.Sectors * SectorBytes;
        public override long Position
        {
            get => pos;
            set => pos = Math.Clamp(value - value % 4, 0, Length);
        }

        public override int Read(byte[] buffer, int offset, int count)
        {
            int total = 0;
            while (count > 0 && pos < Length)
            {
                long sector = pos / SectorBytes;
                int within = (int)(pos % SectorBytes);
                int n = (int)Math.Min(24, t.Sectors - sector);
                long lba = t.StartLba + sector;
                BitConverter.GetBytes(lba * 2048).CopyTo(info, 0);
                BitConverter.GetBytes(n).CopyTo(info, 8);
                BitConverter.GetBytes(2).CopyTo(info, 12);          // CDDA
                if (!DeviceIoControl(h, IOCTL_CDROM_RAW_READ, info, info.Length, raw, n * SectorBytes, out int got, IntPtr.Zero) || got <= within)
                    break;
                int take = Math.Min(count, got - within);
                take = (int)Math.Min(take, Length - pos);
                Array.Copy(raw, within, buffer, offset, take);
                offset += take; count -= take; total += take; pos += take;
            }
            return total;
        }

        protected override void Dispose(bool disposing)
        {
            if (disposing) h.Dispose();
            base.Dispose(disposing);
        }
    }
}
