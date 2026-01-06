/**
 * MSA 后台点击测试程序
 *
 * 功能：
 * 1. 创建共享内存
 * 2. 注入 Hook DLL 到游戏进程
 * 3. 发送后台点击消息
 *
 * 使用方法：
 * - 双击运行，按提示操作
 * - 支持点击指定坐标或窗口中心
 */

#include <windows.h>
#include <tlhelp32.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "../common/protocol.h"

// 游戏进程名
#define GAME_PROCESS_NAME L"StarEra.exe"
// 游戏窗口类名
#define GAME_WINDOW_CLASS L"UnityWndClass"

// 全局变量
static HANDLE g_hMapFile = NULL;
static PMSA_SHARED_DATA g_pSharedData = NULL;
static HWND g_hGameWindow = NULL;
static DWORD g_dwGamePid = 0;
static HANDLE g_hGameProcess = NULL;

// 日志输出
void Log(const char* format, ...) {
    va_list args;
    va_start(args, format);
    printf("[MSA Test] ");
    vprintf(format, args);
    printf("\n");
    va_end(args);
}

// 错误输出
void LogError(const char* format, ...) {
    va_list args;
    va_start(args, format);
    printf("[MSA Error] ");
    vprintf(format, args);
    printf(" (错误码: %lu)\n", GetLastError());
    va_end(args);
}

// 查找游戏进程
DWORD FindGameProcess() {
    HANDLE hSnapshot = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
    if (hSnapshot == INVALID_HANDLE_VALUE) {
        LogError("创建进程快照失败");
        return 0;
    }

    PROCESSENTRY32W pe32;
    pe32.dwSize = sizeof(pe32);

    DWORD pid = 0;
    if (Process32FirstW(hSnapshot, &pe32)) {
        do {
            if (_wcsicmp(pe32.szExeFile, GAME_PROCESS_NAME) == 0) {
                pid = pe32.th32ProcessID;
                break;
            }
        } while (Process32NextW(hSnapshot, &pe32));
    }

    CloseHandle(hSnapshot);
    return pid;
}

// 查找游戏窗口的回调函数
struct FindWindowData {
    DWORD pid;
    HWND hwnd;
};

BOOL CALLBACK EnumWindowsProc(HWND hwnd, LPARAM lParam) {
    struct FindWindowData* data = (struct FindWindowData*)lParam;

    DWORD windowPid;
    GetWindowThreadProcessId(hwnd, &windowPid);

    if (windowPid == data->pid) {
        wchar_t className[256];
        if (GetClassNameW(hwnd, className, 256)) {
            if (wcscmp(className, GAME_WINDOW_CLASS) == 0) {
                data->hwnd = hwnd;
                return FALSE;  // 停止枚举
            }
        }
    }

    return TRUE;  // 继续枚举
}

// 查找游戏窗口
HWND FindGameWindow(DWORD pid) {
    struct FindWindowData data = { pid, NULL };
    EnumWindows(EnumWindowsProc, (LPARAM)&data);
    return data.hwnd;
}

// 创建共享内存
bool CreateSharedMemory() {
    g_hMapFile = CreateFileMappingW(
        INVALID_HANDLE_VALUE,
        NULL,
        PAGE_READWRITE,
        0,
        MSA_SHARED_MEMORY_SIZE,
        MSA_SHARED_MEMORY_NAME
    );

    if (g_hMapFile == NULL) {
        LogError("创建共享内存失败");
        return false;
    }

    g_pSharedData = (PMSA_SHARED_DATA)MapViewOfFile(
        g_hMapFile,
        FILE_MAP_ALL_ACCESS,
        0,
        0,
        MSA_SHARED_MEMORY_SIZE
    );

    if (g_pSharedData == NULL) {
        LogError("映射共享内存失败");
        CloseHandle(g_hMapFile);
        g_hMapFile = NULL;
        return false;
    }

    // 初始化共享数据
    memset(g_pSharedData, 0, MSA_SHARED_MEMORY_SIZE);
    g_pSharedData->version = MSA_PROTOCOL_VERSION;
    g_pSharedData->enabled = FALSE;
    g_pSharedData->game_hwnd = g_hGameWindow;
    g_pSharedData->injected_pid = g_dwGamePid;

    Log("共享内存创建成功");
    return true;
}

// 清理共享内存
void CleanupSharedMemory() {
    if (g_pSharedData != NULL) {
        UnmapViewOfFile(g_pSharedData);
        g_pSharedData = NULL;
    }
    if (g_hMapFile != NULL) {
        CloseHandle(g_hMapFile);
        g_hMapFile = NULL;
    }
}

// 检查 DLL 是否已注入
bool IsDllInjected(DWORD pid, const wchar_t* dllName) {
    HANDLE hSnapshot = CreateToolhelp32Snapshot(TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32, pid);
    if (hSnapshot == INVALID_HANDLE_VALUE) {
        return false;
    }

    MODULEENTRY32W me32;
    me32.dwSize = sizeof(me32);

    bool found = false;
    if (Module32FirstW(hSnapshot, &me32)) {
        do {
            if (_wcsicmp(me32.szModule, dllName) == 0) {
                found = true;
                break;
            }
        } while (Module32NextW(hSnapshot, &me32));
    }

    CloseHandle(hSnapshot);
    return found;
}

// 注入 DLL
bool InjectDll(const wchar_t* dllPath) {
    // 提取 DLL 文件名
    const wchar_t* dllName = wcsrchr(dllPath, L'\\');
    if (dllName != NULL) {
        dllName++;  // 跳过反斜杠
    } else {
        dllName = dllPath;
    }

    // 检查是否已经注入
    if (IsDllInjected(g_dwGamePid, dllName)) {
        Log("DLL 已经注入，跳过注入步骤");
        // 仍然需要打开进程句柄
        g_hGameProcess = OpenProcess(
            PROCESS_QUERY_INFORMATION | PROCESS_VM_READ,
            FALSE,
            g_dwGamePid
        );
        return true;
    }

    // 检查 DLL 文件是否存在
    if (GetFileAttributesW(dllPath) == INVALID_FILE_ATTRIBUTES) {
        LogError("DLL 文件不存在");
        return false;
    }

    // 打开目标进程
    g_hGameProcess = OpenProcess(
        PROCESS_CREATE_THREAD | PROCESS_QUERY_INFORMATION |
        PROCESS_VM_OPERATION | PROCESS_VM_WRITE | PROCESS_VM_READ,
        FALSE,
        g_dwGamePid
    );

    if (g_hGameProcess == NULL) {
        LogError("打开游戏进程失败，请以管理员身份运行");
        return false;
    }

    // 在目标进程中分配内存
    size_t pathSize = (wcslen(dllPath) + 1) * sizeof(wchar_t);
    LPVOID pRemotePath = VirtualAllocEx(
        g_hGameProcess,
        NULL,
        pathSize,
        MEM_COMMIT | MEM_RESERVE,
        PAGE_READWRITE
    );

    if (pRemotePath == NULL) {
        LogError("在目标进程中分配内存失败");
        CloseHandle(g_hGameProcess);
        g_hGameProcess = NULL;
        return false;
    }

    // 写入 DLL 路径
    if (!WriteProcessMemory(g_hGameProcess, pRemotePath, dllPath, pathSize, NULL)) {
        LogError("写入 DLL 路径失败");
        VirtualFreeEx(g_hGameProcess, pRemotePath, 0, MEM_RELEASE);
        CloseHandle(g_hGameProcess);
        g_hGameProcess = NULL;
        return false;
    }

    // 获取 LoadLibraryW 地址
    HMODULE hKernel32 = GetModuleHandleW(L"kernel32.dll");
    LPTHREAD_START_ROUTINE pLoadLibraryW = (LPTHREAD_START_ROUTINE)GetProcAddress(hKernel32, "LoadLibraryW");

    if (pLoadLibraryW == NULL) {
        LogError("获取 LoadLibraryW 地址失败");
        VirtualFreeEx(g_hGameProcess, pRemotePath, 0, MEM_RELEASE);
        CloseHandle(g_hGameProcess);
        g_hGameProcess = NULL;
        return false;
    }

    // 创建远程线程执行 LoadLibraryW
    HANDLE hThread = CreateRemoteThread(
        g_hGameProcess,
        NULL,
        0,
        pLoadLibraryW,
        pRemotePath,
        0,
        NULL
    );

    if (hThread == NULL) {
        LogError("创建远程线程失败");
        VirtualFreeEx(g_hGameProcess, pRemotePath, 0, MEM_RELEASE);
        CloseHandle(g_hGameProcess);
        g_hGameProcess = NULL;
        return false;
    }

    // 等待线程完成
    WaitForSingleObject(hThread, 5000);

    // 获取线程退出码（LoadLibraryW 的返回值）
    DWORD exitCode = 0;
    GetExitCodeThread(hThread, &exitCode);

    CloseHandle(hThread);
    VirtualFreeEx(g_hGameProcess, pRemotePath, 0, MEM_RELEASE);

    if (exitCode == 0) {
        LogError("LoadLibraryW 返回 NULL，DLL 加载失败");
        CloseHandle(g_hGameProcess);
        g_hGameProcess = NULL;
        return false;
    }

    Log("DLL 注入成功，模块句柄: 0x%08X", exitCode);
    return true;
}

// 发送后台点击
void SendBackgroundClick(int x, int y) {
    if (g_pSharedData == NULL || g_hGameWindow == NULL) {
        LogError("未初始化");
        return;
    }

    Log("准备点击坐标: (%d, %d)", x, y);

    // 1. 写入坐标到共享内存
    g_pSharedData->target_x = x;
    g_pSharedData->target_y = y;

    // 2. 启用 Hook
    g_pSharedData->enabled = TRUE;
    Log("Hook 已启用");

    // 3. 发送 WM_ACTIVATE 伪造激活状态
    SendMessageW(g_hGameWindow, WM_ACTIVATE, WA_ACTIVE, 0);
    Log("已发送 WM_ACTIVATE");

    // 4. 计算 lParam（坐标打包）
    LPARAM lParam = MAKELPARAM(x, y);

    // 5. 发送鼠标按下消息
    SendMessageW(g_hGameWindow, WM_LBUTTONDOWN, MK_LBUTTON, lParam);
    Log("已发送 WM_LBUTTONDOWN");

    // 6. 短暂延迟
    Sleep(50);

    // 7. 发送鼠标抬起消息
    SendMessageW(g_hGameWindow, WM_LBUTTONUP, 0, lParam);
    Log("已发送 WM_LBUTTONUP");

    // 8. 禁用 Hook
    g_pSharedData->enabled = FALSE;
    Log("Hook 已禁用");

    Log("点击完成");
}

// 获取窗口客户区大小
void GetClientSize(int* width, int* height) {
    RECT rect;
    if (GetClientRect(g_hGameWindow, &rect)) {
        *width = rect.right - rect.left;
        *height = rect.bottom - rect.top;
    } else {
        *width = 0;
        *height = 0;
    }
}

// 获取 DLL 路径
void GetDllPath(wchar_t* buffer, size_t bufferSize) {
    // 获取当前可执行文件路径
    GetModuleFileNameW(NULL, buffer, (DWORD)bufferSize);

    // 找到最后一个反斜杠
    wchar_t* lastSlash = wcsrchr(buffer, L'\\');
    if (lastSlash != NULL) {
        *(lastSlash + 1) = L'\0';
    }

    // 拼接 DLL 文件名
    wcscat_s(buffer, bufferSize, L"msa_hook.dll");
}

// 主函数
int main() {
    // 设置控制台编码为 UTF-8
    SetConsoleOutputCP(65001);

    printf("========================================\n");
    printf("    MSA 后台点击测试程序\n");
    printf("========================================\n\n");

    // 1. 查找游戏进程
    Log("正在查找游戏进程...");
    g_dwGamePid = FindGameProcess();
    if (g_dwGamePid == 0) {
        LogError("未找到游戏进程，请先启动游戏");
        printf("\n按任意键退出...");
        getchar();
        return 1;
    }
    Log("找到游戏进程，PID: %lu", g_dwGamePid);

    // 2. 查找游戏窗口
    Log("正在查找游戏窗口...");
    g_hGameWindow = FindGameWindow(g_dwGamePid);
    if (g_hGameWindow == NULL) {
        LogError("未找到游戏窗口");
        printf("\n按任意键退出...");
        getchar();
        return 1;
    }
    Log("找到游戏窗口，句柄: 0x%p", g_hGameWindow);

    // 获取窗口大小
    int clientWidth, clientHeight;
    GetClientSize(&clientWidth, &clientHeight);
    Log("窗口客户区大小: %d x %d", clientWidth, clientHeight);

    // 3. 创建共享内存
    Log("正在创建共享内存...");
    if (!CreateSharedMemory()) {
        printf("\n按任意键退出...");
        getchar();
        return 1;
    }

    // 4. 注入 DLL
    Log("正在注入 Hook DLL...");
    wchar_t dllPath[MAX_PATH];
    GetDllPath(dllPath, MAX_PATH);
    wprintf(L"DLL 路径: %s\n", dllPath);

    if (!InjectDll(dllPath)) {
        CleanupSharedMemory();
        printf("\n按任意键退出...");
        getchar();
        return 1;
    }

    // 等待 DLL 初始化
    Sleep(500);

    // 5. 交互式测试
    printf("\n========================================\n");
    printf("    测试菜单\n");
    printf("========================================\n");
    printf("1. 点击窗口中心\n");
    printf("2. 点击指定坐标\n");
    printf("3. 退出\n");
    printf("========================================\n");

    while (1) {
        printf("\n请选择操作 (1-3): ");
        int choice;
        if (scanf("%d", &choice) != 1) {
            // 清除输入缓冲区
            while (getchar() != '\n');
            continue;
        }

        switch (choice) {
        case 1: {
            // 点击窗口中心
            int centerX = clientWidth / 2;
            int centerY = clientHeight / 2;
            Log("点击窗口中心: (%d, %d)", centerX, centerY);
            SendBackgroundClick(centerX, centerY);
            break;
        }
        case 2: {
            // 点击指定坐标
            int x, y;
            printf("请输入 X 坐标: ");
            scanf("%d", &x);
            printf("请输入 Y 坐标: ");
            scanf("%d", &y);
            SendBackgroundClick(x, y);
            break;
        }
        case 3:
            // 退出
            goto cleanup;
        default:
            printf("无效选择，请重试\n");
            break;
        }
    }

cleanup:
    // 清理
    Log("正在清理...");
    CleanupSharedMemory();
    if (g_hGameProcess != NULL) {
        CloseHandle(g_hGameProcess);
    }

    Log("测试程序结束");
    printf("\n按任意键退出...");
    getchar();
    getchar();  // 消耗之前的换行符

    return 0;
}
