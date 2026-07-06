# CLAUDE.md

## 项目性质

本仓库是从 [comfyanonymous/ComfyUI](https://github.com/comfyanonymous/ComfyUI) fork 的分支，绝大部分代码与上游保持一致。`AGENTS.md` 中的工程规范同样适用于本项目。

本仓库仅用于**个人本地使用**，不向 ComfyUI 官方仓库贡献内容。因此不必担心个性化配置（如工作流、UI 设置等）会污染上游仓库；相反，应保留必要的用户数据（尤其是 `user/default/workflows/` 下的工作流文件），使其纳入版本管理，便于在不同环境间同步与恢复。

## 模型文件

- 模型文件存放在 `models/` 目录下，目录结构遵循 ComfyUI 官方格式。
- **严禁主动操作模型文件**（包括读取、移动、修改、删除、分析模型权重等）。
- 仅当用户**明确要求**下载新模型时，才可以执行模型下载操作。
