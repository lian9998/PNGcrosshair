'''
Overlay – shows overlay.png centred on every monitor
* click‑through, top‑most, pixel‑perfect (no scaling)
* run from a console – press Ctrl‑C to quit
'''
import os
import sys
import ctypes
from ctypes import wintypes
from PIL import Image

# --------------------------------------------------------------
# 1️⃣  Win‑API constants & type aliases
# --------------------------------------------------------------
user32   = ctypes.WinDLL('user32', use_last_error=True)
gdi32    = ctypes.WinDLL('gdi32',  use_last_error=True)
kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)

BYTE   = ctypes.c_ubyte
WORD   = ctypes.c_ushort
DWORD  = ctypes.c_ulong
LONG   = ctypes.c_long
INT    = ctypes.c_int
UINT   = ctypes.c_uint
HANDLE = wintypes.HANDLE
HWND   = wintypes.HWND
HDC    = wintypes.HDC
HBITMAP = wintypes.HBITMAP
HRGN   = wintypes.HRGN
WPARAM = wintypes.WPARAM
LPARAM = wintypes.LPARAM
LRESULT= ctypes.c_long
LPVOID = ctypes.c_void_p
HINSTANCE = wintypes.HINSTANCE
HBRUSH = HANDLE

# Window styles -------------------------------------------------
WS_EX_LAYERED     = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOPMOST     = 0x00000008
WS_EX_NOACTIVATE  = 0x00080000   # note: 0x08000 in the original script was a typo
WS_EX_TOOLWINDOW  = 0x00000080
WS_POPUP          = 0x80000000

# SetWindowPos flags -------------------------------------------
SWP_NOSIZE       = 0x0001
SWP_NOMOVE       = 0x0002
SWP_NOACTIVATE   = 0x0010
SWP_SHOWWINDOW   = 0x0040

# Messages ------------------------------------------------------
WM_DESTROY = 0x0002

# UpdateLayeredWindow flags ------------------------------------
ULW_ALPHA = 0x00000002

# --------------------------------------------------------------
# 2️⃣  Structures not present in ctypes.wintypes
# --------------------------------------------------------------
class BLENDFUNCTION(ctypes.Structure):
    _fields_ = [
        ("BlendOp",      BYTE),
        ("BlendFlags",   BYTE),
        ("SourceConstantAlpha", BYTE),
        ("AlphaFormat",  BYTE),
    ]

class POINT(ctypes.Structure):
    _fields_ = [("x", LONG), ("y", LONG)]

class SIZE(ctypes.Structure):
    _fields_ = [("cx", LONG), ("cy", LONG)]

class RECT(ctypes.Structure):
    _fields_ = [("left", LONG), ("top", LONG),
                ("right", LONG), ("bottom", LONG)]

class MONITORINFOEXW(ctypes.Structure):
    _fields_ = [("cbSize", DWORD),
                ("rcMonitor", RECT),
                ("rcWork", RECT),
                ("dwFlags", DWORD),
                ("szDevice", wintypes.WCHAR * 32)]

class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize",          DWORD),
        ("biWidth",         LONG),
        ("biHeight",        LONG),
        ("biPlanes",        WORD),
        ("biBitCount",      WORD),
        ("biCompression",  DWORD),
        ("biSizeImage",     DWORD),
        ("biXPelsPerMeter", LONG),
        ("biYPelsPerMeter", LONG),
        ("biClrUsed",       DWORD),
        ("biClrImportant",  DWORD),
    ]

class BITMAPINFO(ctypes.Structure):
    _fields_ = [("bmiHeader", BITMAPINFOHEADER),
                ("bmiColors", DWORD * 1)]

class WNDCLASSW(ctypes.Structure):
    _fields_ = [
        ("style",          UINT),
        ("lpfnWndProc",    ctypes.WINFUNCTYPE(LRESULT, HWND, UINT, WPARAM, LPARAM)),
        ("cbClsExtra",     ctypes.c_int),
        ("cbWndExtra",     ctypes.c_int),
        ("hInstance",      HINSTANCE),
        ("hIcon",          ctypes.c_void_p),
        ("hCursor",        ctypes.c_void_p),
        ("hbrBackground", HBRUSH),
        ("lpszMenuName",   wintypes.LPCWSTR),
        ("lpszClassName", wintypes.LPCWSTR),
    ]

# --------------------------------------------------------------
# 3️⃣  Function prototypes (only the ones we use)
# --------------------------------------------------------------
# DefWindowProc
user32.DefWindowProcW.restype = LRESULT
user32.DefWindowProcW.argtypes = (HWND, UINT, WPARAM, LPARAM)

# RegisterClassW
user32.RegisterClassW.restype = wintypes.ATOM
user32.RegisterClassW.argtypes = (ctypes.POINTER(WNDCLASSW),)

# CreateWindowExW
user32.CreateWindowExW.restype = HWND
user32.CreateWindowExW.argtypes = (DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR,
                                 DWORD, INT, INT, INT, INT,
                                 HWND, wintypes.HMENU, HINSTANCE,
                                 LPVOID)

# Message‑loop helpers
user32.GetMessageW.restype = wintypes.BOOL
user32.GetMessageW.argtypes = (ctypes.POINTER(wintypes.MSG), HWND, UINT, UINT)

user32.TranslateMessage.restype = wintypes.BOOL
user32.TranslateMessage.argtypes = (ctypes.POINTER(wintypes.MSG),)

user32.DispatchMessageW.restype = LRESULT
user32.DispatchMessageW.argtypes = (ctypes.POINTER(wintypes.MSG),)

user32.PostQuitMessage.restype = None
user32.PostQuitMessage.argtypes = (INT,)

user32.DestroyWindow.restype = wintypes.BOOL
user32.DestroyWindow.argtypes = (HWND,)

# Monitor enumeration
MONITORENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL,
                                     HDC, HDC,
                                     ctypes.POINTER(RECT),
                                     LPARAM)

user32.EnumDisplayMonitors.restype = wintypes.BOOL
user32.EnumDisplayMonitors.argtypes = (HDC,
                                      ctypes.POINTER(RECT),
                                      MONITORENUMPROC,
                                      LPARAM)

user32.GetMonitorInfoW.restype = wintypes.BOOL
user32.GetMonitorInfoW.argtypes = (HDC, ctypes.POINTER(MONITORINFOEXW))

# Window positioning
user32.SetWindowPos.restype = wintypes.BOOL
user32.SetWindowPos.argtypes = (HWND, HWND,
                               INT, INT, INT, INT,
                               UINT)

# UpdateLayeredWindow
user32.UpdateLayeredWindow.restype = wintypes.BOOL
user32.UpdateLayeredWindow.argtypes = (HWND, HDC,
                                      ctypes.POINTER(POINT),
                                      ctypes.POINTER(SIZE),
                                      HDC,
                                      ctypes.POINTER(POINT),
                                      DWORD,
                                      ctypes.POINTER(BLENDFUNCTION),
                                      DWORD)

# DC handling
user32.GetDC.restype = HDC
user32.GetDC.argtypes = (HWND,)

user32.ReleaseDC.restype = INT
user32.ReleaseDC.argtypes = (HWND, HDC)

# GDI helpers
gdi32.CreateCompatibleDC.restype = HDC
gdi32.CreateCompatibleDC.argtypes = (HDC,)

gdi32.DeleteDC.restype = wintypes.BOOL
gdi32.DeleteDC.argtypes = (HDC,)

gdi32.CreateDIBSection.restype = HBITMAP
gdi32.CreateDIBSection.argtypes = (HDC,
                                   ctypes.POINTER(BITMAPINFO),
                                   UINT,
                                   ctypes.POINTER(LPVOID),
                                   HANDLE,
                                   DWORD)

gdi32.SelectObject.restype = HANDLE
gdi32.SelectObject.argtypes = (HDC, HANDLE)

gdi32.DeleteObject.restype = wintypes.BOOL
gdi32.DeleteObject.argtypes = (HANDLE,)

# GetModuleHandle
kernel32.GetModuleHandleW.restype = HINSTANCE
kernel32.GetModuleHandleW.argtypes = (wintypes.LPCWSTR,)

# --------------------------------------------------------------
# 4️⃣  Load PNG → raw BGRA bytes (no scaling)
# --------------------------------------------------------------
def load_png(path: str):
    """Return (width, height, raw BGRA bytes)."""
    img = Image.open(path).convert('RGBA')
    w, h = img.size
    # Convert to BGRA – Windows expects this order
    b, g, r, a = img.split()
    img_bgra = Image.merge('RGBA', (b, g, r, a))
    raw = img_bgra.tobytes('raw', 'BGRA')
    return w, h, raw

# --------------------------------------------------------------
# 5️⃣  Window procedure (handles only WM_DESTROY)
# --------------------------------------------------------------
@ctypes.WINFUNCTYPE(LRESULT, HWND, UINT, WPARAM, LPARAM)
def wndproc(hwnd, msg, wparam, lparam):
    if msg == WM_DESTROY:
        user32.PostQuitMessage(0)
        return 0
    return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

# --------------------------------------------------------------
# 6️⃣  Register the window class **once**
# --------------------------------------------------------------
# Keep the class name in a module‑level variable so we can reuse it.
_CLASS_NAME = "PyOverlayWnd"

def _register_class_once():
    """Register the class if it hasn't been registered already."""
    # First try to register – if it already exists GetLastError == 1410.
    wc = WNDCLASSW()
    wc.style = 0
    wc.lpfnWndProc = wndproc
    wc.cbClsExtra = 0
    wc.cbWndExtra = 0
    wc.hInstance = kernel32.GetModuleHandleW(None)
    wc.hIcon = None
    wc.hCursor = None
    wc.hbrBackground = None
    wc.lpszMenuName = None
    wc.lpszClassName = _CLASS_NAME

    atom = user32.RegisterClassW(ctypes.byref(wc))
    if not atom:
        err = ctypes.get_last_error()
        # 1410 == CLASS_ALREADY_EXISTS – ignore, we can reuse it.
        if err != 1410:
            raise ctypes.WinError(err)
    return _CLASS_NAME

# --------------------------------------------------------------
# 7️⃣  Create a layered, click‑through window for a **single** monitor
# --------------------------------------------------------------
def create_overlay_window(monitor_info: MONITORINFOEXW,
                          img_w: int, img_h: int,
                          img_bytes: bytes) -> HWND:
    # ----- 7.1  Center the image on the monitor -----
    mon_w = monitor_info.rcMonitor.right - monitor_info.rcMonitor.left
    mon_h = monitor_info.rcMonitor.bottom - monitor_info.rcMonitor.top
    x = monitor_info.rcMonitor.left + (mon_w - img_w) // 2
    y = monitor_info.rcMonitor.top  + (mon_h - img_h) // 2

    # ----- 7.2  Create the window -----
    ex_style = (WS_EX_LAYERED | WS_EX_TRANSPARENT |
                WS_EX_TOPMOST | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW)

    hwnd = user32.CreateWindowExW(
        ex_style,
        _register_class_once(),   # re‑use the already‑registered class
        None,                     # window title – not needed for WS_POPUP
        WS_POPUP,
        x, y, img_w, img_h,
        None, None,
        kernel32.GetModuleHandleW(None),
        None)

    if not hwnd:
        raise ctypes.WinError(ctypes.get_last_error())

    # ----- 7.3  Build a 32‑bit DIB that holds the PNG data -----
    hdc_screen = user32.GetDC(None)          # screen DC
    hdc_mem    = gdi32.CreateCompatibleDC(hdc_screen)

    bmi = BITMAPINFO()
    bmi.bmiHeader.biSize        = ctypes.sizeof(BITMAPINFOHEADER)
    bmi.bmiHeader.biWidth       = img_w
    bmi.bmiHeader.biHeight      = -img_h          # top‑down DIB
    bmi.bmiHeader.biPlanes      = 1
    bmi.bmiHeader.biBitCount    = 32
    bmi.bmiHeader.biCompression = 0               # BI_RGB

    bits_ptr = LPVOID()
    hbm = gdi32.CreateDIBSection(
        hdc_mem,
        ctypes.byref(bmi),
        0,                 # DIB_RGB_COLORS
        ctypes.byref(bits_ptr),
        None,
        0)

    if not hbm:
        raise ctypes.WinError(ctypes.get_last_error())

    # copy pixel data into the DIB
    ctypes.memmove(bits_ptr, img_bytes, len(img_bytes))

    old_obj = gdi32.SelectObject(hdc_mem, hbm)

    # ----- 7.4  Paint it with UpdateLayeredWindow -----
    pt_win = POINT(x, y)
    sz     = SIZE(img_w, img_h)
    pt_src = POINT(0, 0)

    blend = BLENDFUNCTION()
    blend.BlendOp            = 0      # AC_SRC_OVER
    blend.BlendFlags         = 0
    blend.SourceConstantAlpha = 255   # per‑pixel alpha
    blend.AlphaFormat        = 1     # AC_SRC_ALPHA

    # Make the window visible before the first UpdateLayeredWindow call.
    # HWND_TOPMOST = -1, but we already set the WS_EX_TOPMOST flag;
    # passing None (NULL) is fine.
    user32.SetWindowPos(hwnd, None,
                        0, 0, 0, 0,
                        SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW)

    ok = user32.UpdateLayeredWindow(
        hwnd,
        hdc_screen,
        ctypes.byref(pt_win),
        ctypes.byref(sz),
        hdc_mem,
        ctypes.byref(pt_src),
        0,
        ctypes.byref(blend),
        ULW_ALPHA)

    # Clean up GDI objects we no longer need
    gdi32.SelectObject(hdc_mem, old_obj)
    gdi32.DeleteObject(hbm)
    gdi32.DeleteDC(hdc_mem)
    user32.ReleaseDC(None, hdc_screen)

    if not ok:
        raise ctypes.WinError(ctypes.get_last_error())

    return hwnd

# --------------------------------------------------------------
# 8️⃣  Enumerate monitors & create an overlay on each
# --------------------------------------------------------------
def enum_monitors(callback):
    """Calls *callback* once for every monitor (passing MONITORINFOEXW)."""
    @MONITORENUMPROC
    def proc(hmon, hdcMon, lprcMon, dwData):
        mi = MONITORINFOEXW()
        mi.cbSize = ctypes.sizeof(MONITORINFOEXW)
        if not user32.GetMonitorInfoW(hmon, ctypes.byref(mi)):
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            callback(mi)
        except Exception as exc:
            # Never let an exception escape the native callback.
            # Store it somewhere or just print – the outer code will
            # terminate gracefully after the enumeration finishes.
            print(f"Error while creating overlay for monitor {mi.szDevice!r}: {exc}",
                  file=sys.stderr)
        return True

    if not user32.EnumDisplayMonitors(None, None, proc, 0):
        raise ctypes.WinError(ctypes.get_last_error())

# --------------------------------------------------------------
# 9️⃣  Main program – message loop + Ctrl‑C handling
# --------------------------------------------------------------
def main():
    # ---- 9.1  Load the PNG (must be in the script's directory) ----
    script_dir = os.path.abspath(os.path.dirname(__file__))
    png_path = os.path.join(script_dir, "overlay.png")
    if not os.path.isfile(png_path):
        sys.exit("overlay.png not found in the script directory.")
    img_w, img_h, img_bytes = load_png(png_path)

    # ---- 9.2  Create a window on each monitor ----
    windows = []

    def make_one(mi):
        hwnd = create_overlay_window(mi, img_w, img_h, img_bytes)
        windows.append(hwnd)

    enum_monitors(make_one)

    # ---- 9.3  Message pump (runs until WM_QUIT) ----
    msg = wintypes.MSG()
    while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
        user32.TranslateMessage(ctypes.byref(msg))
        user32.DispatchMessageW(ctypes.byref(msg))

if __name__ == "__main__":
    main()