"""更新安装器和 manifest 生成的测试。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# 将项目根目录加入 sys.path，以便导入 scripts 模块
_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.resolve()
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from scripts.generate_manifest import (  # noqa: E402
    PROTECTED_PATHS,
    generate_manifest,
    scan_dist_directory,
)


@pytest.fixture()
def fake_dist_dir(tmp_path: Path) -> Path:
    """创建一个模拟的 dist 目录结构。"""
    dist = tmp_path / "endfield-essence-recognizer"
    dist.mkdir()

    # 模拟典型 PyInstaller 输出
    (dist / "endfield-essence-recognizer.exe").write_text("exe")
    internal = dist / "_internal"
    internal.mkdir()
    (internal / "python3.dll").write_text("dll")
    (internal / "cv2").mkdir()
    (internal / "cv2" / "cv2.pyd").write_text("pyd")

    resources = dist / "resources"
    resources.mkdir()
    (resources / "images").mkdir()
    (resources / "images" / "error.webp").write_text("webp")

    (dist / "README.md").write_text("readme")
    (dist / "config.json").write_text("{}")  # 用户配置，应该被 protected

    return dist


class TestScanDistDirectory:
    """扫描 dist 目录的测试。"""

    def test_scan_returns_all_files(self, fake_dist_dir: Path) -> None:
        """应返回目录中所有文件的相对路径。"""
        files = scan_dist_directory(fake_dist_dir)
        assert "endfield-essence-recognizer.exe" in files
        assert "_internal/python3.dll" in files
        assert "_internal/cv2/cv2.pyd" in files
        assert "resources/images/error.webp" in files
        assert "README.md" in files
        assert "config.json" in files

    def test_scan_uses_forward_slashes(self, fake_dist_dir: Path) -> None:
        """路径应统一使用正斜杠。"""
        files = scan_dist_directory(fake_dist_dir)
        for file_path in files:
            assert "\\" not in file_path, f"路径包含反斜杠: {file_path}"

    def test_scan_sorted_output(self, fake_dist_dir: Path) -> None:
        """输出应按字母顺序排序。"""
        files = scan_dist_directory(fake_dist_dir)
        assert files == sorted(files)

    def test_scan_nonexistent_dir_raises(self, tmp_path: Path) -> None:
        """不存在的目录应抛出异常。"""
        with pytest.raises(FileNotFoundError):
            scan_dist_directory(tmp_path / "nonexistent")


class TestGenerateManifest:
    """生成 manifest 的测试。"""

    def test_manifest_structure(self, fake_dist_dir: Path) -> None:
        """manifest 应包含 version、files、protected 三个字段。"""
        manifest = generate_manifest(fake_dist_dir, "1.0.0")
        assert "version" in manifest
        assert "files" in manifest
        assert "protected" in manifest

    def test_manifest_version(self, fake_dist_dir: Path) -> None:
        """版本号应与传入参数一致。"""
        manifest = generate_manifest(fake_dist_dir, "2.3.4")
        assert manifest["version"] == "2.3.4"

    def test_manifest_files_count(self, fake_dist_dir: Path) -> None:
        """文件数量应匹配实际文件数。"""
        manifest = generate_manifest(fake_dist_dir, "1.0.0")
        assert len(manifest["files"]) == 6

    def test_manifest_protected_defaults(self, fake_dist_dir: Path) -> None:
        """默认应使用 PROTECTED_PATHS 作为保护列表。"""
        manifest = generate_manifest(fake_dist_dir, "1.0.0")
        assert manifest["protected"] == sorted(PROTECTED_PATHS)
        assert "config.json" in manifest["protected"]
        assert "logs/" in manifest["protected"]

    def test_manifest_custom_protected(self, fake_dist_dir: Path) -> None:
        """应支持自定义保护列表。"""
        custom = ["my_data.json", "custom_dir/"]
        manifest = generate_manifest(fake_dist_dir, "1.0.0", protected_paths=custom)
        assert manifest["protected"] == sorted(custom)

    def test_manifest_json_serializable(self, fake_dist_dir: Path) -> None:
        """manifest 应可序列化为 JSON。"""
        manifest = generate_manifest(fake_dist_dir, "1.0.0")
        text = json.dumps(manifest, ensure_ascii=False)
        restored = json.loads(text)
        assert restored == manifest


class TestProtectedPaths:
    """受保护路径的测试。"""

    def test_config_json_is_protected(self) -> None:
        """config.json 必须在保护列表中。"""
        assert "config.json" in PROTECTED_PATHS

    def test_logs_dir_is_protected(self) -> None:
        """logs/ 目录必须在保护列表中。"""
        assert "logs/" in PROTECTED_PATHS

    def test_screenshots_dir_is_protected(self) -> None:
        """screenshots/ 目录必须在保护列表中。"""
        assert "screenshots/" in PROTECTED_PATHS


class TestDeleteListGeneration:
    """删除清单生成的测试。"""

    def test_delete_all_old_files_except_protected(self, tmp_path: Path) -> None:
        """应删除旧 manifest 中的所有文件（排除 protected）。"""
        from src.endfield_essence_recognizer.updater.installer import (
            _prepare_delete_list,
        )

        # 创建旧 manifest
        current_dir = tmp_path / "current"
        current_dir.mkdir()
        old_manifest = {
            "version": "0.8.0",
            "files": ["app.exe", "old.dll", "lib.pyd", "config.json"],
            "protected": ["config.json", "logs/"],
        }
        (current_dir / "manifest.json").write_text(
            json.dumps(old_manifest), encoding="utf-8"
        )

        # 新 manifest
        temp_dir = tmp_path / "temp"
        temp_dir.mkdir()
        new_manifest = {
            "version": "0.9.0",
            "files": ["app.exe", "new.dll", "lib.pyd"],
            "protected": ["config.json", "logs/"],
        }

        # 生成删除清单
        _prepare_delete_list(current_dir, temp_dir, new_manifest)

        # 读取删除清单
        delete_list = (temp_dir / "__to_delete.txt").read_text(encoding="utf-8")
        deleted_files = [line for line in delete_list.strip().split("\n") if line]

        # 验证：应删除所有旧文件（排除 protected）
        assert "app.exe" in deleted_files
        assert "old.dll" in deleted_files
        assert "lib.pyd" in deleted_files
        assert "config.json" not in deleted_files  # protected

    def test_no_old_manifest_generates_empty_list(self, tmp_path: Path) -> None:
        """首次安装（无旧 manifest）应生成空删除清单。"""
        from src.endfield_essence_recognizer.updater.installer import (
            _prepare_delete_list,
        )

        current_dir = tmp_path / "current"
        current_dir.mkdir()
        # 没有旧 manifest

        temp_dir = tmp_path / "temp"
        temp_dir.mkdir()
        new_manifest = {
            "version": "0.9.0",
            "files": ["app.exe", "new.dll"],
            "protected": ["config.json"],
        }

        _prepare_delete_list(current_dir, temp_dir, new_manifest)

        delete_list = (temp_dir / "__to_delete.txt").read_text(encoding="utf-8")
        assert delete_list.strip() == ""

    def test_protected_prefix_matching(self, tmp_path: Path) -> None:
        """protected 目录下的文件应被保护（前缀匹配）。"""
        from src.endfield_essence_recognizer.updater.installer import (
            _prepare_delete_list,
        )

        current_dir = tmp_path / "current"
        current_dir.mkdir()
        old_manifest = {
            "version": "0.8.0",
            "files": ["app.exe", "logs/app.log", "logs/error.log"],
            "protected": ["logs/"],
        }
        (current_dir / "manifest.json").write_text(
            json.dumps(old_manifest), encoding="utf-8"
        )

        temp_dir = tmp_path / "temp"
        temp_dir.mkdir()
        new_manifest = {
            "version": "0.9.0",
            "files": ["app.exe"],
            "protected": ["logs/"],
        }

        _prepare_delete_list(current_dir, temp_dir, new_manifest)

        delete_list = (temp_dir / "__to_delete.txt").read_text(encoding="utf-8")
        deleted_files = [line for line in delete_list.strip().split("\n") if line]

        # logs/ 下的文件应被保护
        assert "app.exe" in deleted_files
        assert "logs/app.log" not in deleted_files
        assert "logs/error.log" not in deleted_files
