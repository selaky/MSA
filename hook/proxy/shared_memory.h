/**
 * MSA Proxy DLL - 共享内存管理（控制单元端）
 *
 * 控制单元端负责创建共享内存，Hook DLL 端负责打开
 */

#pragma once

#include "../common/protocol.h"

/**
 * 共享内存管理类（控制单元端）
 *
 * 负责创建和管理共享内存，供 Hook DLL 读取
 */
class SharedMemoryManager
{
public:
    SharedMemoryManager();
    ~SharedMemoryManager();

    // 禁止拷贝
    SharedMemoryManager(const SharedMemoryManager&) = delete;
    SharedMemoryManager& operator=(const SharedMemoryManager&) = delete;

    /**
     * 初始化共享内存
     * @param hwnd 游戏窗口句柄
     * @return 是否成功
     */
    bool init(HWND hwnd);

    /**
     * 清理共享内存
     */
    void cleanup();

    /**
     * 检查共享内存是否有效
     */
    bool is_valid() const;

    /**
     * 设置目标坐标（客户区坐标）
     * @param x X 坐标
     * @param y Y 坐标
     */
    void set_target(int x, int y);

    /**
     * 启用 Hook（GetCursorPos 返回伪造坐标）
     */
    void enable();

    /**
     * 禁用 Hook（GetCursorPos 透传原始 API）
     */
    void disable();

    /**
     * 设置被注入进程的 PID
     * @param pid 进程 ID
     */
    void set_injected_pid(DWORD pid);

    /**
     * 获取被注入进程的 PID
     * @return 进程 ID，未设置返回 0
     */
    DWORD get_injected_pid() const;

private:
    HANDLE map_file_;           // 共享内存句柄
    PMSA_SHARED_DATA data_;     // 共享数据指针
};
