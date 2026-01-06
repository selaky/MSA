# MSA 后台点击 Hook 方案规划书 v2

> 版本：2.0
> 日期：2026-01-06
> 状态：待实施
> 前置文档：`后台点击Hook方案规划书.md`（已归档）

---

## 一、方案变更说明

原方案第四阶段（自定义控制器集成到 GUI）无法实施，原因：MFAAvalonia 不支持自定义控制器。

新方案：通过 Proxy DLL 替换 MAA Framework 的 `MaaWin32ControlUnit.dll`，修改 `SendMessage` 输入方法的实现。

---

## 二、技术方案

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                      MSA 后台点击架构 v2                     │
├─────────────────────────────────────────────────────────────┤
│  Proxy DLL (MaaWin32ControlUnit.dll)                        │
│    - 动态加载原版 DLL (MaaWin32ControlUnit_original.dll)    │
│    - 透传所有函数，仅修改 SendMessage 输入方法              │
│    - 点击时：检查注入 → 写入共享内存 → 发送消息             │
├─────────────────────────────────────────────────────────────┤
│  Hook DLL (msa_hook.dll) - 注入到游戏进程                   │
│    - Hook GetCursorPos → 返回共享内存中的坐标               │
├─────────────────────────────────────────────────────────────┤
│  共享内存 - Proxy DLL 与 Hook DLL 的通信桥梁                │
│    - 目标坐标、窗口句柄、启用标志                           │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Proxy DLL

**职责**：

- 加载原版 DLL（`MaaWin32ControlUnit_original.dll`）
- 导出与原版相同的函数
- 大部分函数直接转发到原版
- `SendMessage` 输入方法替换为自定义实现

**SendMessage 输入方法修改**：

- 点击前检查注入状态，失效则重新注入
- 写入坐标到共享内存
- 设置 `enabled = true`
- 发送 `WM_ACTIVATE` 伪造激活
- 发送 `WM_LBUTTONDOWN` / `WM_LBUTTONUP`
- 设置 `enabled = false`

### 2.3 Hook DLL

与原方案一致，参考 `后台点击Hook方案规划书.md` 第 2.3 节。

### 2.4 通信机制

与原方案一致，参考 `后台点击Hook方案规划书.md` 第 2.4 节。

### 2.5 截图方法

不修改，使用 MAA Framework 自带的 `FramePool`。

---

## 三、用户操作流程

1. 启动游戏 → 启动 MSA
2. 选择"桌面端"控制器
3. 鼠标控制方式选择 `SendMessage`（后台模式）
4. 点击开始 → 自动注入 → 执行任务
5. 若后台模式不生效，用户可切换到 `SendMessageWithCursorPos`（前台模式）

---

## 四、项目结构

```
MSA/
├── hook/                            # 后台点击模块
│   ├── CMakeLists.txt
│   │
│   ├── proxy/                      # Proxy DLL（新增）
│   │   ├── dllmain.cpp             # DLL 入口，加载原版 DLL
│   │   ├── exports.cpp             # 导出函数转发
│   │   ├── input_hook.cpp          # SendMessage 输入方法修改
│   │   ├── injector.cpp            # 注入逻辑
│   │   └── shared_memory.cpp       # 共享内存（Proxy 端）
│   │
│   ├── dll/                        # Hook DLL（已有）
│   │   ├── dllmain.cpp
│   │   ├── hooks.cpp
│   │   └── shared_memory.cpp
│   │
│   ├── common/
│   │   └── protocol.h              # 共享内存结构定义
│   │
│   └── third_party/
│       └── minhook/
│
└── tools/
    ├── install.py                  # 修改：打包时处理 DLL 替换
    └── dump_exports.py             # 新增：读取 DLL 导出函数表
```

**构建产物**：

- `MaaWin32ControlUnit.dll` - Proxy DLL
- `MaaWin32ControlUnit_original.dll` - 原版 DLL（改名）
- `msa_hook.dll` - Hook DLL

---

## 五、开发阶段

### 阶段一：Hook DLL（已完成）

参考原方案，Hook DLL 已开发完成。

### 阶段二：导出函数分析

- 编写 `dump_exports.py` 脚本，存入 `my_tools` 文件夹, 读取 `MaaWin32ControlUnit.dll` 导出函数表
- 分析需要转发的函数列表
- **验收**：脚本能正确输出所有导出函数名和序号

### 阶段三：Proxy DLL 框架

- 实现 DLL 加载和函数转发框架
- 所有函数透传到原版 DLL
- **验收**：替换 DLL 后，MAA 功能正常（行为与原版一致）

### 阶段四：SendMessage 输入方法修改

- 修改 SendMessage 输入方法实现
- 集成注入逻辑和共享内存通信
- **验收**：选择 SendMessage 方式时，能实现后台点击

### 阶段五：构建与打包

- 更新 CMakeLists.txt
- 更新 install.py 打包脚本
- **验收**：构建产物正确，打包后目录结构正确

---

## 六、错误处理

| 错误场景 | 处理方式 |
|---------|---------|
| 原版 DLL 加载失败 | 记录日志，返回失败 |
| 游戏未启动 | 注入失败，返回失败 |
| 注入失败 | 记录日志，返回失败 |
| 共享内存失败 | 记录日志，返回失败 |

**原则**：失败不自动降级，用户可自行切换到 `SendMessageWithCursorPos`。

---

## 七、风险与注意事项

| 风险 | 缓解措施 |
|------|---------|
| 杀软误报 | 使用标准 API，代码开源 |
| MAA 更新导致接口变化 | 定期检查上游更新，更新导出函数表 |
| 多开场景 | 默认注入第一个进程 |

---

## 八、与原方案差异对照

| 项目 | 原方案 | 新方案 |
|------|--------|--------|
| 控制器类型 | 自定义控制器 | Proxy DLL 替换原版 |
| 截图实现 | Windows Graphics Capture | 使用 MAA 自带 FramePool |
| 输入方法 | 完全自定义 | 仅修改 SendMessage |
| GUI 集成 | 新增控制器选项 | 复用现有选项 |
| 回退方案 | 切换到原生控制器 | 切换到 SendMessageWithCursorPos |
