# 风格与约定

## Python（`agent/`）
- 写法偏简洁，示例里有类型标注（例如 `Context`、`CustomAction.RunArg`）。
- 主要通过装饰器注册：
  - `@AgentServer.custom_action("...")`
  - `@AgentServer.custom_recognition("...")`

## JSON / Markdown
- JSON、Yaml：用 prettier 统一格式（见 `.pre-commit-config.yaml`）。
- Markdown：用 markdownlint 统一格式（见 `.pre-commit-config.yaml`、`docs/.markdownlint.yaml`）。

## pipeline JSON（`assets/resource/pipeline/*.json`）
- 顶层是一个对象：每个 key 是“节点名”，value 是该节点的识别方式、动作、以及 `next`（下一步可能去哪里）。
- `next` 里写的是“节点名”（字符串），或带属性的对象（例如 `jump_back` 这类）。
