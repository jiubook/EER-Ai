"""更新安装模块

基于 manifest.json 实现增量更新：
- 新增：manifest 中有、本地没有的文件 → 复制
- 覆盖：manifest 中有、本地也有的文件 → 覆盖
- 删除：本地有、manifest 中没有、且不在 protected 列表中的文件 → 删除
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from endfield_essence_recognizer.utils.log import logger


def _load_manifest(temp_dir: Path) -> dict | None:
    """从解压目录中加载 manifest.json。

    Args:
        temp_dir: 解压后的临时目录。

    Returns:
        manifest 字典，如果文件不存在则返回 None。
    """
    manifest_path = temp_dir / "manifest.json"
    if not manifest_path.is_file():
        logger.warning("更新包中未找到 manifest.json，将使用回退方案")
        return None

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        # 基本校验
        if "files" not in manifest or "protected" not in manifest:
            logger.error("manifest.json 格式不完整，缺少 files 或 protected 字段")
            return None
        logger.info(
            f"加载 manifest: version={manifest.get('version', '?')}, "
            f"files={len(manifest['files'])}, protected={len(manifest['protected'])}"
        )
        return manifest
    except (json.JSONDecodeError, OSError) as exc:
        logger.error(f"加载 manifest.json 失败: {exc}")
        return None


def _generate_update_script_manifest(
    current_dir: Path,
    temp_dir: Path,
    manifest: dict,
) -> str:
    """生成基于 manifest 的批处理更新脚本。

    Args:
        current_dir: 当前程序所在目录。
        temp_dir: 解压后的临时目录。
        manifest: manifest 字典。

    Returns:
        批处理脚本内容。
    """
    # manifest 文件本身也需要在更新后保留
    # （它已经在 manifest["files"] 中了，因为 generate_manifest 会把它加进去）

    script = """@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

echo ========================================
echo  EER Updater - Manifest-based Update
echo ========================================

echo [1/5] Waiting for program to close...
timeout /t 3 /nobreak >nul

:wait_loop
tasklist /FI "IMAGENAME eq endfield-essence-recognizer.exe" 2>NUL | find /I /N "endfield-essence-recognizer.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo   Program still running, waiting...
    timeout /t 1 /nobreak >nul
    goto wait_loop
)

echo [2/5] Waiting for file handles to release...
timeout /t 2 /nobreak >nul

REM 检查写入权限（尝试创建测试文件）
echo test >"%~dp0__write_test__.tmp" 2>nul
if errorlevel 1 (
    echo ERROR: No write permission! Please run as administrator.
    echo Press any key to exit...
    pause >nul
    exit /b 1
)
del "%~dp0__write_test__.tmp" 2>nul

echo [3/5] Copying new / updated files from update package...

REM 校验 manifest 文件是否存在
if not exist "%~dp0_update_temp\\__manifest_files.txt" (
    echo ERROR: Manifest file missing! Update aborted.
    echo Press any key to exit...
    pause >nul
    exit /b 1
)

set copy_failed=0
set copy_count=0

REM 复制 manifest 中列出的所有文件（新增 + 覆盖）
for /F "usebackq delims=" %%F in ("%~dp0_update_temp\\__manifest_files.txt") do (
    if exist "%~dp0_update_temp\\%%F" (
        REM 确保目标目录存在
        for %%D in ("%~dp0%%F") do (
            if not exist "%%~dpD" mkdir "%%~dpD" 2>nul
        )
        copy /Y "%~dp0_update_temp\\%%F" "%~dp0%%F" >nul
        if errorlevel 1 (
            echo   FAILED: %%F
            set copy_failed=1
        ) else (
            set /a copy_count+=1
        )
    )
)

if !copy_failed!==1 (
    echo WARNING: Some files failed to copy.
)

echo   Copied !copy_count! files.

echo [4/5] Removing obsolete files...

REM 校验 protected 文件是否存在
if not exist "%~dp0_update_temp\\__protected.txt" (
    echo ERROR: Protected list missing! Skipping file deletion for safety.
    goto cleanup
)

REM 再次确认 manifest 文件存在（删除逻辑依赖它）
if not exist "%~dp0_update_temp\\__manifest_files.txt" (
    echo ERROR: Manifest file missing! Skipping file deletion for safety.
    goto cleanup
)

REM 读取受保护路径列表
set protected_list="%~dp0_update_temp\\__protected.txt"

REM 遍历当前目录中的所有文件，删除不在 manifest 中的
set delete_count=0
for /R "%~dp0" %%F in (*) do (
    REM 获取相对路径
    set "filepath=%%F"
    set "relpath=!filepath:%~dp0=!"
    REM 将反斜杠替换为正斜杠
    set "relpath=!relpath:\\=/!"

    REM 检查是否在 manifest files 列表中
    findstr /X /C:"!relpath!" "%~dp0_update_temp\\__manifest_files.txt" >nul 2>&1
    if errorlevel 1 (
        REM 不在 manifest 中，检查是否在 protected 列表中
        findstr /X /C:"!relpath!" "!protected_list!" >nul 2>&1
        if errorlevel 1 (
            REM 不在 protected 中，检查是否以 protected 目录开头
            set should_keep=0
            for /F "usebackq delims=" %%P in ("!protected_list!") do (
                echo !relpath! | findstr /B /C:"%%P" >nul 2>&1
                if not errorlevel 1 set should_keep=1
            )

            if !should_keep!==0 (
                del /F /Q "%%F" 2>nul
                if not errorlevel 1 (
                    echo   Deleted: !relpath!
                    set /a delete_count+=1
                )
            )
        )
    )
)

echo   Deleted !delete_count! obsolete files.

:cleanup
echo [5/5] Cleaning up update files...
rmdir /S /Q "%~dp0_update_temp" 2>nul
rmdir /S /Q "%~dp0_updates" 2>nul

echo.
echo ========================================
echo  Update complete! Starting new version...
echo ========================================
start "" "%~dp0endfield-essence-recognizer.exe"

timeout /t 1 /nobreak >nul
del "%~f0"
"""
    return script


def _generate_update_script_fallback(current_dir: Path, temp_dir: Path) -> str:
    """生成回退方案的批处理更新脚本（无 manifest 时使用）。

    保持与原始行为一致：硬编码删除列表 + xcopy 全量复制。

    Args:
        current_dir: 当前程序所在目录。
        temp_dir: 解压后的临时目录。

    Returns:
        批处理脚本内容。
    """
    return """@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

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


def _prepare_manifest_helper_files(temp_dir: Path, manifest: dict) -> None:
    """将 manifest 数据写入辅助文本文件，供批处理脚本读取。

    批处理脚本使用 findstr 逐行匹配，因此需要将文件列表和保护列表
    写为每行一个条目的纯文本文件。

    Args:
        temp_dir: 解压后的临时目录。
        manifest: manifest 字典。
    """
    files_path = temp_dir / "__manifest_files.txt"
    files_path.write_text(
        "\n".join(sorted(manifest["files"])) + "\n",
        encoding="utf-8",
    )

    protected_path = temp_dir / "__protected.txt"
    protected_path.write_text(
        "\n".join(sorted(manifest["protected"])) + "\n",
        encoding="utf-8",
    )


def install_update(zip_path: Path) -> bool:
    """安装更新。

    流程：
    1. 解压更新包到临时目录
    2. 读取 manifest.json（如果存在）
    3. 生成批处理更新脚本
    4. 启动脚本并退出当前程序

    Args:
        zip_path: 更新包路径。

    Returns:
        bool: 安装是否成功。
    """
    import zipfile

    try:
        # 获取当前程序目录
        if getattr(sys, "frozen", False):
            current_dir = Path(sys.executable).parent
        else:
            current_dir = Path.cwd()

        # 创建临时解压目录
        temp_dir = current_dir / "_update_temp"
        if temp_dir.exists():
            import shutil

            shutil.rmtree(temp_dir)
        temp_dir.mkdir()

        # 解压更新包
        logger.info(f"解压更新包到: {temp_dir}")
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            # 安全校验：拒绝路径穿越
            for member in zip_ref.namelist():
                member_path = (temp_dir / member).resolve()
                if not str(member_path).startswith(str(temp_dir.resolve())):
                    logger.error(f"拒绝可疑的 zip 条目（路径穿越）: {member}")
                    return False
            zip_ref.extractall(temp_dir)

        # 尝试加载 manifest
        manifest = _load_manifest(temp_dir)

        if manifest is not None:
            # Manifest 模式：基于文件列表的增量更新
            logger.info("使用 manifest 模式进行增量更新")
            _prepare_manifest_helper_files(temp_dir, manifest)
            script_content = _generate_update_script_manifest(
                current_dir, temp_dir, manifest
            )
        else:
            # 回退模式：兼容无 manifest 的旧版更新包
            logger.info("使用回退模式进行全量更新")
            script_content = _generate_update_script_fallback(current_dir, temp_dir)

        # 创建更新脚本
        updater_script = current_dir / "_updater.bat"
        updater_script.write_text(script_content, encoding="utf-8-sig")

        logger.info("启动更新脚本并退出程序")
        subprocess.Popen(
            ["cmd.exe", "/c", str(updater_script)],
            creationflags=subprocess.CREATE_NEW_CONSOLE,
        )

        # 延迟退出，确保响应返回给前端
        import threading

        def delayed_exit() -> None:
            import os
            import time

            time.sleep(1)
            os._exit(0)

        threading.Thread(target=delayed_exit, daemon=True).start()

        return True

    except Exception as exc:
        logger.error(f"安装更新失败: {exc}")
        return False
