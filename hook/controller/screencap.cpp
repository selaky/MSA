/**
 * MSA 自定义控制器 - Windows Graphics Capture 截图实现
 *
 * 使用 Windows.Graphics.Capture API (FramePool) 实现后台截图
 */

#include "screencap.h"

// 先包含 Windows SDK 头文件
#include <d3d11.h>
#include <dxgi1_2.h>

// 然后包含 C++/WinRT 头文件
#include <winrt/Windows.Foundation.h>
#include <winrt/Windows.Foundation.Collections.h>
#include <winrt/Windows.Graphics.Capture.h>
#include <winrt/Windows.Graphics.DirectX.h>
#include <winrt/Windows.Graphics.DirectX.Direct3D11.h>
#include <windows.graphics.capture.interop.h>
#include <windows.graphics.directx.direct3d11.interop.h>

#include <mutex>
#include <atomic>

#pragma comment(lib, "d3d11.lib")
#pragma comment(lib, "dxgi.lib")
#pragma comment(lib, "windowsapp.lib")

// 使用 WinRT 命名空间
namespace wf = winrt::Windows::Foundation;
namespace wgc = winrt::Windows::Graphics::Capture;
namespace wgd = winrt::Windows::Graphics::DirectX;
namespace wgd3d = winrt::Windows::Graphics::DirectX::Direct3D11;

// 截图器上下文
struct ScreencapContext {
    HWND hwnd;

    // Direct3D 设备
    ID3D11Device* d3dDevice = nullptr;
    ID3D11DeviceContext* d3dContext = nullptr;
    wgd3d::IDirect3DDevice winrtDevice{ nullptr };

    // Capture 相关
    wgc::GraphicsCaptureItem captureItem{ nullptr };
    wgc::Direct3D11CaptureFramePool framePool{ nullptr };
    wgc::GraphicsCaptureSession captureSession{ nullptr };

    // 用于读取的 staging texture
    ID3D11Texture2D* stagingTexture = nullptr;
    int stagingWidth = 0;
    int stagingHeight = 0;

    // 最新帧数据
    std::mutex frameMutex;
    std::atomic<bool> hasNewFrame{ false };
    ID3D11Texture2D* latestTexture = nullptr;
    int latestWidth = 0;
    int latestHeight = 0;

    // 帧到达事件 token
    winrt::event_token frameArrivedToken;
};

// 辅助函数：创建 Direct3D 设备
static bool CreateD3DDevice(ScreencapContext* ctx) {
    D3D_FEATURE_LEVEL featureLevels[] = {
        D3D_FEATURE_LEVEL_11_1,
        D3D_FEATURE_LEVEL_11_0,
        D3D_FEATURE_LEVEL_10_1,
        D3D_FEATURE_LEVEL_10_0,
    };

    UINT flags = D3D11_CREATE_DEVICE_BGRA_SUPPORT;
#ifdef _DEBUG
    flags |= D3D11_CREATE_DEVICE_DEBUG;
#endif

    HRESULT hr = D3D11CreateDevice(
        nullptr,
        D3D_DRIVER_TYPE_HARDWARE,
        nullptr,
        flags,
        featureLevels,
        ARRAYSIZE(featureLevels),
        D3D11_SDK_VERSION,
        &ctx->d3dDevice,
        nullptr,
        &ctx->d3dContext
    );

    return SUCCEEDED(hr);
}

// 辅助函数：将 ID3D11Device 转换为 WinRT IDirect3DDevice
static wgd3d::IDirect3DDevice CreateWinRTDevice(ID3D11Device* d3dDevice) {
    // 获取 DXGI 设备
    IDXGIDevice* dxgiDevice = nullptr;
    HRESULT hr = d3dDevice->QueryInterface(__uuidof(IDXGIDevice), reinterpret_cast<void**>(&dxgiDevice));
    if (FAILED(hr) || !dxgiDevice) {
        return nullptr;
    }

    // 创建 WinRT Direct3D 设备
    IInspectable* inspectable = nullptr;
    hr = CreateDirect3D11DeviceFromDXGIDevice(dxgiDevice, &inspectable);
    dxgiDevice->Release();

    if (FAILED(hr) || !inspectable) {
        return nullptr;
    }

    // 转换为 WinRT 类型
    wgd3d::IDirect3DDevice device{ nullptr };
    winrt::copy_from_abi(device, inspectable);
    inspectable->Release();
    return device;
}

// 辅助函数：从窗口句柄创建 GraphicsCaptureItem
static wgc::GraphicsCaptureItem CreateCaptureItemForWindow(HWND hwnd) {
    auto factory = winrt::get_activation_factory<wgc::GraphicsCaptureItem, IGraphicsCaptureItemInterop>();
    wgc::GraphicsCaptureItem item{ nullptr };
    HRESULT hr = factory->CreateForWindow(
        hwnd,
        winrt::guid_of<ABI::Windows::Graphics::Capture::IGraphicsCaptureItem>(),
        reinterpret_cast<void**>(winrt::put_abi(item))
    );
    if (FAILED(hr)) {
        return nullptr;
    }
    return item;
}

// 辅助函数：确保 staging texture 大小正确
static bool EnsureStagingTexture(ScreencapContext* ctx, int width, int height) {
    if (ctx->stagingTexture && ctx->stagingWidth == width && ctx->stagingHeight == height) {
        return true;
    }

    if (ctx->stagingTexture) {
        ctx->stagingTexture->Release();
        ctx->stagingTexture = nullptr;
    }

    D3D11_TEXTURE2D_DESC desc = {};
    desc.Width = width;
    desc.Height = height;
    desc.MipLevels = 1;
    desc.ArraySize = 1;
    desc.Format = DXGI_FORMAT_B8G8R8A8_UNORM;
    desc.SampleDesc.Count = 1;
    desc.Usage = D3D11_USAGE_STAGING;
    desc.CPUAccessFlags = D3D11_CPU_ACCESS_READ;

    HRESULT hr = ctx->d3dDevice->CreateTexture2D(&desc, nullptr, &ctx->stagingTexture);
    if (FAILED(hr)) {
        return false;
    }

    ctx->stagingWidth = width;
    ctx->stagingHeight = height;
    return true;
}

// 帧到达回调
static void OnFrameArrived(ScreencapContext* ctx, wgc::Direct3D11CaptureFramePool const& sender, wf::IInspectable const&) {
    auto frame = sender.TryGetNextFrame();
    if (!frame) {
        return;
    }

    auto surface = frame.Surface();

    // 获取 Direct3D 纹理
    auto interop = surface.as<Windows::Graphics::DirectX::Direct3D11::IDirect3DDxgiInterfaceAccess>();

    ID3D11Texture2D* texture = nullptr;
    HRESULT hr = interop->GetInterface(__uuidof(ID3D11Texture2D), reinterpret_cast<void**>(&texture));
    if (FAILED(hr) || !texture) {
        return;
    }

    D3D11_TEXTURE2D_DESC desc;
    texture->GetDesc(&desc);

    // 保存最新帧
    {
        std::lock_guard<std::mutex> lock(ctx->frameMutex);
        if (ctx->latestTexture) {
            ctx->latestTexture->Release();
        }
        ctx->latestTexture = texture;  // 转移所有权
        ctx->latestWidth = desc.Width;
        ctx->latestHeight = desc.Height;
        ctx->hasNewFrame = true;
    }
}

bool Screencap_IsSupported() {
    // 检查 Windows 版本是否支持 Windows Graphics Capture
    // 需要 Windows 10 1903 (10.0.18362) 或更高版本
    return wgc::GraphicsCaptureSession::IsSupported();
}

ScreencapContext* Screencap_Create(HWND hwnd) {
    if (!IsWindow(hwnd)) {
        return nullptr;
    }

    if (!Screencap_IsSupported()) {
        return nullptr;
    }

    auto ctx = new ScreencapContext();
    ctx->hwnd = hwnd;

    // 初始化 WinRT
    winrt::init_apartment(winrt::apartment_type::multi_threaded);

    // 创建 D3D 设备
    if (!CreateD3DDevice(ctx)) {
        delete ctx;
        return nullptr;
    }

    // 创建 WinRT 设备
    ctx->winrtDevice = CreateWinRTDevice(ctx->d3dDevice);
    if (!ctx->winrtDevice) {
        ctx->d3dDevice->Release();
        ctx->d3dContext->Release();
        delete ctx;
        return nullptr;
    }

    // 创建 Capture Item
    ctx->captureItem = CreateCaptureItemForWindow(hwnd);
    if (!ctx->captureItem) {
        ctx->d3dDevice->Release();
        ctx->d3dContext->Release();
        delete ctx;
        return nullptr;
    }

    // 获取窗口大小
    auto size = ctx->captureItem.Size();

    // 创建 Frame Pool
    ctx->framePool = wgc::Direct3D11CaptureFramePool::CreateFreeThreaded(
        ctx->winrtDevice,
        wgd::DirectXPixelFormat::B8G8R8A8UIntNormalized,
        1,  // 只需要 1 帧缓冲
        size
    );

    if (!ctx->framePool) {
        ctx->d3dDevice->Release();
        ctx->d3dContext->Release();
        delete ctx;
        return nullptr;
    }

    // 注册帧到达回调
    ctx->frameArrivedToken = ctx->framePool.FrameArrived(
        [ctx](wgc::Direct3D11CaptureFramePool const& sender, wf::IInspectable const& args) {
            OnFrameArrived(ctx, sender, args);
        }
    );

    // 创建 Capture Session
    ctx->captureSession = ctx->framePool.CreateCaptureSession(ctx->captureItem);
    if (!ctx->captureSession) {
        ctx->framePool.FrameArrived(ctx->frameArrivedToken);
        ctx->framePool.Close();
        ctx->d3dDevice->Release();
        ctx->d3dContext->Release();
        delete ctx;
        return nullptr;
    }

    // 设置不显示黄色边框（Windows 11 支持）
    try {
        ctx->captureSession.IsBorderRequired(false);
    } catch (...) {
        // Windows 10 不支持此属性，忽略
    }

    // 设置不显示鼠标光标
    try {
        ctx->captureSession.IsCursorCaptureEnabled(false);
    } catch (...) {
        // 旧版本可能不支持，忽略
    }

    // 开始捕获
    ctx->captureSession.StartCapture();

    return ctx;
}

void Screencap_Destroy(ScreencapContext* ctx) {
    if (!ctx) {
        return;
    }

    // 停止捕获
    if (ctx->captureSession) {
        ctx->captureSession.Close();
        ctx->captureSession = nullptr;
    }

    // 移除回调并关闭 frame pool
    if (ctx->framePool) {
        ctx->framePool.FrameArrived(ctx->frameArrivedToken);
        ctx->framePool.Close();
        ctx->framePool = nullptr;
    }

    ctx->captureItem = nullptr;
    ctx->winrtDevice = nullptr;

    if (ctx->stagingTexture) {
        ctx->stagingTexture->Release();
        ctx->stagingTexture = nullptr;
    }

    if (ctx->latestTexture) {
        ctx->latestTexture->Release();
        ctx->latestTexture = nullptr;
    }

    if (ctx->d3dContext) {
        ctx->d3dContext->Release();
        ctx->d3dContext = nullptr;
    }

    if (ctx->d3dDevice) {
        ctx->d3dDevice->Release();
        ctx->d3dDevice = nullptr;
    }

    delete ctx;
}

bool Screencap_Capture(ScreencapContext* ctx, uint8_t** out_data, int* out_width, int* out_height) {
    if (!ctx || !out_data || !out_width || !out_height) {
        return false;
    }

    *out_data = nullptr;
    *out_width = 0;
    *out_height = 0;

    // 检查窗口是否仍然有效
    if (!IsWindow(ctx->hwnd)) {
        return false;
    }

    // 检查窗口大小是否变化，如果变化则重新创建 frame pool
    auto currentSize = ctx->captureItem.Size();
    if (currentSize.Width <= 0 || currentSize.Height <= 0) {
        return false;
    }

    // 等待新帧（最多等待 100ms）
    for (int i = 0; i < 10 && !ctx->hasNewFrame; ++i) {
        Sleep(10);
    }

    // 获取最新帧
    ID3D11Texture2D* texture = nullptr;
    int width, height;
    {
        std::lock_guard<std::mutex> lock(ctx->frameMutex);
        if (!ctx->latestTexture) {
            return false;
        }
        texture = ctx->latestTexture;
        texture->AddRef();  // 增加引用计数
        width = ctx->latestWidth;
        height = ctx->latestHeight;
        ctx->hasNewFrame = false;
    }

    // 确保 staging texture 大小正确
    if (!EnsureStagingTexture(ctx, width, height)) {
        texture->Release();
        return false;
    }

    // 复制到 staging texture
    ctx->d3dContext->CopyResource(ctx->stagingTexture, texture);
    texture->Release();

    // 映射 staging texture 以读取数据
    D3D11_MAPPED_SUBRESOURCE mapped;
    HRESULT hr = ctx->d3dContext->Map(ctx->stagingTexture, 0, D3D11_MAP_READ, 0, &mapped);
    if (FAILED(hr)) {
        return false;
    }

    // 分配输出缓冲区
    size_t dataSize = (size_t)width * height * 4;
    uint8_t* data = (uint8_t*)malloc(dataSize);
    if (!data) {
        ctx->d3dContext->Unmap(ctx->stagingTexture, 0);
        return false;
    }

    // 复制数据（处理行对齐）
    uint8_t* dst = data;
    uint8_t* src = (uint8_t*)mapped.pData;
    size_t rowSize = (size_t)width * 4;
    for (int y = 0; y < height; ++y) {
        memcpy(dst, src, rowSize);
        dst += rowSize;
        src += mapped.RowPitch;
    }

    ctx->d3dContext->Unmap(ctx->stagingTexture, 0);

    *out_data = data;
    *out_width = width;
    *out_height = height;
    return true;
}

void Screencap_FreeData(uint8_t* data) {
    if (data) {
        free(data);
    }
}
