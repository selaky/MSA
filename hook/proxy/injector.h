/**
 * MSA Proxy DLL - DLL 注入器
 *
 * 使用 CreateRemoteThread + LoadLibraryW 注入 Hook DLL 到游戏进程
 */

#pragma once

#include <windows.h>
#include <string>

/**
 * DLL 注入器类
 *
 * 负责将 Hook DLL 注入到目标进程
 */
class Injector
{
public:
    Injector();
    ~Injector();

    // 禁止拷贝
    Injector(const Injector&) = delete;
    Injector& operator=(const Injector&) = delete;

    /**
     * 注入 DLL 到目标进程
     * @param hwnd 目标窗口句柄
     * @param dll_path Hook DLL 的完整路径
     * @return 是否成功
     */
    bool inject(HWND hwnd, const std::wstring& dll_path);

    /**
     * 检查注入是否仍然有效（目标进程是否存活）
     * @return 是否有效
     */
    bool is_valid() const;

    /**
     * 获取被注入进程的 PID
     * @return 进程 ID，未注入返回 0
     */
    DWORD get_injected_pid() const;

    /**
     * 获取最后的错误信息
     * @return 错误信息
     */
    const std::wstring& get_last_error() const;

private:
    /**
     * 获取窗口所属进程的 PID
     * @param hwnd 窗口句柄
     * @return 进程 ID，失败返回 0
     */
    DWORD get_process_id_from_hwnd(HWND hwnd);

    /**
     * 检查进程是否存活
     * @param pid 进程 ID
     * @return 是否存活
     */
    bool is_process_alive(DWORD pid) const;

    DWORD injected_pid_;        // 被注入进程的 PID
    std::wstring last_error_;   // 最后的错误信息
};
