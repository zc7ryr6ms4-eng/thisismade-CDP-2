// Windows-Mediensteuerung (SMTC): Medientasten, Lautstärke-Flyout und Sperrbildschirm zeigen Titel und Cover.
using System.Drawing.Imaging;
using System.Runtime.InteropServices.WindowsRuntime;
using Windows.Media;
using Windows.Storage.Streams;

namespace Thisismade;

sealed class MediaControls : IDisposable
{
    readonly Windows.Media.Playback.MediaPlayer mp;
    readonly SystemMediaTransportControls smtc;
    public bool Available => smtc != null;

    public MediaControls(Control ui, Player player)
    {
        try
        {
            mp = new Windows.Media.Playback.MediaPlayer();
            mp.CommandManager.IsEnabled = false;
            smtc = mp.SystemMediaTransportControls;
            smtc.IsEnabled = true;
            smtc.IsPlayEnabled = smtc.IsPauseEnabled = smtc.IsStopEnabled = true;
            smtc.IsNextEnabled = smtc.IsPreviousEnabled = true;
            smtc.ButtonPressed += (_, e) => ui.BeginInvoke((Action)(() =>
            {
                switch (e.Button)
                {
                    case SystemMediaTransportControlsButton.Play: player.Play(); break;
                    case SystemMediaTransportControlsButton.Pause: player.Pause(); break;
                    case SystemMediaTransportControlsButton.Stop: player.Stop(); break;
                    case SystemMediaTransportControlsButton.Next: player.NextTrack(); break;
                    case SystemMediaTransportControlsButton.Previous: player.PrevTrack(true); break;
                }
            }));
        }
        catch
        {
            smtc = null;
        }
    }

    public async void Update(Track t, System.Drawing.Image cover, bool playing, bool hasTrack)
    {
        if (smtc == null) return;
        try
        {
            smtc.PlaybackStatus = !hasTrack ? MediaPlaybackStatus.Closed
                : playing ? MediaPlaybackStatus.Playing : MediaPlaybackStatus.Paused;
            var du = smtc.DisplayUpdater;
            du.ClearAll();
            if (t != null)
            {
                du.Type = MediaPlaybackType.Music;
                du.MusicProperties.Title = t.Title ?? "";
                du.MusicProperties.Artist = t.Artist ?? "";
                du.MusicProperties.AlbumTitle = t.Album ?? "";
                if (cover != null)
                {
                    using var ms = new MemoryStream();
                    lock (cover) cover.Save(ms, ImageFormat.Png);
                    var ras = new InMemoryRandomAccessStream();
                    await ras.WriteAsync(ms.ToArray().AsBuffer());
                    ras.Seek(0);
                    du.Thumbnail = RandomAccessStreamReference.CreateFromStream(ras);
                }
            }
            du.Update();
        }
        catch { }
    }

    public void Dispose()
    {
        try { mp?.Dispose(); } catch { }
    }
}
