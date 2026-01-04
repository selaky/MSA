# 常用命令（Windows / PowerShell）

## 资源检查（改完 pipeline/图片后建议跑）
- `python check_resource.py assets/resource`
  - 用于检查资源目录是否能被 MaaFramework 正常读取（包括 pipeline JSON）。

## 打包安装目录（CI 构建产物，生成 `install/`）
- `python tools/install.py <version> <os> <arch>`
  - 示例：`python tools/install.py v0.1.0 win x86_64`
  - 作用：复制 `deps/bin`、`assets/resource`、`assets/interface.json`、`agent/` 等到 `install/`。
  - 注意：`install/` 是构建产物目录，已在 .gitignore 中忽略，开发时不应参考其中内容。

## 开发时的自动格式化（可选，但推荐）
- `pip install pre-commit`
- `pre-commit install`
  - 提交代码时会自动格式化：JSON/Yaml（prettier）、Markdown（markdownlint）、PNG（oxipng）。

## Node 依赖（仅用于 prettier 插件）
- `npm install`
  - 安装 `prettier-plugin-multiline-arrays`（见 `package.json`）。
