# 完成修改后的自检清单

- 改了 `assets/resource/pipeline/*.json` 或图片后：跑 `python check_resource.py assets/resource`（能尽早发现 JSON 结构/字段问题）。
- 提交前：确保 pre-commit 已安装并启用（会自动格式化 JSON/Markdown/PNG）。
- 如果要发布/打包：用 `python tools/install.py ...` 重新生成 `install/`，确认 `assets/interface.json` 里的版本号已更新。
