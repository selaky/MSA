# MSA 后台点击 Hook 方案规划书

> 版本：1.0
> 日期：2026-01-05
> 状态：待实施

---

## 一、项目背景与目标

### 1.1 现状分析

MSA 当前使用 MAA Framework 内置的 `Seize` 模式进行鼠标控制，该模式：

- 需要游戏窗口处于前台
- 会完全抢占用户鼠标
- 用户无法在脚本运行期间进行其他操作

### 1.2 目标

实现**真正的后台点击**，使脚本运行时：

- 游戏窗口可以处于后台
- 不抢占用户鼠标
- 用户可以正常使用电脑进行其他操作

### 1.3 技术原理

《星纪元》的点击检测机制经测试验证：

- 游戏会通过 `GetCursorPos` 检测实际鼠标位置
- 游戏会通过 `GetForegroundWindow` 检测窗口激活状态
- 仅发送 `WM_LBUTTONDOWN/UP` 消息无法触发点击

**解决方案**：通过 DLL 注入 + API Hook，在游戏进程内拦截上述 API 调用，返回伪造的鼠标位置和窗口状态。

---

## 二、技术方案

### 2.1 Hook 目标 API

| API | 作用 | 优先级 |
|-----|------|--------|
| `GetCursorPos` | 返回伪造的鼠标坐标（脚本指定的点击位置） | 必须 |
| `GetForegroundWindow` | 返回游戏窗口句柄（伪装为前台窗口） | 必须 |

> 键盘相关 API 暂不 Hook，因为游戏为纯鼠标操作。后续如有需要可扩展。

### 2.2 注入方式

**选择：`CreateRemoteThread` + `LoadLibraryW`**

理由：

1. **精准定向**：只注入到《星纪元》进程，不影响系统其他进程
2. **标准方式**：Windows 系统级 API，行为可预测
3. **隔离性好**：不会触发其他游戏的反作弊系统（如 EAC、BattlEye 等），因为它们只监控自己的进程
4. **杀软友好**：相比 Manual Map 等高级技术，标准注入方式被误报的概率更低

**安全措施**：

- 注入器仅在用户主动触发时运行
- 严格校验目标进程名（`StarEra.exe`）
- 注入完成后注入器立即退出，不驻留后台
- DLL 内部只做 Hook 操作，不进行任何网络通信或文件操作

### 2.3 Hook 技术

**选择：MinHook**

理由：

1. **轻量级**：仅需几个源文件，无外部依赖
2. **稳定可靠**：GitHub 4k+ Star，广泛应用于各类项目
3. **协议友好**：BSD 2-Clause 协议，可自由使用和分发
4. **跨架构**：同时支持 x86 和 x64
5. **线程安全**：内置多线程保护机制

### 2.4 通信机制

脚本与 Hook DLL 之间需要传递点击坐标，采用**共享内存**方案：

```
┌─────────────────┐     共享内存      ┌─────────────────┐
│   MSA 脚本      │ ◄──────────────► │   Hook DLL      │
│  (控制器)       │   - 目标坐标 X    │  (游戏进程内)   │
│                 │   - 目标坐标 Y    │                 │
│                 │   - 启用标志      │                 │
└─────────────────┘                   └─────────────────┘
```

**共享内存结构**：

- `enabled`: bool - Hook 是否生效
- `target_x`: int - 目标 X 坐标（客户区坐标）
- `target_y`: int - 目标 Y 坐标（客户区坐标）
- `hwnd`: HWND - 游戏窗口句柄

**工作流程**：

1. 脚本写入目标坐标到共享内存
2. 脚本设置 `enabled = true`
3. 脚本发送 `WM_LBUTTONDOWN` 消息
4. 游戏调用 `GetCursorPos` → Hook 返回共享内存中的坐标
5. 游戏调用 `GetForegroundWindow` → Hook 返回游戏窗口句柄
6. 游戏处理点击
7. 脚本发送 `WM_LBUTTONUP` 消息
8. 脚本设置 `enabled = false`

---

## 三、与 MAA Framework 集成

### 3.1 自定义控制器

在 `interface.json` 中新增控制器类型，与现有 `桌面端` 控制器平行：

```jsonc
"controller": [
    {
        "name": "桌面端",
        "type": "Win32",
        // ... 现有配置
    },
    {
        "name": "桌面端（后台版）",
        "type": "Win32",
        "win32": {
            "class_regex": ".*",
            "window_regex": "StarEra",
            "screencap": "FramePool",
            "mouse": "SendMessage",      // 使用消息方式
            "keyboard": "SendMessage"
        }
    }
]
```

> 注意：MAA 的 `SendMessage` 模式本身不会移动鼠标，配合 Hook 即可实现后台点击。

### 3.2 注入任务设计

新增独立任务 `启动后台操作`，实际作用为注入后台 Hook，位于任务列表最前面：

```
任务列表：
☑ 启动后台操作        ← 新增，默认勾选
☑ 跑图
☐ 竞技场
```

**任务流程**：

```
用户点击"开始"
       │
       ▼
┌──────────────────┐
│  检查是否勾选    │
│  "启动后台操作"      │
└────────┬─────────┘
         │ 是
         ▼
┌──────────────────┐
│  执行注入程序    │
│  (injector.exe)  │
└────────┬─────────┘
         │ 完成
         ▼
┌──────────────────┐
│  继续执行后续    │
│  游戏任务        │
└──────────────────┘
```

### 3.3 Pipeline 节点设计

```jsonc
// 注入任务入口节点
"开始注入Hook": {
    "action": {
        "type": "Command",
        "param": {
            "exec": "./hook/injector.exe",
            "args": []
        }
    },
    "next": ["注入完成检查"]
},

"注入完成检查": {
    // 检查注入是否成功（可选）
    "action": { "type": "DoNothing" },
    "next": []
}
```

---

## 四、项目结构

```
MSA/
├── assets/
│   ├── interface.json          # 修改：添加新控制器和任务
│   └── resource/
│       └── pipeline/
│           └── 注入Hook.json   # 新增：注入任务流程
│
├── hook/                        # 新增：Hook 模块根目录
│   ├── CMakeLists.txt          # CMake 构建配置
│   ├── README.md               # 模块说明文档
│   │
│   ├── injector/               # 注入器
│   │   ├── main.cpp            # 注入器入口
│   │   └── injector.h          # 注入逻辑
│   │
│   ├── dll/                    # Hook DLL
│   │   ├── dllmain.cpp         # DLL 入口
│   │   ├── hooks.cpp           # Hook 实现
│   │   ├── hooks.h
│   │   ├── shared_memory.cpp   # 共享内存通信
│   │   └── shared_memory.h
│   │
│   ├── common/                 # 公共定义
│   │   └── protocol.h          # 共享内存结构定义
│   │
│   └── third_party/            # 第三方库
│       └── minhook/            # MinHook 源码
│
├── agent/                       # 现有 Python Agent（无需修改）
│
└── tools/
    └── install.py              # 修改：打包时包含 hook 模块产物
```

### 4.1 构建产物

构建后在 `install/` 目录生成：

```
install/
├── hook/
│   ├── injector.exe            # 注入器可执行文件
│   └── msa_hook.dll            # Hook DLL
└── ...
```

### 4.2 构建集成

在 `tools/install.py` 中添加 hook 模块的打包逻辑：

```python
# 复制 hook 模块产物
shutil.copytree("hook/build/Release", "install/hook")
```

---

## 五、用户体验设计

### 5.1 默认行为

- 新用户首次使用时，`启动后台操作` 任务默认勾选
- 控制器默认选择 `桌面端（后台版）`
- 用户无需额外配置即可享受后台点击

### 5.2 操作流程

```
1. 启动游戏
2. 启动 MSA
3. 自动连接游戏窗口
4. 确认勾选"启动后台操作"任务
5. 点击"开始任务"
6. 脚本自动完成注入，然后执行游戏任务
7. 用户可以切换到其他窗口正常使用电脑
```

### 5.3 切换控制模式

如果用户遇到问题，可以：

1. 取消勾选 `启动后台操作` 任务
2. 在控制器下拉框选择 `桌面端`（原生模式）
3. 重新开始任务

---

## 六、错误处理

### 6.1 错误类型与处理

| 错误场景 | 检测方式 | 处理方式 |
|---------|---------|---------|
| 游戏未启动 | 注入器找不到进程 | 日志报错 + GUI 提示 |
| 注入失败 | 注入器返回非零退出码 | 日志报错 + GUI 提示 |
| 游戏更新导致不兼容 | Hook 函数地址异常 | 日志报错 + GUI 提示 |
| 共享内存创建失败 | API 返回错误 | 日志报错 + GUI 提示 |

### 6.2 错误提示格式

```
[错误] Hook注入失败：未找到游戏进程
请确保游戏已启动，或切换到"桌面端"控制器使用原生模式。
```

### 6.3 不自动回退原则

当 Hook 模式出现问题时：

- **不**自动切换到原生控制器
- 明确告知用户问题所在
- 引导用户手动切换控制器

理由：避免用户困惑，确保用户清楚当前脚本的运行模式。

---

## 七、开发阶段划分

### 阶段一：基础 Hook 实现

**目标**：验证 Hook 方案可行性

**交付物**：

- [ ] MinHook 集成
- [ ] `GetCursorPos` Hook 实现
- [ ] `GetForegroundWindow` Hook 实现
- [ ] 简单测试程序验证 Hook 效果

**验收标准**：

- 手动注入 DLL 后，游戏能响应后台发送的点击消息

### 阶段二：通信机制

**目标**：实现脚本与 DLL 的坐标传递

**交付物**：

- [ ] 共享内存模块
- [ ] 协议定义
- [ ] 注入器程序

**验收标准**：

- 脚本能通过共享内存控制 Hook 行为
- 注入器能自动完成注入流程

### 阶段三：MAA 集成

**目标**：与现有任务系统无缝集成

**交付物**：

- [ ] 新控制器配置
- [ ] 注入任务 Pipeline
- [ ] interface.json 更新

**验收标准**：

- 用户可在 GUI 中选择 Hook 模式
- 任务执行前自动完成注入

### 阶段四：完善与测试

**目标**：提升稳定性和用户体验

**交付物**：

- [ ] 错误处理完善
- [ ] 日志输出
- [ ] 构建脚本更新
- [ ] 用户文档

**验收标准**：

- 各种异常场景都有合理的错误提示
- 构建产物完整可用

---

## 八、风险与注意事项

### 8.1 杀毒软件误报

**风险**：DLL 注入行为可能被杀毒软件标记为可疑

**缓解措施**：

- 使用标准 Windows API，避免使用高级注入技术
- 代码开源，用户可自行审查和编译
- 提供详细说明文档，解释技术原理
- 如有条件，考虑代码签名

### 8.2 游戏更新兼容性

**风险**：游戏更新可能改变检测机制

**缓解措施**：

- Hook 的是 Windows 系统 API，而非游戏内部函数，兼容性较好
- 保留原生控制器作为备选方案
- 建立问题反馈渠道，及时响应兼容性问题

### 8.3 多开场景

**风险**：用户可能同时运行多个游戏实例

**处理方式**：

- 注入器默认注入第一个找到的游戏进程
- 后续可扩展支持指定进程 ID

### 8.4 权限问题

**说明**：

- 注入器需要足够权限访问游戏进程
- 如果游戏以管理员权限运行，注入器也需要管理员权限
- 可在注入器 manifest 中声明 `requireAdministrator`

---

## 九、后续扩展可能

以下功能不在当前规划范围内，但架构设计时应预留扩展空间：

1. **键盘 Hook**：如果后续游戏增加键盘操作需求
2. **多点触控**：如果需要支持复杂手势
3. **滑动操作**：Hook 滑动轨迹的坐标返回
4. **配置界面**：在 GUI 中提供 Hook 相关的高级设置

---

## 十、参考资料

- [MAA Framework 控制方式说明](https://maafw.xyz/docs/2.4-ControlMethods)
- [MinHook GitHub](https://github.com/TsudaKageworker/minhook)
- [Windows 消息机制](https://docs.microsoft.com/en-us/windows/win32/winmsg/about-messages-and-message-queues)
- [共享内存 IPC](https://docs.microsoft.com/en-us/windows/win32/memory/creating-named-shared-memory)

---

## 附录 A：关键 API 签名

```cpp
// 需要 Hook 的 API
BOOL WINAPI GetCursorPos(LPPOINT lpPoint);
HWND WINAPI GetForegroundWindow(void);

// 共享内存相关
HANDLE CreateFileMappingW(HANDLE, LPSECURITY_ATTRIBUTES, DWORD, DWORD, DWORD, LPCWSTR);
LPVOID MapViewOfFile(HANDLE, DWORD, DWORD, DWORD, SIZE_T);

// 注入相关
HANDLE OpenProcess(DWORD, BOOL, DWORD);
LPVOID VirtualAllocEx(HANDLE, LPVOID, SIZE_T, DWORD, DWORD);
BOOL WriteProcessMemory(HANDLE, LPVOID, LPCVOID, SIZE_T, SIZE_T*);
HANDLE CreateRemoteThread(HANDLE, LPSECURITY_ATTRIBUTES, SIZE_T, LPTHREAD_START_ROUTINE, LPVOID, DWORD, LPDWORD);
```

## 附录 B：共享内存协议定义

```cpp
// common/protocol.h
#pragma once
#include <Windows.h>

#define MSA_SHARED_MEMORY_NAME L"MSA_Hook_SharedMemory"

#pragma pack(push, 1)
struct MSAHookData {
    volatile bool enabled;      // Hook 是否生效
    volatile LONG target_x;     // 目标 X 坐标（客户区）
    volatile LONG target_y;     // 目标 Y 坐标（客户区）
    volatile HWND game_hwnd;    // 游戏窗口句柄
    volatile DWORD version;     // 协议版本，用于兼容性检查
};
#pragma pack(pop)

constexpr DWORD MSA_PROTOCOL_VERSION = 1;
```

---

*本规划书为 MSA 后台点击 Hook 功能的顶层设计文档，具体实现细节将在各阶段开发时确定。*
