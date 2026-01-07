/**
 * MSA Proxy DLL - DLL 入口点
 *
 * 加载原版 MaaWin32ControlUnit_original.dll
 */

#include <windows.h>
#include <string>

// 原版 DLL 句柄
static HMODULE g_hOriginalDll = nullptr;

// 原版 DLL 文件名
static const wchar_t* ORIGINAL_DLL_NAME = L"MaaWin32ControlUnit_original.dll";

/**
 * 获取原版 DLL 句柄
 */
HMODULE GetOriginalDll()
{
    return g_hOriginalDll;
}

/**
 * 加载原版 DLL
 */
static bool LoadOriginalDll()
{
    if (g_hOriginalDll != nullptr) {
        return true;
    }

    // 获取当前 DLL 所在目录
    wchar_t modulePath[MAX_PATH] = { 0 };
    HMODULE hSelf = nullptr;

    // 获取当前 DLL 的句柄
    if (!GetModuleHandleExW(
            GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS | GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
            reinterpret_cast<LPCWSTR>(&LoadOriginalDll),
            &hSelf)) {
        return false;
    }

    // 获取当前 DLL 的完整路径
    if (GetModuleFileNameW(hSelf, modulePath, MAX_PATH) == 0) {
        return false;
    }

    // 找到最后一个反斜杠，截取目录部分
    std::wstring dllDir(modulePath);
    size_t lastSlash = dllDir.find_last_of(L"\\/");
    if (lastSlash != std::wstring::npos) {
        dllDir = dllDir.substr(0, lastSlash + 1);
    }

    // 构建原版 DLL 的完整路径
    std::wstring originalDllPath = dllDir + ORIGINAL_DLL_NAME;

    // 加载原版 DLL
    g_hOriginalDll = LoadLibraryW(originalDllPath.c_str());

    return g_hOriginalDll != nullptr;
}

/**
 * 卸载原版 DLL
 */
static void UnloadOriginalDll()
{
    if (g_hOriginalDll != nullptr) {
        FreeLibrary(g_hOriginalDll);
        g_hOriginalDll = nullptr;
    }
}

/**
 * DLL 入口点
 */
BOOL APIENTRY DllMain(HMODULE hModule, DWORD ul_reason_for_call, LPVOID lpReserved)
{
    switch (ul_reason_for_call) {
    case DLL_PROCESS_ATTACH:
        // 禁用线程通知以提高性能
        DisableThreadLibraryCalls(hModule);

        // 加载原版 DLL
        if (!LoadOriginalDll()) {
            // 加载失败，返回 FALSE 会导致 DLL 加载失败
            return FALSE;
        }
        break;

    case DLL_PROCESS_DETACH:
        // 卸载原版 DLL
        UnloadOriginalDll();
        break;

    case DLL_THREAD_ATTACH:
    case DLL_THREAD_DETACH:
        break;
    }

    return TRUE;
}
