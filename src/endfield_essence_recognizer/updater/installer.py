"""更新安装模块

基于 manifest.json 实现增量更新：
- 新增：manifest 中有、本地没有的文件 → 复制
- 覆盖：manifest 中有、本地也有的文件 → 覆盖
- 删除：本地有、manifest 中没有、且不在 protected 列表中的文件 → 删除
- protected 保护"删除"和"覆盖"双重语义

manifest.json 存放在 ``_internal/manifest.json``，随更新包一起被复制到目标目录，
下次更新时作为"旧 manifest"被读取。
"""

from __future__ import annotations

import json
import subprocess
import sys
import threading
from pathlib import Path

from endfield_essence_recognizer.utils.log import logger

# manifest 在安装目录中的相对路径（与 generate_manifest.py 保持一致）
MANIFEST_RELATIVE_PATH = "_internal/manifest.json"

# updater 可执行文件名
UPDATER_EXE_NAME = "eer_updater.exe"

# 状态文件名
SUCCESS_STATUS_FILE = "_update_success.txt"
FAILURE_STATUS_FILE = "_update_failure.txt"


def _is_path_traversal(temp_dir: Path, member: str) -> bool:
    """检查 zip 条目是否存在路径穿越风险。

    使用 Path.relative_to() 做严格的路径归属判断，而非字符串前缀匹配，
    避免前缀碰撞绕过（如 temp_dir="/tmp/u" + member="../update_evil"）。

    Args:
        temp_dir: 解压目标目录（已 resolve）。
        member: zip 条目名称。

    Returns:
        True 表示存在穿越风险，应拒绝该条目。
    """
    resolved_temp = temp_dir.resolve()
    try:
        member_path = (resolved_temp / member).resolve()
        member_path.relative_to(resolved_temp)
        return False
    except ValueError:
        return True


def _load_manifest(temp_dir: Path) -> dict | None:
    """从解压目录中加载 manifest.json。

    读取 ``_internal/manifest.json``（新规范位置），同时兼容根目录 ``manifest.json``
    （旧版更新包回退）。

    Args:
        temp_dir: 解压后的临时目录。

    Returns:
        manifest 字典，如果文件不存在则返回 None。
    """
    # 优先尝试新位置 _internal/manifest.json
    manifest_path = temp_dir / MANIFEST_RELATIVE_PATH
    if not manifest_path.is_file():
        # 回退：旧版更新包把 manifest.json 放在根目录
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


def _is_protected(file_path: str, protected: set[str]) -> bool:
    """判断文件是否被 protected 列表保护（精确匹配或前缀目录匹配）。"""
    if file_path in protected:
        return True
    return any(file_path.startswith(p) for p in protected)


def _compute_delete_list(
    current_dir: Path,
    new_manifest: dict,
) -> list[str]:
    """基于旧 manifest 计算需要删除的文件列表。

    删除旧 manifest 中的所有文件（排除 protected），
    确保所有程序文件都会被新版本替换。

    如果没有旧 manifest（首次升级到 manifest 方案），则扫描磁盘上
    安装目录中的文件，删除那些"大概率是旧程序"的文件（.exe, .dll,
    .pyd, .pyz 等），但跳过 manifest 识别的新版本文件和 protected 文件。

    Args:
        current_dir: 当前程序所在目录。
        new_manifest: 新版本的 manifest 字典。

    Returns:
        需要删除的文件相对路径列表（正斜杠格式）。
    """
    protected = set(new_manifest["protected"])
    new_files = set(new_manifest["files"])

    # 读取旧 manifest
    old_manifest_path = current_dir / MANIFEST_RELATIVE_PATH
    # 兼容旧版：旧版 manifest.json 在根目录
    if not old_manifest_path.is_file():
        old_manifest_path = current_dir / "manifest.json"

    old_files: set[str] = set()
    if old_manifest_path.is_file():
        try:
            old_manifest = json.loads(old_manifest_path.read_text(encoding="utf-8"))
            old_files = set(old_manifest.get("files", []))
            logger.info(f"读取旧 manifest: {len(old_files)} 个文件")
        except Exception as exc:
            logger.warning(f"无法读取旧 manifest: {exc}")

    to_delete: list[str] = []

    if old_files:
        # 有旧 manifest：精确删除旧文件（排除 protected）
        for file in old_files:
            if not _is_protected(file, protected):
                to_delete.append(file)
    else:
        # 无旧 manifest（首次升级到 manifest 方案）：
        # 核心原则：不要删除用户本来就有的文件。
        # 此前版本的更新策略是"删文件夹+重新解压"，不需要额外兜底。
        # 只清理 manifest 中声明的目录内的旧程序文件残留（.exe/.dll/.pyd），
        # 确保 _internal 等目录干净即可，其他文件一律不动。
        _PROGRAM_EXTENSIONS = {".exe", ".dll", ".pyd", ".pyz", ".pyi"}

        # 从新 manifest 中提取涉及的目录前缀
        manifest_dirs: set[str] = set()
        for f in new_files:
            parts = f.split("/")
            for i in range(1, len(parts)):
                manifest_dirs.add("/".join(parts[:i]) + "/")

        for path in current_dir.rglob("*"):
            if not path.is_file():
                continue
            try:
                rel = str(path.relative_to(current_dir).as_posix())
            except ValueError:
                continue
            # 跳过 protected
            if _is_protected(rel, protected):
                continue
            # 跳过新 manifest 中的文件
            if rel in new_files:
                continue
            # 只清理 manifest 涉及目录下的旧程序文件（.exe/.dll/.pyd 等）
            in_manifest_dir = any(rel.startswith(d) for d in manifest_dirs)
            if in_manifest_dir and path.suffix.lower() in _PROGRAM_EXTENSIONS:
                to_delete.append(rel)
        logger.info(
            f"首次升级（无旧 manifest）：清理 manifest 目录下的旧程序文件残留，"
            f"共 {len(to_delete)} 个"
        )

    logger.info(f"生成删除清单: {len(to_delete)} 个文件")
    return sorted(to_delete)


def _compute_copy_list(manifest: dict) -> list[str]:
    """计算需要复制的文件列表（已排除 protected 和 .git 相关文件）。

    Args:
        manifest: manifest 字典。

    Returns:
        需要复制的文件相对路径列表（正斜杠格式）。
    """
    protected = set(manifest["protected"])
    copy_files = [
        f
        for f in manifest["files"]
        if not _is_protected(f, protected)
        and not f.startswith(".git")
        and "/.git" not in f
        and not f.startswith("resources/.git")
        and "/resources/.git" not in f
    ]
    return sorted(copy_files)


def _compute_protected_list(manifest: dict) -> list[str]:
    """计算 protected 文件列表（仅具体文件，排除目录条目）。

    Args:
        manifest: manifest 字典。

    Returns:
        protected 文件相对路径列表（正斜杠格式）。
    """
    return sorted(p for p in manifest["protected"] if not p.endswith("/"))


def _generate_plan_json(
    temp_dir: Path,
    package_type: str,
    remove_list: list[str],
    copy_list: list[str],
    protected_list: list[str],
) -> Path:
    """生成更新计划 JSON 文件。

    Args:
        temp_dir: 临时目录路径。
        package_type: 包类型（"manifest" 或 "fallback"）。
        remove_list: 需要删除的文件列表。
        copy_list: 需要复制的文件列表。
        protected_list: 受保护的文件列表。

    Returns:
        plan JSON 文件路径。
    """
    plan = {
        "package_type": package_type,
        "remove_list": remove_list,
        "copy_list": copy_list,
        "protected_list": protected_list,
    }
    plan_path = temp_dir / "_plan.json"
    plan_path.write_text(
        json.dumps(plan, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    logger.info(
        f"生成 plan JSON: remove={len(remove_list)}, "
        f"copy={len(copy_list)}, protected={len(protected_list)}"
    )
    return plan_path


def _compute_fallback_remove_list(current_dir: Path) -> list[str]:
    """无 manifest 时的回退删除列表。

    硬编码删除已知的程序目录和文件，与旧版 bat 脚本行为一致。

    Args:
        current_dir: 当前程序所在目录。

    Returns:
        需要删除的文件/目录相对路径列表。
    """
    to_delete = []
    known_items = [
        "endfield-essence-recognizer.exe",
        "_internal/",
        "resources/",
        "README.md",
        "界面白屏解决方法.md",
        "遇到报错解决方法.webp",
    ]
    for item in known_items:
        full_path = current_dir / item
        if full_path.exists():
            to_delete.append(item)
    return to_delete


def install_update(zip_path: Path) -> bool:
    """安装更新。

    流程：
    1. 解压更新包到临时目录（含路径穿越校验）
    2. 读取 manifest.json（``_internal/manifest.json`` 或根目录回退）
    3. 生成删除清单（有旧 manifest 则精确删除，无则保守清理旧程序文件）
    4. 生成复制清单（已排除 protected）
    5. 生成 protected 备份清单
    6. 生成 plan JSON 文件
    7. 启动 eer_updater.exe 并退出当前程序

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
            # 安全校验：使用 Path.relative_to() 拒绝路径穿越
            for member in zip_ref.namelist():
                if _is_path_traversal(temp_dir, member):
                    logger.error(f"拒绝可疑的 zip 条目（路径穿越）: {member}")
                    return False
            zip_ref.extractall(temp_dir)

        # 尝试加载 manifest
        manifest = _load_manifest(temp_dir)

        if manifest is not None:
            # Manifest 模式：精确删除 + 排除 protected 的复制
            logger.info("使用 manifest 模式进行更新")
            remove_list = _compute_delete_list(current_dir, manifest)
            copy_list = _compute_copy_list(manifest)
            protected_list = _compute_protected_list(manifest)
            plan_path = _generate_plan_json(
                temp_dir, "manifest", remove_list, copy_list, protected_list
            )
        else:
            # 回退模式：兼容无 manifest 的旧版更新包
            logger.info("使用回退模式进行全量更新")
            remove_list = _compute_fallback_remove_list(current_dir)
            # 回退模式下，复制 temp_dir 中的所有文件
            copy_list = [
                str(p.relative_to(temp_dir).as_posix())
                for p in temp_dir.rglob("*")
                if p.is_file() and p.name != "_plan.json"
            ]
            protected_list = ["config.json", ".env"]
            plan_path = _generate_plan_json(
                temp_dir, "fallback", remove_list, copy_list, protected_list
            )

        # 优先运行更新包内的新 updater，使 updater 本身可以被替换。
        packaged_updater = temp_dir / UPDATER_EXE_NAME
        updater_exe = packaged_updater if packaged_updater.is_file() else current_dir / UPDATER_EXE_NAME
        if not updater_exe.is_file():
            logger.error(f"未找到更新器: {updater_exe}")
            return False

        # 构造命令行参数
        main_exe = current_dir / "endfield-essence-recognizer.exe"
        success_file = current_dir / SUCCESS_STATUS_FILE
        failure_file = current_dir / FAILURE_STATUS_FILE

        args = [
            str(updater_exe),
            str(subprocess.os.getpid()),  # ParentPid
            str(current_dir),  # RootDir
            str(temp_dir),  # ExtractDir
            str(zip_path),  # PackagePath
            str(success_file),  # SuccessStatusFile
            str(failure_file),  # FailureStatusFile
            str(main_exe),  # RelaunchExecutable
            str(plan_path),  # PlanFile
        ]

        logger.info(f"启动更新器: {updater_exe}")
        logger.info(f"参数: RootDir={current_dir}, PlanFile={plan_path}")

        subprocess.Popen(
            args,
            creationflags=subprocess.CREATE_NEW_CONSOLE,
        )

        # 延迟退出，确保响应返回给前端
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
