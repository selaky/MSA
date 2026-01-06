/**
 * MSA 自定义控制器 - 共享内存访问实现（控制器端）
 */

#include "shared_memory.h"
#include <stdio.h>

// 全局变量
static HANDLE g_hMapFile = NULL;
static PMSA_SHARED_DATA g_pSharedData = NULL;

bool ControllerSharedMemory_Init() {
    // 如果已经初始化，直接返回
    if (g_pSharedData != NULL) {
        return true;
    }

    // 创建共享内存
    g_hMapFile = CreateFileMappingW(
        INVALID_HANDLE_VALUE,
        NULL,
        PAGE_READWRITE,
        0,
        MSA_SHARED_MEMORY_SIZE,
        MSA_SHARED_MEMORY_NAME
    );

    if (g_hMapFile == NULL) {
        return false;
    }

    // 映射共享内存
    g_pSharedData = (PMSA_SHARED_DATA)MapViewOfFile(
        g_hMapFile,
        FILE_MAP_ALL_ACCESS,
        0,
        0,
        MSA_SHARED_MEMORY_SIZE
    );

    if (g_pSharedData == NULL) {
        CloseHandle(g_hMapFile);
        g_hMapFile = NULL;
        return false;
    }

    // 初始化共享数据
    memset(g_pSharedData, 0, MSA_SHARED_MEMORY_SIZE);
    g_pSharedData->version = MSA_PROTOCOL_VERSION;
    g_pSharedData->enabled = FALSE;

    return true;
}

void ControllerSharedMemory_Cleanup() {
    if (g_pSharedData != NULL) {
        UnmapViewOfFile(g_pSharedData);
        g_pSharedData = NULL;
    }

    if (g_hMapFile != NULL) {
        CloseHandle(g_hMapFile);
        g_hMapFile = NULL;
    }
}

PMSA_SHARED_DATA ControllerSharedMemory_GetData() {
    return g_pSharedData;
}

bool ControllerSharedMemory_IsValid() {
    return g_pSharedData != NULL;
}

void ControllerSharedMemory_SetGameHwnd(HWND hwnd) {
    if (g_pSharedData != NULL) {
        g_pSharedData->game_hwnd = hwnd;
    }
}

void ControllerSharedMemory_SetInjectedPid(DWORD pid) {
    if (g_pSharedData != NULL) {
        g_pSharedData->injected_pid = pid;
    }
}

void ControllerSharedMemory_SetTargetPos(int x, int y) {
    if (g_pSharedData != NULL) {
        g_pSharedData->target_x = x;
        g_pSharedData->target_y = y;
    }
}

void ControllerSharedMemory_SetEnabled(bool enabled) {
    if (g_pSharedData != NULL) {
        g_pSharedData->enabled = enabled ? TRUE : FALSE;
    }
}
