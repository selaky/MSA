/**
 * MSA Hook DLL - GetCursorPos Hook 实现
 */

#include "hooks.h"
#include "shared_memory.h"
#include "../third_party/minhook/include/MinHook.h"

// 原始函数指针
static BOOL(WINAPI* g_pOriginalGetCursorPos)(LPPOINT lpPoint) = NULL;

// Hook 函数
static BOOL WINAPI HookedGetCursorPos(LPPOINT lpPoint) {
    PMSA_SHARED_DATA pData = SharedMemory_GetData();

    // 如果共享内存无效或未启用，透传原始 API
    if (pData == NULL || !pData->enabled) {
        return g_pOriginalGetCursorPos(lpPoint);
    }

    // 如果输出参数无效，透传原始 API
    if (lpPoint == NULL) {
        return g_pOriginalGetCursorPos(lpPoint);
    }

    // 将客户区坐标转换为屏幕坐标
    POINT clientPoint;
    clientPoint.x = pData->target_x;
    clientPoint.y = pData->target_y;

    // 使用 ClientToScreen 转换坐标
    if (pData->game_hwnd != NULL && IsWindow(pData->game_hwnd)) {
        if (ClientToScreen(pData->game_hwnd, &clientPoint)) {
            lpPoint->x = clientPoint.x;
            lpPoint->y = clientPoint.y;
            return TRUE;
        }
    }

    // 转换失败时，透传原始 API
    return g_pOriginalGetCursorPos(lpPoint);
}

bool Hooks_Init() {
    // 初始化 MinHook
    MH_STATUS status = MH_Initialize();
    if (status != MH_OK && status != MH_ERROR_ALREADY_INITIALIZED) {
        return false;
    }

    // 创建 GetCursorPos Hook
    status = MH_CreateHookApi(
        L"user32",
        "GetCursorPos",
        (LPVOID)HookedGetCursorPos,
        (LPVOID*)&g_pOriginalGetCursorPos
    );

    if (status != MH_OK) {
        return false;
    }

    // 启用 Hook
    status = MH_EnableHook(MH_ALL_HOOKS);
    if (status != MH_OK) {
        return false;
    }

    return true;
}

void Hooks_Cleanup() {
    // 禁用所有 Hook
    MH_DisableHook(MH_ALL_HOOKS);

    // 反初始化 MinHook
    MH_Uninitialize();

    g_pOriginalGetCursorPos = NULL;
}
