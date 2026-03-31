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

        # 查找解压后的实际目录（可能在子目录中）
        extracted_dirs = list(temp_dir.iterdir())
        if len(extracted_dirs) == 1 and extracted_dirs[0].is_dir():
            source_dir = extracted_dirs[0]
        else:
            source_dir = temp_dir

        zip_filename = zip_path.name
        script_content = f"""@echo off
chcp 65001 >nul
echo Waiting for program to close...
timeout /t 2 /nobreak >nul

:wait_loop
tasklist /FI "IMAGENAME eq endfield-essence-recognizer.exe" 2>NUL | find /I /N "endfield-essence-recognizer.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo Program still running, waiting...
    timeout /t 1 /nobreak >nul
    goto wait_loop
)

echo Deleting old files...
for /d %%d in ("{current_dir}\\*") do (
    if /i not "%%~nxd"=="_updates" if /i not "%%~nxd"=="_update_temp" if /i not "%%~nxd"=="data" (
        rmdir /S /Q "%%d" 2>nul
    )
)
for %%f in ("{current_dir}\\*") do (
    if /i not "%%~nxf"=="_updater.bat" if /i not "%%~nxf"=="{zip_filename}" if /i not "%%~nxf"=="config.json" (
        del /F /Q "%%f" 2>nul
    )
)

echo Copying new files...
xcopy /E /Y /I "{source_dir}\\*" "{current_dir}\\"
if errorlevel 1 (
    echo File copy failed
    pause
    exit /b 1
)

echo Cleaning up...
rmdir /S /Q "{temp_dir}"
del "{zip_path}"

echo Starting new version...
start "" "{current_dir}\\endfield-essence-recognizer.exe"

timeout /t 1 /nobreak >nul
del "%~f0"
"""
        updater_script.write_text(script_content, encoding="gbk")

        logger.info("启动更新脚本并退出程序")
        subprocess.Popen(
            ["cmd.exe", "/c", str(updater_script)],
            creationflags=subprocess.CREATE_NEW_CONSOLE | subprocess.DETACHED_PROCESS,
        )

        # 延迟退出，确保响应返回给前端
        import threading

        def delayed_exit():
            import time

            time.sleep(1)
            import os

            os._exit(0)

        threading.Thread(target=delayed_exit, daemon=True).start()

        return True

    except Exception as e:
        logger.error(f"安装更新失败: {e}")
        return False
