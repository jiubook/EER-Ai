"""更新安装模块"""

import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

from endfield_essence_recognizer.utils.log import logger


def install_update(zip_path: Path) -> bool:
    """安装更新

    Args:
        zip_path: 更新包路径

    Returns:
        bool: 安装是否成功
    """
    try:
        # 获取当前程序目录
        if getattr(sys, "frozen", False):
            current_dir = Path(sys.executable).parent
        else:
            current_dir = Path.cwd()

        # 创建临时解压目录
        temp_dir = current_dir / "_update_temp"
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        temp_dir.mkdir()

        # 解压更新包
        logger.info(f"解压更新包到: {temp_dir}")
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(temp_dir)

        # 创建更新脚本
        updater_script = current_dir / "_updater.bat"

        script_content = """@echo off
chcp 65001 >nul
echo Waiting for program to close...
timeout /t 3 /nobreak >nul

:wait_loop
tasklist /FI "IMAGENAME eq endfield-essence-recognizer.exe" 2>NUL | find /I /N "endfield-essence-recognizer.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo Program still running, waiting...
    timeout /t 1 /nobreak >nul
    goto wait_loop
)

echo Waiting for file handles to release...
timeout /t 2 /nobreak >nul

echo Protecting user configuration...
if exist "%~dp0config.json" (
    copy /Y "%~dp0config.json" "%~dp0config.json.protected" >nul
    echo Config file backed up
)

echo Deleting old program files...
if exist "%~dp0endfield-essence-recognizer.exe" del /F /Q "%~dp0endfield-essence-recognizer.exe" 2>nul
if exist "%~dp0_internal" rmdir /S /Q "%~dp0_internal" 2>nul
if exist "%~dp0logs" rmdir /S /Q "%~dp0logs" 2>nul
if exist "%~dp0resources" rmdir /S /Q "%~dp0resources" 2>nul
if exist "%~dp0README.md" del /F /Q "%~dp0README.md" 2>nul
if exist "%~dp0界面白屏解决方法.md" del /F /Q "%~dp0界面白屏解决方法.md" 2>nul
if exist "%~dp0遇到报错解决方法.webp" del /F /Q "%~dp0遇到报错解决方法.webp" 2>nul

echo Copying new files...
set retry=0
:copy_retry
xcopy /E /Y /I "%~dp0_update_temp\\*" "%~dp0" 2>nul
if errorlevel 1 (
    set /a retry+=1
    if !retry! lss 5 (
        echo Copy failed, retrying... (attempt !retry!/5^)
        timeout /t 2 /nobreak >nul
        goto copy_retry
    )
    echo File copy failed after 5 attempts
    pause
    exit /b 1
)

echo Cleaning up...
rmdir /S /Q "%~dp0_update_temp"
rmdir /S /Q "%~dp0_updates"

echo Restoring user configuration...
if exist "%~dp0config.json.protected" (
    move /Y "%~dp0config.json.protected" "%~dp0config.json" >nul
    echo Config file restored
)

echo Starting new version...
start "" "%~dp0endfield-essence-recognizer.exe"

timeout /t 1 /nobreak >nul
del "%~f0"
"""
        updater_script.write_text(script_content, encoding="gbk")

        logger.info("启动更新脚本并退出程序")
        subprocess.Popen(
            ["cmd.exe", "/c", str(updater_script)],
            creationflags=subprocess.CREATE_NEW_CONSOLE,
        )

        # 延迟退出，确保响应返回给前端
        import threading

        def delayed_exit():
            import os
            import time

            time.sleep(1)
            os._exit(0)

        threading.Thread(target=delayed_exit, daemon=True).start()

        return True

    except Exception as e:
        logger.error(f"安装更新失败: {e}")
        return False
