/**
 * MSA Proxy DLL - 导出函数实现
 *
 * 实现 MaaWin32ControlUnit.dll 的导出函数
 */

#include <windows.h>
#include "control_unit.h"

// 获取原版 DLL 句柄（在 dllmain.cpp 中定义）
extern HMODULE GetOriginalDll();

// ========== 原版函数类型定义 ==========

using FnMaaWin32ControlUnitGetVersion = const char* (*)();
using FnMaaWin32ControlUnitCreate = MaaWin32ControlUnitHandle (*)(
    void* hWnd,
    MaaWin32ScreencapMethod screencap_method,
    MaaWin32InputMethod mouse_method,
    MaaWin32InputMethod keyboard_method);
using FnMaaWin32ControlUnitDestroy = void (*)(MaaWin32ControlUnitHandle handle);

// ========== 原版函数指针缓存 ==========

static FnMaaWin32ControlUnitGetVersion g_pfnGetVersion = nullptr;
static FnMaaWin32ControlUnitCreate g_pfnCreate = nullptr;
static FnMaaWin32ControlUnitDestroy g_pfnDestroy = nullptr;

/**
 * 获取原版函数指针
 */
template <typename T>
static T GetOriginalFunction(const char* name, T& cache)
{
    if (cache == nullptr) {
        HMODULE hDll = GetOriginalDll();
        if (hDll != nullptr) {
            cache = reinterpret_cast<T>(GetProcAddress(hDll, name));
        }
    }
    return cache;
}

// ========== 导出函数实现 ==========

extern "C" {

/**
 * 获取版本号
 * 直接透传原版
 */
__declspec(dllexport) const char* MaaWin32ControlUnitGetVersion()
{
    auto fn = GetOriginalFunction("MaaWin32ControlUnitGetVersion", g_pfnGetVersion);
    if (fn != nullptr) {
        return fn();
    }
    return "unknown";
}

/**
 * 创建控制单元
 *
 * 如果 mouse_method 是 SendMessage，返回自定义控制单元
 * 否则透传原版控制单元
 */
__declspec(dllexport) MaaWin32ControlUnitHandle MaaWin32ControlUnitCreate(
    void* hWnd,
    MaaWin32ScreencapMethod screencap_method,
    MaaWin32InputMethod mouse_method,
    MaaWin32InputMethod keyboard_method)
{
    auto fn = GetOriginalFunction("MaaWin32ControlUnitCreate", g_pfnCreate);
    if (fn == nullptr) {
        return nullptr;
    }

    // 调用原版 Create 获取原版控制单元
    MaaWin32ControlUnitHandle original = fn(hWnd, screencap_method, mouse_method, keyboard_method);
    if (original == nullptr) {
        return nullptr;
    }

    // 判断是否需要使用自定义控制单元
    // MaaWin32InputMethod_SendMessage = (1ULL << 1) = 2
    if (mouse_method == MaaWin32InputMethod_SendMessage) {
        // 创建自定义控制单元包装器
        return new MsaControlUnit(original, static_cast<HWND>(hWnd));
    }

    // 其他模式直接返回原版
    return original;
}

/**
 * 销毁控制单元
 */
__declspec(dllexport) void MaaWin32ControlUnitDestroy(MaaWin32ControlUnitHandle handle)
{
    if (handle == nullptr) {
        return;
    }

    // 尝试转换为 MsaControlUnit
    MsaControlUnit* msaUnit = dynamic_cast<MsaControlUnit*>(handle);

    if (msaUnit != nullptr) {
        // 是自定义控制单元，需要先销毁原版控制单元
        auto fn = GetOriginalFunction("MaaWin32ControlUnitDestroy", g_pfnDestroy);
        if (fn != nullptr) {
            // 获取原版控制单元并销毁
            MaaWin32ControlUnitHandle original = msaUnit->get_original();
            if (original != nullptr) {
                fn(original);
            }
        }

        // 删除自定义控制单元
        delete msaUnit;
    }
    else {
        // 是原版控制单元，直接调用原版 Destroy
        auto fn = GetOriginalFunction("MaaWin32ControlUnitDestroy", g_pfnDestroy);
        if (fn != nullptr) {
            fn(handle);
        }
    }
}

} // extern "C"
