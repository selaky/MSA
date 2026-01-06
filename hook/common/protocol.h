/**
 * MSA 后台点击 - 共享内存协议定义
 *
 * 控制器与 Hook DLL 通过命名共享内存通信
 */

#pragma once

#include <windows.h>
#include <stdint.h>

// 共享内存名称
#define MSA_SHARED_MEMORY_NAME L"Local\\MSA_BackgroundClick_SharedMemory"

// 协议版本号
#define MSA_PROTOCOL_VERSION 1

// 共享内存结构
#pragma pack(push, 1)
typedef struct _MSA_SHARED_DATA {
    // 协议版本，用于兼容性检查
    DWORD version;

    // Hook 是否生效
    // true: GetCursorPos 返回伪造坐标
    // false: GetCursorPos 透传原始 API
    BOOL enabled;

    // 目标坐标（客户区坐标）
    int target_x;
    int target_y;

    // 游戏窗口句柄，用于坐标转换
    HWND game_hwnd;

    // 被注入进程的 PID，用于检测进程是否存活
    DWORD injected_pid;

    // 保留字段，用于未来扩展
    BYTE reserved[32];
} MSA_SHARED_DATA, *PMSA_SHARED_DATA;
#pragma pack(pop)

// 共享内存大小
#define MSA_SHARED_MEMORY_SIZE sizeof(MSA_SHARED_DATA)
