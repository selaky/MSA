# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

MSA (Miss.Sirius Assistant) 是基于 [MAA Framework](https://github.com/MaaXYZ/MaaFramework) 开发的《星纪元》游戏自动化脚本。

**主要功能**：自动跑图、自动战斗、自动补给、竞技场、世界 BOSS

**版本**：0.5.0 (Beta)

## 常用命令

```bash
# Pipeline 配置检查
python my_tools/check_pipeline.py              # 检测悬空引用、重复节点、缺失模板图片等
python my_tools/check_pipeline.py --strict     # 严格模式（有 WARN 也返回非 0）
python my_tools/check_pipeline.py --no-unreachable  # 不提示"可能未触达的遗留节点"

# Pipeline 节点优先级检查
python my_tools/check_priority.py              # 检查 next 列表优先级顺序
python my_tools/check_priority.py --fix        # 自动修正优先级顺序

# Hook 模块兼容性检测
python my_tools/hook/check_maa_compat.py       # 检测 MAA Framework 更新后的 ABI 兼容性
python my_tools/hook/check_maa_compat.py --offline  # 离线模式（使用缓存）

# JSON 格式化（使用 prettier）
npx prettier --write "assets/**/*.json"

# Hook 模块构建（Windows，需要 CMake 和 MSVC）
cd hook && build.bat

# 打包发布
python tools/install.py v0.5.0 win x86_64
```

## 核心架构

### 目录结构

```
assets/                          # 主要开发目录
├── interface.json               # UI 配置、任务入口、用户选项定义
└── resource/
    ├── pipeline/                # 任务流水线 JSON 文件
    │   ├── 跑图/                # 跑图相关（主流程、战斗、恢复、升级处理）
    │   ├── 导航/                # 导航相关（前往地图、竞技场、世界BOSS、返回主界面）
    │   ├── 竞技场.json
    │   ├── 世界BOSS.json
    │   └── 意外处理.json
    └── image/                   # 模板匹配图片资源

agent/                           # Python Agent 模块
├── main.py                      # Agent 入口
├── recover/                     # 恢复（吃药）模块
├── arena/                       # 竞技场模块
├── boss/                        # 世界 BOSS 模块
└── utils/                       # 通用工具（common_action, common_reco, common_func）

hook/                            # 后台点击 Hook 模块（C++）
├── dll/                         # Hook DLL（注入游戏进程，Hook GetCursorPos）
├── proxy/                       # 代理 DLL（替换 MAA 原版控制单元）
├── CMakeLists.txt               # CMake 构建配置
└── build.bat                    # 构建脚本

my_tools/                        # 自定义工具
├── check_pipeline.py            # Pipeline 自检脚本
├── check_priority.py            # 节点优先级检查
└── hook/check_maa_compat.py     # MAA Framework 兼容性检测

deps/                            # MAA Framework SDK 和文档
└── docs/zh_cn/                  # 中文文档
```

### MAA Framework Pipeline 机制

1. **任务触发**：通过 `tasker.post_task` 指定入口节点启动任务
2. **顺序检测**：对当前节点的 `next` 列表依次尝试识别每个子节点的 `recognition` 特征
3. **中断机制**：检测到某个子节点匹配成功时，立即终止后续检测，执行匹配节点的 `action`
4. **后继处理**：操作完成后，将激活节点切换为当前节点，重复检测流程
5. **终止条件**：`next` 为空，或所有后继节点持续检测失败直至超时

**Pipeline JSON 节点示例**：

```jsonc
{
    "节点名": {
        "recognition": "TemplateMatch",
        "template": ["路径/图片.png"],
        "roi": [x, y, w, h],
        "action": "Click",
        "next": ["下一节点A", "下一节点B"]
    }
}
```

### 后台点击实现（Hook 方案）

通过 DLL 代理 + API Hook 实现后台操作，无需游戏窗口前台显示：

1. **MaaWin32ControlUnit.dll（代理 DLL）**：
   - 加载原版 `MaaWin32ControlUnit_original.dll`
   - 截图操作委托原版实现
   - 输入操作使用自定义实现（后台点击）
   - 注入 `msa_hook.dll` 到游戏进程

2. **msa_hook.dll（Hook DLL）**：
   - 使用 MinHook 库 Hook `GetCursorPos` API
   - 通过共享内存接收目标坐标
   - 返回伪造的光标位置，使游戏认为鼠标在目标位置

3. **共享内存**：代理 DLL 和 Hook DLL 之间的通信机制

### Python Agent

Agent 通过 `maa.agent.agent_server` 实现自定义识别和动作：

```python
from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction

@AgentServer.custom_action("action_name")
class MyAction(CustomAction):
    def run(self, context, argv) -> bool:
        # 实现自定义逻辑
        return True
```

**已实现的 Agent 模块**：

- `recover/`：药品恢复逻辑（PotionManager 管理大小 APBC 药使用）
- `arena/`：竞技场数据管理（积分追踪、战斗结果记录）
- `boss/`：世界 BOSS 数据管理（战斗计数、排名检测）
- `utils/`：通用函数（时间判断、参数解析）

## 关键配置文件

**interface.json**：

- `task`：任务列表，每个任务有 `entry`（入口节点）和 `option`（用户选项）
- `option`：用户可配置选项，通过 `pipeline_override` 动态修改节点属性
- `controller`：控制器配置（Win32 桌面端）
- `agent`：Python Agent 配置

## 开发注意事项

- Pipeline JSON 支持 JSONC 注释（`//` 和 `/* */`）
- 节点名不能以 `$` 开头（保留给编辑器元数据）
- 模板图片路径相对于 `assets/resource/image/`
- `pipeline_override` 可在 interface.json 中动态覆盖节点属性
- Hook 模块仅支持 Windows 平台，需要 CMake 3.15+ 和 MSVC 编译
- 修改 Hook 代码或 Maa Framwork 更新后需运行兼容性检测

## 相关文档

- MAA Framework Pipeline 协议：`deps/docs/zh_cn/3.1-任务流水线协议.md`
- ProjectInterface 协议：`deps/docs/zh_cn/3.3-ProjectInterfaceV2协议.md`
- 控制方式说明：`deps/docs/zh_cn/2.4-控制方式说明.md`
- 后台点击方案设计：`docs/development_notes/后台点击Hook方案规划书v2.md`
