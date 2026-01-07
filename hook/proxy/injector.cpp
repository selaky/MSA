/**
 * MSA Proxy DLL - DLL 注入器实现
 */

#include "injector.h"
#include <tlhelp32.h>

Injector::Injector()
    : injected_pid_(0)
{
}

Injector::~Injector()
{
    // 注入后不需要特别清理，DLL 会在目标进程退出时自动卸载
}

bool Injector::inject(HWND hwnd, const std::wstring& dll_path)
{
    last_error_.clear();

    // 获取目标进程 PID
    DWORD pid = get_process_id_from_hwnd(hwnd);
    if (pid == 0) {
        last_error_ = L"无法获取目标进程 PID";
        return false;
    }

    // 如果已经注入到同一进程，检查是否仍然有效
    if (injected_pid_ == pid && is_process_alive(pid)) {
        return true;  // 已经注入，无需重复
    }

    // 打开目标进程
    HANDLE hProcess = OpenProcess(
        PROCESS_CREATE_THREAD | PROCESS_QUERY_INFORMATION |
        PROCESS_VM_OPERATION | PROCESS_VM_WRITE | PROCESS_VM_READ,
        FALSE,
        pid
    );

    if (hProcess == NULL) {
        last_error_ = L"无法打开目标进程，错误码: " + std::to_wstring(GetLastError());
        return false;
    }

    // 计算 DLL 路径所需的内存大小（包含 null 终止符）
    SIZE_T dll_path_size = (dll_path.length() + 1) * sizeof(wchar_t);

    // 在目标进程中分配内存
    LPVOID remote_memory = VirtualAllocEx(
        hProcess,
        NULL,
        dll_path_size,
        MEM_COMMIT | MEM_RESERVE,
        PAGE_READWRITE
    );

    if (remote_memory == NULL) {
        last_error_ = L"无法在目标进程中分配内存，错误码: " + std::to_wstring(GetLastError());
        CloseHandle(hProcess);
        return false;
    }

    // 写入 DLL 路径到目标进程
    SIZE_T bytes_written = 0;
    BOOL write_result = WriteProcessMemory(
        hProcess,
        remote_memory,
        dll_path.c_str(),
        dll_path_size,
        &bytes_written
    );

    if (!write_result || bytes_written != dll_path_size) {
        last_error_ = L"无法写入 DLL 路径到目标进程，错误码: " + std::to_wstring(GetLastError());
        VirtualFreeEx(hProcess, remote_memory, 0, MEM_RELEASE);
        CloseHandle(hProcess);
        return false;
    }

    // 获取 LoadLibraryW 函数地址
    HMODULE hKernel32 = GetModuleHandleW(L"kernel32.dll");
    if (hKernel32 == NULL) {
        last_error_ = L"无法获取 kernel32.dll 句柄";
        VirtualFreeEx(hProcess, remote_memory, 0, MEM_RELEASE);
        CloseHandle(hProcess);
        return false;
    }

    LPTHREAD_START_ROUTINE load_library_addr =
        (LPTHREAD_START_ROUTINE)GetProcAddress(hKernel32, "LoadLibraryW");

    if (load_library_addr == NULL) {
        last_error_ = L"无法获取 LoadLibraryW 地址";
        VirtualFreeEx(hProcess, remote_memory, 0, MEM_RELEASE);
        CloseHandle(hProcess);
        return false;
    }

    // 创建远程线程执行 LoadLibraryW
    HANDLE hThread = CreateRemoteThread(
        hProcess,
        NULL,
        0,
        load_library_addr,
        remote_memory,
        0,
        NULL
    );

    if (hThread == NULL) {
        last_error_ = L"无法创建远程线程，错误码: " + std::to_wstring(GetLastError());
        VirtualFreeEx(hProcess, remote_memory, 0, MEM_RELEASE);
        CloseHandle(hProcess);
        return false;
    }

    // 等待远程线程完成（最多等待 5 秒）
    DWORD wait_result = WaitForSingleObject(hThread, 5000);

    if (wait_result == WAIT_TIMEOUT) {
        last_error_ = L"远程线程执行超时";
        CloseHandle(hThread);
        VirtualFreeEx(hProcess, remote_memory, 0, MEM_RELEASE);
        CloseHandle(hProcess);
        return false;
    }

    // 获取线程退出码（LoadLibraryW 的返回值）
    DWORD exit_code = 0;
    GetExitCodeThread(hThread, &exit_code);

    // 清理资源
    CloseHandle(hThread);
    VirtualFreeEx(hProcess, remote_memory, 0, MEM_RELEASE);
    CloseHandle(hProcess);

    // 检查 LoadLibraryW 是否成功
    if (exit_code == 0) {
        last_error_ = L"LoadLibraryW 执行失败，DLL 可能不存在或无法加载";
        return false;
    }

    // 注入成功
    injected_pid_ = pid;
    return true;
}

bool Injector::is_valid() const
{
    if (injected_pid_ == 0) {
        return false;
    }
    return is_process_alive(injected_pid_);
}

DWORD Injector::get_injected_pid() const
{
    return injected_pid_;
}

const std::wstring& Injector::get_last_error() const
{
    return last_error_;
}

DWORD Injector::get_process_id_from_hwnd(HWND hwnd)
{
    DWORD pid = 0;
    GetWindowThreadProcessId(hwnd, &pid);
    return pid;
}

bool Injector::is_process_alive(DWORD pid) const
{
    HANDLE hProcess = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, FALSE, pid);
    if (hProcess == NULL) {
        return false;
    }

    DWORD exit_code = 0;
    BOOL result = GetExitCodeProcess(hProcess, &exit_code);
    CloseHandle(hProcess);

    // 如果进程仍在运行，exit_code 为 STILL_ACTIVE
    return result && exit_code == STILL_ACTIVE;
}
