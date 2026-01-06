/**
 * MSA Hook DLL - 共享内存访问实现（DLL 端）
 */

#include "shared_memory.h"

// 全局变量
static HANDLE g_hMapFile = NULL;
static PMSA_SHARED_DATA g_pSharedData = NULL;

bool SharedMemory_Init() {
    // 如果已经初始化，直接返回
    if (g_pSharedData != NULL) {
        return true;
    }

    // 打开已存在的共享内存（由控制器创建）
    g_hMapFile = OpenFileMappingW(
        FILE_MAP_ALL_ACCESS,
        FALSE,
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

    // 验证协议版本
    if (g_pSharedData->version != MSA_PROTOCOL_VERSION) {
        UnmapViewOfFile(g_pSharedData);
        CloseHandle(g_hMapFile);
        g_pSharedData = NULL;
        g_hMapFile = NULL;
        return false;
    }

    return true;
}

void SharedMemory_Cleanup() {
    if (g_pSharedData != NULL) {
        UnmapViewOfFile(g_pSharedData);
        g_pSharedData = NULL;
    }

    if (g_hMapFile != NULL) {
        CloseHandle(g_hMapFile);
        g_hMapFile = NULL;
    }
}

PMSA_SHARED_DATA SharedMemory_GetData() {
    return g_pSharedData;
}

bool SharedMemory_IsValid() {
    return g_pSharedData != NULL;
}
