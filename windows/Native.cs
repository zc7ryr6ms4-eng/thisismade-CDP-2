// Windows-API-Aufrufe: Fenster verschieben/skalieren, Windows-11-Ecken, Ruhezustand, Einzelinstanz.
using System.Runtime.InteropServices;

namespace Thisismade;

static class Native
{
    public const int WM_NCLBUTTONDOWN = 0xA1, WM_NCHITTEST = 0x84, WM_SIZING = 0x214, WM_COPYDATA = 0x4A;
    public const int HTCAPTION = 2, HTLEFT = 10, HTRIGHT = 11, HTTOP = 12, HTTOPLEFT = 13, HTTOPRIGHT = 14,
                     HTBOTTOM = 15, HTBOTTOMLEFT = 16, HTBOTTOMRIGHT = 17;
    public const int WMSZ_LEFT = 1, WMSZ_RIGHT = 2, WMSZ_TOP = 3, WMSZ_TOPLEFT = 4, WMSZ_TOPRIGHT = 5,
                     WMSZ_BOTTOM = 6, WMSZ_BOTTOMLEFT = 7, WMSZ_BOTTOMRIGHT = 8;

    [DllImport("user32.dll")] public static extern bool ReleaseCapture();
    [DllImport("user32.dll")] public static extern IntPtr SendMessage(IntPtr hWnd, int msg, IntPtr wParam, IntPtr lParam);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] public static extern IntPtr FindWindow(string cls, string title);
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int cmd);
    [DllImport("dwmapi.dll")] static extern int DwmSetWindowAttribute(IntPtr hwnd, int attr, ref int value, int size);
    [DllImport("dwmapi.dll")] static extern int DwmExtendFrameIntoClientArea(IntPtr hwnd, ref Margins m);
    [DllImport("kernel32.dll")] static extern uint SetThreadExecutionState(uint flags);

    [StructLayout(LayoutKind.Sequential)]
    struct Margins { public int Left, Right, Top, Bottom; }

    [StructLayout(LayoutKind.Sequential)]
    public struct RECT { public int Left, Top, Right, Bottom; }

    [StructLayout(LayoutKind.Sequential)]
    public struct COPYDATASTRUCT { public IntPtr dwData; public int cbData; public IntPtr lpData; }

    /// <summary>Windows-11-Ecken und Schatten für das randlose Fenster.</summary>
    public static void StyleWindow(IntPtr hwnd)
    {
        try
        {
            int round = 2;                                   // DWMWCP_ROUND
            DwmSetWindowAttribute(hwnd, 33, ref round, sizeof(int));
            var m = new Margins { Left = 0, Right = 0, Top = 1, Bottom = 0 };
            DwmExtendFrameIntoClientArea(hwnd, ref m);
        }
        catch { }
    }

    public static void KeepAwake(bool on)
    {
        const uint ES_CONTINUOUS = 0x80000000, ES_SYSTEM_REQUIRED = 0x00000001;
        SetThreadExecutionState(on ? ES_CONTINUOUS | ES_SYSTEM_REQUIRED : ES_CONTINUOUS);
    }

    /// <summary>Pfade an eine bereits laufende Instanz schicken.</summary>
    public static bool SendToRunning(string title, string[] args)
    {
        var h = FindWindow(null, title);
        if (h == IntPtr.Zero) return false;
        var text = string.Join("\n", args);
        var ptr = Marshal.StringToHGlobalUni(text);
        try
        {
            var cds = new COPYDATASTRUCT { dwData = (IntPtr)0x544D, cbData = (text.Length + 1) * 2, lpData = ptr };
            var p = Marshal.AllocHGlobal(Marshal.SizeOf<COPYDATASTRUCT>());
            Marshal.StructureToPtr(cds, p, false);
            SendMessage(h, WM_COPYDATA, IntPtr.Zero, p);
            Marshal.FreeHGlobal(p);
            ShowWindow(h, 9);
            SetForegroundWindow(h);
        }
        finally { Marshal.FreeHGlobal(ptr); }
        return true;
    }
}
