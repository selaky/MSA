/**
 * MSA 自定义控制器 - MaaCustomControllerCallbacks 实现
 *
 * 实现 MAA Framework 的自定义控制器接口，支持后台截图和点击
 */

#pragma once

#include <windows.h>
#include "MaaFramework/MaaAPI.h"

#ifdef __cplusplus
extern "C" {
#endif

// 控制器上下文
typedef struct MsaControllerContext MsaControllerContext;

// 创建控制器上下文
// hwnd: 游戏窗口句柄（可选，如果为 NULL 则在 connect 时自动查找）
MsaControllerContext* MsaController_Create(HWND hwnd);

// 销毁控制器上下文
void MsaController_Destroy(MsaControllerContext* ctx);

// 获取 MaaCustomControllerCallbacks 结构
// 返回的指针在 ctx 销毁前有效
MaaCustomControllerCallbacks* MsaController_GetCallbacks(MsaControllerContext* ctx);

// 获取控制器上下文指针（用于传递给 MaaCustomControllerCreate）
void* MsaController_GetTransArg(MsaControllerContext* ctx);

// 便捷函数：创建 MAA 控制器
// hwnd: 游戏窗口句柄（可选）
// 返回: MaaController 句柄，失败返回 NULL
// 注意：调用者需要在不再使用时调用 MaaControllerDestroy
MaaController* MsaController_CreateMaaController(HWND hwnd);

#ifdef __cplusplus
}
#endif
