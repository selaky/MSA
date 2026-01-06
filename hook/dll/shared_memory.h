/**
 * MSA Hook DLL - 共享内存访问（DLL 端）
 */

#pragma once

#include "../common/protocol.h"

// 初始化共享内存（打开已存在的共享内存）
bool SharedMemory_Init();

// 清理共享内存
void SharedMemory_Cleanup();

// 获取共享数据指针
PMSA_SHARED_DATA SharedMemory_GetData();

// 检查共享内存是否有效
bool SharedMemory_IsValid();
