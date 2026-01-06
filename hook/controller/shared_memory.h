/**
 * MSA 自定义控制器 - 共享内存访问（控制器端）
 *
 * 控制器端负责创建共享内存，Hook DLL 端负责打开
 */

#pragma once

#include "../common/protocol.h"

// 初始化共享内存（创建新的共享内存）
bool ControllerSharedMemory_Init();

// 清理共享内存
void ControllerSharedMemory_Cleanup();

// 获取共享数据指针
PMSA_SHARED_DATA ControllerSharedMemory_GetData();

// 检查共享内存是否有效
bool ControllerSharedMemory_IsValid();

// 设置游戏窗口句柄
void ControllerSharedMemory_SetGameHwnd(HWND hwnd);

// 设置注入进程 PID
void ControllerSharedMemory_SetInjectedPid(DWORD pid);

// 设置目标坐标
void ControllerSharedMemory_SetTargetPos(int x, int y);

// 启用/禁用 Hook
void ControllerSharedMemory_SetEnabled(bool enabled);
