/**
 * MSA Proxy DLL - 共享内存管理实现（控制单元端）
 */

#include "shared_memory.h"

SharedMemoryManager::SharedMemoryManager()
    : map_file_(NULL)
    , data_(NULL)
{
}

SharedMemoryManager::~SharedMemoryManager()
{
    cleanup();
}

bool SharedMemoryManager::init(HWND hwnd)
{
    // 如果已经初始化，先清理
    if (data_ != NULL) {
        cleanup();
    }

    // 创建共享内存
    map_file_ = CreateFileMappingW(
        INVALID_HANDLE_VALUE,       // 使用系统分页文件
        NULL,                       // 默认安全属性
        PAGE_READWRITE,             // 读写权限
        0,                          // 高位大小
        MSA_SHARED_MEMORY_SIZE,     // 低位大小
        MSA_SHARED_MEMORY_NAME      // 共享内存名称
    );

    if (map_file_ == NULL) {
        return false;
    }

    // 映射共享内存
    data_ = (PMSA_SHARED_DATA)MapViewOfFile(
        map_file_,
        FILE_MAP_ALL_ACCESS,
        0,
        0,
        MSA_SHARED_MEMORY_SIZE
    );

    if (data_ == NULL) {
        CloseHandle(map_file_);
        map_file_ = NULL;
        return false;
    }

    // 初始化共享数据
    ZeroMemory(data_, MSA_SHARED_MEMORY_SIZE);
    data_->version = MSA_PROTOCOL_VERSION;
    data_->enabled = FALSE;
    data_->target_x = 0;
    data_->target_y = 0;
    data_->game_hwnd = hwnd;
    data_->injected_pid = 0;

    return true;
}

void SharedMemoryManager::cleanup()
{
    if (data_ != NULL) {
        UnmapViewOfFile(data_);
        data_ = NULL;
    }

    if (map_file_ != NULL) {
        CloseHandle(map_file_);
        map_file_ = NULL;
    }
}

bool SharedMemoryManager::is_valid() const
{
    return data_ != NULL;
}

void SharedMemoryManager::set_target(int x, int y)
{
    if (data_ != NULL) {
        data_->target_x = x;
        data_->target_y = y;
    }
}

void SharedMemoryManager::enable()
{
    if (data_ != NULL) {
        data_->enabled = TRUE;
    }
}

void SharedMemoryManager::disable()
{
    if (data_ != NULL) {
        data_->enabled = FALSE;
    }
}

void SharedMemoryManager::set_injected_pid(DWORD pid)
{
    if (data_ != NULL) {
        data_->injected_pid = pid;
    }
}

DWORD SharedMemoryManager::get_injected_pid() const
{
    if (data_ != NULL) {
        return data_->injected_pid;
    }
    return 0;
}
