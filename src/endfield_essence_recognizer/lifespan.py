import importlib.resources
import mimetypes
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from endfield_essence_recognizer.core.config import ServerConfig, get_server_config
from endfield_essence_recognizer.dependencies import (
    default_user_setting_manager,
    get_log_service,
)
from endfield_essence_recognizer.hotkey_entrypoints import bind_hotkeys
from endfield_essence_recognizer.utils.log import logger


def log_welcome_message():
    """Log a formatted welcome and usage guide message to the logger."""
    message = """
==================================================
<green><bold>终末地基质妙妙小工具已启动</></>
==================================================
<green><bold>使用前阅读：</></>
  - 请使用<yellow><bold>管理员权限</></>运行本工具，否则无法捕获全局热键
  - 支持分辨率自动缩放，按照原生 1080p 比例自动计算ROI缩放
  - 请按 "<green><bold>N</></>" 键打开终末地<yellow><bold>贵重品库</></>并切换到<yellow><bold>武器基质</></>页面
  - 在运行过程中，请确保终末地窗口<yellow><bold>置于前台</></>

<green><bold>功能介绍：</></>
  - 按 "<green><bold>[</></>" 键识别当前基质，仅识别不操作
  - 按 "<green><bold>]</></>" 键扫描所有基质，并根据设置，自动锁定或者解锁基质
    基质扫描过程中再次按 "<green><bold>]</></>" 键中断扫描
  - 按 "<green><bold>Alt+Delete</></>" 退出程序

  <cyan><bold>宝藏基质和养成材料：</></>可以在设置界面自定义。默认情况下，如果这个基质和任何一把武器能对上，则是宝藏，否则是养成材料。
==================================================
"""
    logger.opt(colors=True).info(message)


def init_load_user_setting():
    """Load user settings at startup."""
    user_setting_manager = default_user_setting_manager()
    user_setting_manager.load_user_setting()


def init_mount_frontend_build(app: FastAPI, server_config: ServerConfig):
    """Mount the frontend build directory to serve static files."""
    if server_config.dev_mode:
        return

    # 确保正确的 MIME 类型映射，避免 Windows 系统上的问题
    mimetypes.add_type("application/javascript", ".js")
    mimetypes.add_type("application/javascript", ".mjs")
    mimetypes.add_type("text/css", ".css")
    mimetypes.add_type("application/json", ".json")
    mimetypes.add_type("image/svg+xml", ".svg")
    mimetypes.add_type("application/wasm", ".wasm")

    if not server_config.dist_dir:
        dist_dir = (
            Path(str(importlib.resources.files("endfield_essence_recognizer")))
            / "webui_dist"
        )
    else:
        dist_dir = Path(server_config.dist_dir)
    if dist_dir.exists():
        app.mount("/", StaticFiles(directory=dist_dir, html=True), name="dist")
    else:
        logger.error(f"未找到前端构建文件夹: {dist_dir}")
        logger.error("请先执行前端构建: cd frontend && npm install && npm run build")
        # 提供一个简单的错误页面
        from fastapi.responses import HTMLResponse

        @app.get("/")
        async def fallback_error_page():
            return HTMLResponse(
                content="""
                <!DOCTYPE html>
                <html lang="zh-CN">
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <title>前端构建文件缺失</title>
                    <style>
                        body {
                            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                            display: flex;
                            justify-content: center;
                            align-items: center;
                            min-height: 100vh;
                            margin: 0;
                            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        }
                        .container {
                            background: white;
                            padding: 2rem;
                            border-radius: 8px;
                            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                            max-width: 600px;
                        }
                        h1 { color: #e53e3e; margin-top: 0; }
                        code {
                            background: #f7fafc;
                            padding: 0.2rem 0.4rem;
                            border-radius: 4px;
                            font-family: 'Courier New', monospace;
                        }
                        .command {
                            background: #2d3748;
                            color: #68d391;
                            padding: 1rem;
                            border-radius: 4px;
                            margin: 1rem 0;
                            font-family: 'Courier New', monospace;
                        }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <h1>⚠️ 前端构建文件缺失</h1>
                        <p>前端构建文件夹不存在，请先执行前端构建：</p>
                        <div class="command">
                            cd frontend<br>
                            npm install<br>
                            npm run build
                        </div>
                        <p>构建完成后，重新启动应用即可。</p>
                        <p><strong>构建文件夹路径：</strong> <code>""" + str(dist_dir) + """</code></p>
                    </div>
                </body>
                </html>
                """,
                status_code=503,
            )


@asynccontextmanager
async def lifespan(app: FastAPI):
    server_config = get_server_config()
    async with get_log_service().scope(server_config):
        logger.success(f"Server configuration: {server_config.model_dump()}")
        init_mount_frontend_build(app, server_config)
        init_load_user_setting()
        log_welcome_message()
        with bind_hotkeys(server_config):
            yield
