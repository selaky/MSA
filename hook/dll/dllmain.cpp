/**
 * MSA Hook DLL - DLL 入口点
 *
 * 注入到游戏进程后，Hook GetCursorPos 以支持后台点击
 */

#include <windows.h>
#include "shared_memory.h"
#include "hooks.h"

// 全局变量：标记是否已初始化
static BOOL g_bInitialized = FALSE;

// DLL 初始化
static BOOL Initialize() {
    // 避免重复初始化
    if (g_bInitialized) {
        return TRUE;
    }

    // 初始化共享内存
    if (!SharedMemory_Init()) {
        return FALSE;
    }

    // 初始化 Hook
    if (!Hooks_Init()) {
        SharedMemory_Cleanup();
        return FALSE;
    }

    g_bInitialized = TRUE;
    return TRUE;
}

// DLL 清理
static void Cleanup() {
    if (!g_bInitialized) {
        return;
    }

    Hooks_Cleanup();
    SharedMemory_Cleanup();

    g_bInitialized = FALSE;
}

// DLL 入口点
BOOL APIENTRY DllMain(HMODULE hModule, DWORD ul_reason_for_call, LPVOID lpReserved) {
    switch (ul_reason_for_call) {
    case DLL_PROCESS_ATTACH:
        // 禁用线程通知以提高性能
        DisableThreadLibraryCalls(hModule);
        // 初始化
        if (!Initialize()) {
            return FALSE;
        }
        break;

    case DLL_PROCESS_DETACH:
        // 清理资源
        Cleanup();
        break;

    case DLL_THREAD_ATTACH:
    case DLL_THREAD_DETACH:
        break;
    }

    return TRUE;
}
