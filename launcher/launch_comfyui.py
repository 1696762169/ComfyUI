"""ComfyUI 一键启动器。

功能：
- 启动 ComfyUI 服务器
- 等待就绪后自动打开新浏览器窗口
- 按 Ctrl+C 或关闭本窗口即可停止服务器
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("launcher")

LAUNCHER_DIR = Path(__file__).resolve().parent
COMFYUI_ROOT = LAUNCHER_DIR.parent
VENV_DIR = COMFYUI_ROOT / ".venv"
PYTHON_EXE = (
    VENV_DIR / "Scripts" / "python.exe"
    if sys.platform == "win32"
    else VENV_DIR / "bin" / "python"
)
SERVER_URL = "http://127.0.0.1:8188"
HEALTH_URL = f"{SERVER_URL}/system_stats"


def start_server() -> subprocess.Popen:
    """启动 ComfyUI 服务器。"""
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["TQDM_DISABLE"] = "1"
    return subprocess.Popen(
        [str(PYTHON_EXE), "main.py", "--listen", "127.0.0.1", "--port", "8188"],
        cwd=str(COMFYUI_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=env,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )


def wait_for_server(timeout: float = 120.0) -> bool:
    """等待服务器就绪。"""
    start = time.time()
    while time.time() - start < timeout:
        try:
            with urllib.request.urlopen(HEALTH_URL, timeout=2) as response:
                if response.status == 200:
                    return True
        except Exception:
            time.sleep(0.5)
    return False


def open_browser() -> None:
    """在新浏览器窗口中打开 ComfyUI 前端。"""
    logger.info("正在打开浏览器：%s", SERVER_URL)
    if sys.platform == "win32":
        os.startfile(SERVER_URL)
    else:
        import webbrowser
        webbrowser.open_new(SERVER_URL)


def main() -> None:
    if not PYTHON_EXE.is_file():
        logger.error("错误：未找到 Python 解释器 %s", PYTHON_EXE)
        logger.error("请确认 .venv 已正确创建。")
        input("按 Enter 退出...")
        sys.exit(1)

    logger.info("")
    logger.info("  ComfyUI 启动器")
    logger.info("  ─────────────")
    logger.info("")

    logger.info("正在启动服务器...")
    proc = start_server()

    logger.info("等待服务器就绪...")
    if not wait_for_server():
        logger.error("错误：服务器启动超时，请检查日志。")

        # 读取并显示服务器输出的前几行
        if proc.stdout:
            out = proc.stdout.read()
            if out:
                logger.error("服务器输出（最后 2000 字符）：")
                logger.error(out[-2000:])

        proc.kill()
        input("按 Enter 退出...")
        sys.exit(1)

    logger.info("服务器已就绪：%s", SERVER_URL)
    open_browser()

    logger.info("")
    logger.info("  ─────────────────────────────────")
    logger.info("  按 Ctrl+C 或关闭本窗口以停止服务器")
    logger.info("  ─────────────────────────────────")
    logger.info("")

    try:
        _ = proc.wait()
    except KeyboardInterrupt:
        logger.info("")
        logger.info("正在停止服务器...")
        if sys.platform == "win32":
            subprocess.run(
                ["taskkill", "/T", "/F", "/PID", str(proc.pid)],
                capture_output=True,
            )
        else:
            import signal
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        logger.info("服务器已停止。")


if __name__ == "__main__":
    main()
