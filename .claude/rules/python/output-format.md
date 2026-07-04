---
paths:
  - "**/*.py"
  - "**/*.pyi"
---
# Python 输出格式规范

> 本文件扩展全局 `ecc/python/hooks.md` 中的 print 警告，补充具体实践指导。

## 禁止 `print()` 输出

项目 `pyproject.toml` 已启用 Ruff **T201** 规则（`flake8-print`），所有 Python 文件中 **禁止使用 `print()` 函数**。

### 原因

| `print()` | `logging` |
|-----------|-----------|
| 无日志级别 | 支持 DEBUG / INFO / WARNING / ERROR / CRITICAL |
| 无时间戳 | 可按需配置时间戳格式 |
| 无模块来源 | 自动记录 `__name__` 便于定位 |
| 只能写 stdout | 可输出到文件、syslog、集中日志系统 |
| 干扰协议通信 | 独立日志流，不影响 stdout 协议 |

## 正确做法：使用 `logging` 模块

### 库/模块代码（默认）

```python
import logging

logger = logging.getLogger(__name__)

logger.debug("详细的调试信息")
logger.info("运行时关键节点")
logger.warning("需要关注但非致命的异常")
logger.error("发生了错误")
```

- 使用 `logging.getLogger(__name__)` 创建模块级 logger
- 日志消息使用 `%s` 格式化参数（lazy evaluation），**不要用 f-string**：
  ```python
  # ✅ 正确
  logger.info("用户 %s 已登录", username)

  # ❌ 错误
  logger.info(f"用户 {username} 已登录")
  ```

### CLI 启动器/独立脚本

对于直接面向终端用户的脚本（如 `launcher/launch_comfyui.py`），在入口处配置简洁格式：

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",       # 仅显示消息，无前缀
    stream=sys.stdout,
)
logger = logging.getLogger("launcher")
```

- `format="%(message)s"` 确保终端输出干净，与 print 的视觉效果一致
- 使用独立 logger 名称（如 `"launcher"`），避免与模块 logger 冲突

### 日志级别选用

| 场景 | 级别 | 示例 |
|------|------|------|
| 开发调试、变量追踪 | `DEBUG` | `logger.debug("计算结果: %s", result)` |
| 正常运行时状态 | `INFO` | `logger.info("服务器已启动")` |
| 可恢复的异常 | `WARNING` | `logger.warning("配置文件缺失，使用默认值")` |
| 操作失败需关注 | `ERROR` | `logger.error("数据库连接失败")` |
| 致命错误需终止 | `CRITICAL` | `logger.critical("磁盘空间不足，无法继续")` |

## 例外

以下场景可以使用 `print()`，但需在文件顶部添加 `# noqa: T201` 注释：

1. **一次性调试脚本**：不会提交到仓库的本地脚本
2. **命令行工具**：需要通过 stdout 输出结构化数据给管道处理的工具

生产代码中任何提交到仓库的 `print()` 都不被接受。
