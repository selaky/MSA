/**
 * MSA Hook DLL - Hook 函数声明
 */

#pragma once

#include <windows.h>

// 初始化所有 Hook
bool Hooks_Init();

// 清理所有 Hook
void Hooks_Cleanup();
