/**
 * MSA 自定义控制器 - Windows Graphics Capture 截图实现
 *
 * 使用 Windows.Graphics.Capture API 实现后台截图
 * 需要 Windows 10 1903 (10.0.18362) 或更高版本
 */

#pragma once

#include <windows.h>
#include <stdint.h>

// 截图器上下文（前向声明）
struct ScreencapContext;

// 创建截图器
// hwnd: 目标窗口句柄
// 返回: 截图器上下文，失败返回 NULL
ScreencapContext* Screencap_Create(HWND hwnd);

// 销毁截图器
void Screencap_Destroy(ScreencapContext* ctx);

// 执行截图
// ctx: 截图器上下文
// out_data: 输出图像数据（BGRA 格式）
// out_width: 输出图像宽度
// out_height: 输出图像高度
// 返回: 成功返回 true
bool Screencap_Capture(ScreencapContext* ctx, uint8_t** out_data, int* out_width, int* out_height);

// 释放截图数据
void Screencap_FreeData(uint8_t* data);

// 检查系统是否支持 Windows Graphics Capture
bool Screencap_IsSupported();
