"""生成更新包 manifest 文件。

在 PyInstaller 构建完成后运行此脚本，扫描 dist 目录并生成 manifest.json，
用于热更新时确定哪些文件应该新增 / 覆盖 / 删除。

用法：
    python scripts/generate_manifest.py [--dist-dir DIST_DIR] [--version VERSION]

如果不指定参数，默认扫描 dist/endfield-essence-recognizer/ 目录，
版本号从 pyproject.toml 中读取。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

# 用户数据目录 / 文件，更新时绝对不能删除
PROTECTED_PATHS: list[str] = [
    "config.json",
    "logs/",
    "screenshots/",
    "_updates/",
    "_update_temp/",
    "_updater.bat",
    ".env",
]


def scan_dist_directory(dist_dir: Path) -> list[str]:
    """扫描 dist 目录，返回所有文件的相对路径列表（使用正斜杠）。

    Args:
        dist_dir: PyInstaller 构建产物的根目录。

    Returns:
        排序后的文件相对路径列表。
    """
    if not dist_dir.is_dir():
        raise FileNotFoundError(f"dist 目录不存在: {dist_dir}")

    files: list[str] = []
    for path in dist_dir.rglob("*"):
        if path.is_file():
            relative = path.relative_to(dist_dir)
            # 统一使用正斜杠，避免 Windows 反斜杠问题
            files.append(str(relative).replace("\\", "/"))

    files.sort()
    return files


def read_version_from_pyproject(project_root: Path) -> str:
    """从 pyproject.toml 中读取项目版本号。

    Args:
        project_root: 项目根目录。

    Returns:
        版本号字符串。
    """
    pyproject_path = project_root / "pyproject.toml"
    if not pyproject_path.is_file():
        raise FileNotFoundError(f"pyproject.toml 不存在: {pyproject_path}")

    for line in pyproject_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("version") and "=" in stripped:
            # 解析 version = "0.8.0" 格式
            value = stripped.split("=", maxsplit=1)[1].strip().strip('"').strip("'")
            return value

    raise ValueError("pyproject.toml 中未找到 version 字段")


def generate_manifest(
    dist_dir: Path,
    version: str,
    protected_paths: list[str] | None = None,
) -> dict:
    """生成 manifest 字典。

    Args:
        dist_dir: PyInstaller 构建产物的根目录。
        version: 当前版本号。
        protected_paths: 受保护的路径列表（不参与清理），默认使用 PROTECTED_PATHS。

    Returns:
        manifest 字典。
    """
    if protected_paths is None:
        protected_paths = PROTECTED_PATHS

    files = scan_dist_directory(dist_dir)

    return {
        "version": version,
        "files": files,
        "protected": sorted(protected_paths),
    }


def main() -> None:
    """CLI 入口。"""
    parser = argparse.ArgumentParser(description="生成更新包 manifest 文件")
    parser.add_argument(
        "--dist-dir",
        type=Path,
        default=None,
        help="PyInstaller 构建产物目录（默认: dist/endfield-essence-recognizer）",
    )
    parser.add_argument(
        "--version",
        type=str,
        default=None,
        help="版本号（默认: 从 pyproject.toml 读取）",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="manifest.json 输出路径（默认: 写入 dist-dir/manifest.json）",
    )
    args = parser.parse_args()

    # 确定项目根目录（此脚本位于 scripts/ 下）
    project_root = Path(__file__).parent.parent.resolve()

    # 确定 dist 目录
    dist_dir = args.dist_dir or (project_root / "dist" / "endfield-essence-recognizer")
    dist_dir = dist_dir.resolve()

    # 确定版本号
    version = args.version or read_version_from_pyproject(project_root)

    print(f"项目根目录: {project_root}")
    print(f"dist 目录:   {dist_dir}")
    print(f"版本号:      {version}")

    # 生成 manifest
    manifest = generate_manifest(dist_dir, version)
    file_count = len(manifest["files"])
    protected_count = len(manifest["protected"])
    print(f"扫描到 {file_count} 个文件, {protected_count} 个受保护路径")

    # 输出
    output_path = args.output or (dist_dir / "manifest.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"manifest 已写入: {output_path}")

    # 打印摘要
    print("\n--- manifest 摘要 ---")
    print(f"  version:   {manifest['version']}")
    print(f"  files:     {file_count} 个")
    print(f"  protected: {manifest['protected']}")


if __name__ == "__main__":
    main()
