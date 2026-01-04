# 项目概览（MSA）

## 项目是做什么的
- 这是基于 MaaFramework 的项目模板（见 `README.md`），用于做“看屏幕 → 识别 → 执行动作 → 按流程跳转”的自动化流程。
- 当前项目在 `assets/interface.json` 中声明名称为 `MSA`，控制目标是桌面窗口（`Win32`，窗口名匹配 `StarEra`）。

## 主要技术组成
- Python：用于写可选的“自定义识别/自定义动作”（`agent/` 目录）。
- 资源文件：图片、文字识别模型、以及流程（pipeline）JSON，位于 `assets/resource/`。
- 工程工具：用 pre-commit 统一格式化（JSON/Markdown），见 `.pre-commit-config.yaml`。

## 目录结构（和你最常碰的）
- `assets/interface.json`：项目对外描述、控制器配置、资源路径、任务入口节点等。
- `assets/resource/pipeline/`：流程节点 JSON（每个 JSON 顶层 key 是“节点名”）。
- `agent/`：自定义动作/识别示例（`AgentServer.custom_action/custom_recognition`）。
- `tools/install.py`：构建脚本，把运行所需文件复制到 `install/` 目录（CI 构建产物，不应在开发时参考）。
- `check_resource.py`：调用 MaaFramework 的资源检查接口，对资源目录做校验。
