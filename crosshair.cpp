#include <windows.h>
#include <gdiplus.h>
#include <iostream>
#include <vector>
#include <memory>
#pragma comment(lib, "gdiplus.lib")
#pragma comment(lib, "user32.lib")
#pragma comment(lib, "gdi32.lib")

// Global variables
std::vector<HWND> g_windows;
HWND g_controlWindow = NULL;
ULONG_PTR g_gdiplusToken = 0;

// Forward declarations
LRESULT CALLBACK WndProc(HWND hwnd, UINT msg, WPARAM wParam, LPARAM lParam);
LRESULT CALLBACK ControlWndProc(HWND hwnd, UINT msg, WPARAM wParam, LPARAM lParam);
BOOL CALLBACK MonitorEnumProc(HMONITOR hMonitor, HDC hdcMonitor, LPRECT lprcMonitor, LPARAM dwData);
HWND CreateOverlayWindow(const RECT& monitorRect, int imgWidth, int imgHeight, const std::vector<BYTE>& imgData);
HWND CreateControlWindow(HINSTANCE hInstance);
std::vector<BYTE> LoadPNG(const std::wstring& filePath, int& width, int& height);

// Window class names
const wchar_t* OVERLAY_CLASS_NAME = L"OverlayWindowClass";
const wchar_t* CONTROL_CLASS_NAME = L"ControlWindowClass";

void CleanupAndExit()
{
    // Cleanup overlay windows
    for (HWND hwnd : g_windows)
    {
        DestroyWindow(hwnd);
    }

    // Cleanup control window
    if (g_controlWindow)
    {
        DestroyWindow(g_controlWindow);
    }

    // Shutdown GDI+
    if (g_gdiplusToken)
    {
        Gdiplus::GdiplusShutdown(g_gdiplusToken);
    }

    PostQuitMessage(0);
}

int WINAPI WinMain(HINSTANCE hInstance, HINSTANCE hPrevInstance, LPSTR lpCmdLine, int nCmdShow)
{
    // Initialize GDI+
    Gdiplus::GdiplusStartupInput gdiplusStartupInput;
    Gdiplus::GdiplusStartup(&g_gdiplusToken, &gdiplusStartupInput, NULL);

    // Register overlay window class
    WNDCLASSEX wc = {};
    wc.cbSize = sizeof(WNDCLASSEX);
    wc.lpfnWndProc = WndProc;
    wc.hInstance = GetModuleHandle(NULL);
    wc.lpszClassName = OVERLAY_CLASS_NAME;
    if (!RegisterClassEx(&wc))
    {
        std::wcerr << L"Failed to register overlay window class: " << GetLastError() << std::endl;
        return 1;
    }

    // Register control window class
    WNDCLASSEX controlWc = {};
    controlWc.cbSize = sizeof(WNDCLASSEX);
    controlWc.lpfnWndProc = ControlWndProc;
    controlWc.hInstance = GetModuleHandle(NULL);
    controlWc.hIcon = LoadIcon(NULL, IDI_APPLICATION);
    controlWc.hCursor = LoadCursor(NULL, IDC_ARROW);
    controlWc.hbrBackground = (HBRUSH)(COLOR_WINDOW + 1);
    controlWc.lpszClassName = CONTROL_CLASS_NAME;
    controlWc.lpszMenuName = NULL;
    controlWc.style = CS_HREDRAW | CS_VREDRAW;

    if (!RegisterClassEx(&controlWc))
    {
        std::wcerr << L"Failed to register control window class: " << GetLastError() << std::endl;
        return 1;
    }

    // Create control window first
    g_controlWindow = CreateControlWindow(hInstance);
    if (!g_controlWindow)
    {
        std::wcerr << L"Failed to create control window: " << GetLastError() << std::endl;
        return 1;
    }

    // Load PNG image
    int imgWidth, imgHeight;
    std::vector<BYTE> imgData;
    wchar_t exePath[MAX_PATH];
    GetModuleFileName(NULL, exePath, MAX_PATH);
    std::wstring exeDir = exePath;
    exeDir = exeDir.substr(0, exeDir.find_last_of(L'\\'));
    std::wstring pngPath = exeDir + L"\\overlay.png";

    try
    {
        imgData = LoadPNG(pngPath, imgWidth, imgHeight);
    }
    catch (const std::exception& e)
    {
        std::wcerr << L"Failed to load overlay.png: " << e.what() << std::endl;
        // Don't exit here - let the user close the control window
    }

    // Create overlay windows on all monitors (only if PNG loaded successfully)
    if (!imgData.empty())
    {
        auto imgDataPair = std::make_pair(imgWidth, imgHeight);
        if (!EnumDisplayMonitors(NULL, NULL, MonitorEnumProc, reinterpret_cast<LPARAM>(&imgDataPair)))
        {
            std::wcerr << L"Failed to enumerate monitors: " << GetLastError() << std::endl;
        }
    }

    // Message loop
    MSG msg;
    while (GetMessage(&msg, NULL, 0, 0))
    {
        TranslateMessage(&msg);
        DispatchMessage(&msg);
    }

    CleanupAndExit();
    return 0;
}

LRESULT CALLBACK WndProc(HWND hwnd, UINT msg, WPARAM wParam, LPARAM lParam)
{
    switch (msg)
    {
    case WM_DESTROY:
    {

        // Overlay window destroyed - remove from list
        auto it = std::find(g_windows.begin(), g_windows.end(), hwnd);
        if (it != g_windows.end())
        {
            g_windows.erase(it);
        }
    }
        return 0;
    default:
        return DefWindowProc(hwnd, msg, wParam, lParam);
    }
}

LRESULT CALLBACK ControlWndProc(HWND hwnd, UINT msg, WPARAM wParam, LPARAM lParam)
{
    switch (msg)
    {
    case WM_CLOSE:
        CleanupAndExit();
        return 0;

    case WM_DESTROY:
        PostQuitMessage(0);
        return 0;

    default:
        return DefWindowProc(hwnd, msg, wParam, lParam);
    }
    return 0;
}

BOOL CALLBACK MonitorEnumProc(HMONITOR hMonitor, HDC hdcMonitor, LPRECT lprcMonitor, LPARAM dwData)
{
    auto* imgData = reinterpret_cast<std::pair<int, int>*>(dwData);
    MONITORINFO monitorInfo = {};
    monitorInfo.cbSize = sizeof(MONITORINFO);
    if (!GetMonitorInfo(hMonitor, &monitorInfo))
    {
        std::wcerr << L"Failed to get monitor info: " << GetLastError() << std::endl;
        return TRUE; // Continue enumeration
    }

    // Load PNG data for this window
    wchar_t exePath[MAX_PATH];
    GetModuleFileName(NULL, exePath, MAX_PATH);
    std::wstring exeDir = exePath;
    exeDir = exeDir.substr(0, exeDir.find_last_of(L'\\'));
    std::wstring pngPath = exeDir + L"\\overlay.png";
    int imgWidth, imgHeight;
    std::vector<BYTE> imgDatatmp;
    try
    {
        imgDatatmp = LoadPNG(pngPath, imgWidth, imgHeight);
    }
    catch (const std::exception& e)
    {
        std::wcerr << L"Failed to load PNG for monitor: " << e.what() << std::endl;
        return TRUE;
    }

    HWND hwnd = CreateOverlayWindow(monitorInfo.rcMonitor, imgWidth, imgHeight, imgDatatmp);
    if (hwnd)
    {
        g_windows.push_back(hwnd);
    }
    return TRUE; // Continue enumeration
}

HWND CreateControlWindow(HINSTANCE hInstance)
{
    // Calculate position (center of primary monitor)
    int width = 300;
    int height = 150;
    int x = (GetSystemMetrics(SM_CXSCREEN) - width) / 2;
    int y = (GetSystemMetrics(SM_CYSCREEN) - height) / 2;

    HWND hwnd = CreateWindowEx(
        0,
        CONTROL_CLASS_NAME,
        L"Overlay Control",
        WS_OVERLAPPEDWINDOW & ~WS_MAXIMIZEBOX, // No resize, no maximize
        x, y, width, height,
        NULL, NULL,
        hInstance,
        NULL);

    if (hwnd)
    {
        ShowWindow(hwnd, SW_SHOW);
        UpdateWindow(hwnd);
    }

    return hwnd;
}

HWND CreateOverlayWindow(const RECT& monitorRect, int imgWidth, int imgHeight, const std::vector<BYTE>& imgData)
{
    // Calculate centered position
    int monitorWidth = monitorRect.right - monitorRect.left;
    int monitorHeight = monitorRect.bottom - monitorRect.top;
    int x = monitorRect.left + (monitorWidth - imgWidth) / 2;
    int y = monitorRect.top + (monitorHeight - imgHeight) / 2;

    // Create window
    DWORD exStyle = WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOPMOST | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW;
    DWORD style = WS_POPUP;
    HWND hwnd = CreateWindowEx(
        exStyle,
        OVERLAY_CLASS_NAME,
        NULL,
        style,
        x, y, imgWidth, imgHeight,
        NULL, NULL,
        GetModuleHandle(NULL),
        NULL);
    if (!hwnd)
    {
        std::wcerr << L"Failed to create overlay window: " << GetLastError() << std::endl;
        return NULL;
    }

    // Create compatible DC and bitmap
    HDC hdcScreen = GetDC(NULL);
    HDC hdcMem = CreateCompatibleDC(hdcScreen);
    BITMAPINFO bmi = {};
    bmi.bmiHeader.biSize = sizeof(BITMAPINFOHEADER);
    bmi.bmiHeader.biWidth = imgWidth;
    bmi.bmiHeader.biHeight = -imgHeight; // Top-down
    bmi.bmiHeader.biPlanes = 1;
    bmi.bmiHeader.biBitCount = 32;
    bmi.bmiHeader.biCompression = BI_RGB;
    void* bits = nullptr;
    HBITMAP hBitmap = CreateDIBSection(
        hdcMem, &bmi, DIB_RGB_COLORS, &bits, NULL, 0);
    if (!hBitmap)
    {
        std::wcerr << L"Failed to create DIB section: " << GetLastError() << std::endl;
        DeleteDC(hdcMem);
        ReleaseDC(NULL, hdcScreen);
        DestroyWindow(hwnd);
        return NULL;
    }

    // Copy image data to bitmap
    memcpy(bits, imgData.data(), imgData.size());
    HGDIOBJ oldBitmap = SelectObject(hdcMem, hBitmap);

    // Set up layered window
    POINT ptPos = { x, y };
    SIZE sizeWindow = { imgWidth, imgHeight };
    POINT ptSrc = { 0, 0 };
    BLENDFUNCTION blend = {};
    blend.BlendOp = AC_SRC_OVER;
    blend.BlendFlags = 0;
    blend.SourceConstantAlpha = 255;
    blend.AlphaFormat = AC_SRC_ALPHA;

    // Make window visible and update
    SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0,
        SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW);
    BOOL result = UpdateLayeredWindow(
        hwnd, hdcScreen, &ptPos, &sizeWindow,
        hdcMem, &ptSrc, 0, &blend, ULW_ALPHA);

    // Cleanup
    SelectObject(hdcMem, oldBitmap);
    DeleteObject(hBitmap);
    DeleteDC(hdcMem);
    ReleaseDC(NULL, hdcScreen);

    if (!result)
    {
        std::wcerr << L"Failed to update layered window: " << GetLastError() << std::endl;
        DestroyWindow(hwnd);
        return NULL;
    }

    return hwnd;
}
std::vector<BYTE> LoadPNG(const std::wstring& filePath, int& width, int& height)
{
    Gdiplus::Bitmap bitmap(filePath.c_str());
    if (bitmap.GetLastStatus() != Gdiplus::Ok)
    {
        throw std::runtime_error("Failed to load PNG file");
    }

    width = bitmap.GetWidth();
    height = bitmap.GetHeight();

    Gdiplus::BitmapData bitmapData;
    Gdiplus::Rect rect(0, 0, width, height);


    if (bitmap.LockBits(&rect, Gdiplus::ImageLockModeRead, PixelFormat32bppARGB, &bitmapData) != Gdiplus::Ok)
    {
        throw std::runtime_error("Failed to lock bitmap bits");
    }

    std::vector<BYTE> result(width * height * 4);


    memcpy(result.data(), bitmapData.Scan0, result.size());

    bitmap.UnlockBits(&bitmapData);

    return result;
}