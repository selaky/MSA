/**
 * MSA Proxy DLL - 自定义控制单元实现
 *
 * 截图委托原版，输入使用自定义实现（阶段四完成）
 */

#include "control_unit.h"

// OpenCV Mat 头文件
// 注意：需要配置 OpenCV 头文件路径
#ifdef _MSC_VER
#pragma warning(push)
#pragma warning(disable : 4819) // 忽略代码页警告
#endif

#include <opencv2/core/mat.hpp>

#ifdef _MSC_VER
#pragma warning(pop)
#endif

// ========== 构造与析构 ==========

MsaControlUnit::MsaControlUnit(MAA_CTRL_UNIT_NS::Win32ControlUnitAPI* original, HWND hwnd)
    : original_(original)
    , hwnd_(hwnd)
    , injected_(false)
{
}

MsaControlUnit::~MsaControlUnit()
{
    // 注意：不要在这里删除 original_，由 Destroy 函数负责
}

// ========== 委托给原版的方法 ==========

bool MsaControlUnit::connect()
{
    // 委托原版
    bool result = original_->connect();

    // TODO: 阶段四 - 在这里初始化注入

    return result;
}

bool MsaControlUnit::request_uuid(std::string& uuid)
{
    return original_->request_uuid(uuid);
}

MaaControllerFeature MsaControlUnit::get_features() const
{
    return original_->get_features();
}

bool MsaControlUnit::start_app(const std::string& intent)
{
    return original_->start_app(intent);
}

bool MsaControlUnit::stop_app(const std::string& intent)
{
    return original_->stop_app(intent);
}

bool MsaControlUnit::screencap(cv::Mat& image)
{
    return original_->screencap(image);
}

bool MsaControlUnit::click_key(int key)
{
    return original_->click_key(key);
}

bool MsaControlUnit::input_text(const std::string& text)
{
    return original_->input_text(text);
}

bool MsaControlUnit::key_down(int key)
{
    return original_->key_down(key);
}

bool MsaControlUnit::key_up(int key)
{
    return original_->key_up(key);
}

bool MsaControlUnit::scroll(int dx, int dy)
{
    return original_->scroll(dx, dy);
}

// ========== 自定义实现的方法（阶段四实现） ==========
// 当前阶段：委托给原版，阶段四替换为自定义实现

bool MsaControlUnit::click(int x, int y)
{
    // TODO: 阶段四 - 替换为自定义后台点击实现
    return original_->click(x, y);
}

bool MsaControlUnit::swipe(int x1, int y1, int x2, int y2, int duration)
{
    // TODO: 阶段四 - 替换为自定义后台滑动实现
    return original_->swipe(x1, y1, x2, y2, duration);
}

bool MsaControlUnit::touch_down(int contact, int x, int y, int pressure)
{
    // TODO: 阶段四 - 替换为自定义实现
    return original_->touch_down(contact, x, y, pressure);
}

bool MsaControlUnit::touch_move(int contact, int x, int y, int pressure)
{
    // TODO: 阶段四 - 替换为自定义实现
    return original_->touch_move(contact, x, y, pressure);
}

bool MsaControlUnit::touch_up(int contact)
{
    // TODO: 阶段四 - 替换为自定义实现
    return original_->touch_up(contact);
}
