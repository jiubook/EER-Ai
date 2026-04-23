"""账号管理器服务的测试。"""

from pathlib import Path

import pytest

from endfield_essence_recognizer.schemas.profile import (
    TreasureMatrixEntry,
)
from endfield_essence_recognizer.services.profile_manager import ProfileManager


@pytest.fixture
def temp_profiles_file(tmp_path: Path) -> Path:
    """创建临时账号配置文件路径。"""
    return tmp_path / "profiles.json"


@pytest.fixture
def profile_manager(temp_profiles_file: Path) -> ProfileManager:
    """创建使用临时文件的 ProfileManager 实例。"""
    return ProfileManager(temp_profiles_file)


def test_profile_manager_init(profile_manager: ProfileManager):
    """测试 ProfileManager 初始化。"""
    assert profile_manager is not None


def test_load_creates_default_profile(profile_manager: ProfileManager):
    """测试 load() 在文件不存在时创建默认账号。"""
    profile_manager.load()
    collection = profile_manager.get_collection()
    assert "default" in collection.profiles
    assert collection.active_profile == "default"


def test_switch_profile_creates_new(profile_manager: ProfileManager):
    """测试切换到不存在的账号会创建它。"""
    profile_manager.load()
    profile = profile_manager.switch_profile("test_account")
    assert profile.name == "test_account"
    assert profile_manager.get_active_profile_name() == "test_account"


def test_validate_profile_name_empty():
    """测试空账号名称会被拒绝。"""
    with pytest.raises(ValueError, match="账号名称不能为空"):
        ProfileManager._validate_profile_name("")
    with pytest.raises(ValueError, match="账号名称不能为空"):
        ProfileManager._validate_profile_name("   ")


def test_validate_profile_name_too_long():
    """测试超过 32 个字符的账号名称会被拒绝。"""
    with pytest.raises(ValueError, match="账号名称不能超过 32 个字符"):
        ProfileManager._validate_profile_name("a" * 33)


def test_validate_profile_name_forbidden_chars():
    """测试包含禁止字符的账号名称会被拒绝。"""
    forbidden = ["/", "\\", "\x00", "\n", "\r", "\t"]
    for char in forbidden:
        with pytest.raises(ValueError, match="账号名称包含非法字符"):
            ProfileManager._validate_profile_name(f"test{char}name")


def test_rename_profile(profile_manager: ProfileManager):
    """测试重命名账号。"""
    profile_manager.load()
    profile_manager.switch_profile("old_name")
    profile = profile_manager.rename_profile("old_name", "new_name")
    assert profile.name == "new_name"
    assert "new_name" in profile_manager.get_collection().profiles
    assert "old_name" not in profile_manager.get_collection().profiles
    assert profile_manager.get_active_profile_name() == "new_name"


def test_rename_nonexistent_profile(profile_manager: ProfileManager):
    """测试重命名不存在的账号会抛出 ValueError。"""
    profile_manager.load()
    with pytest.raises(ValueError, match="不存在"):
        profile_manager.rename_profile("nonexistent", "new_name")


def test_rename_to_existing_name(profile_manager: ProfileManager):
    """测试重命名为已存在的名称会抛出 ValueError。"""
    profile_manager.load()
    profile_manager.switch_profile("profile1")
    profile_manager.switch_profile("profile2")
    with pytest.raises(ValueError, match="已存在"):
        profile_manager.rename_profile("profile1", "profile2")


def test_delete_profile(profile_manager: ProfileManager):
    """测试删除账号。"""
    profile_manager.load()
    profile_manager.switch_profile("to_delete")
    profile_manager.switch_profile("default")
    profile_manager.delete_profile("to_delete")
    assert "to_delete" not in profile_manager.get_collection().profiles


def test_delete_default_profile(profile_manager: ProfileManager):
    """测试删除默认账号是被禁止的。"""
    profile_manager.load()
    with pytest.raises(ValueError, match="不能删除默认账号"):
        profile_manager.delete_profile("default")


def test_delete_active_profile(profile_manager: ProfileManager):
    """测试删除激活的账号是被禁止的。"""
    profile_manager.load()
    profile_manager.switch_profile("active")
    with pytest.raises(ValueError, match="不能删除当前正在使用的账号"):
        profile_manager.delete_profile("active")


def test_treasure_matrix_operations(profile_manager: ProfileManager):
    """测试宝藏基质的 CRUD 操作。"""
    profile_manager.load()
    entry1 = TreasureMatrixEntry(
        weapon_id="wpn_001",
        weapon_name="Test Weapon 1",
        affix1_level=3,
        affix2_level=4,
        affix3_level=2,
    )
    entry2 = TreasureMatrixEntry(
        weapon_id="wpn_002",
        weapon_name="Test Weapon 2",
        affix1_level=5,
        affix2_level=6,
        affix3_level=3,
    )

    # 添加条目
    profile_manager.add_treasure_matrix_entry(entry1)
    profile_manager.add_treasure_matrix_entry(entry2)
    matrix = profile_manager.get_active_profile().treasure_matrix
    assert len(matrix) == 2

    # 更新现有条目
    entry1_updated = TreasureMatrixEntry(
        weapon_id="wpn_001",
        weapon_name="Test Weapon 1 Updated",
        affix1_level=6,
        affix2_level=6,
        affix3_level=3,
    )
    profile_manager.add_treasure_matrix_entry(entry1_updated)
    matrix = profile_manager.get_active_profile().treasure_matrix
    assert len(matrix) == 2
    updated = next(e for e in matrix if e.weapon_id == "wpn_001")
    assert updated.affix1_level == 6

    # 移除条目
    profile_manager.remove_treasure_matrix_entry("wpn_001")
    matrix = profile_manager.get_active_profile().treasure_matrix
    assert len(matrix) == 1
    assert matrix[0].weapon_id == "wpn_002"


def test_persistence(temp_profiles_file: Path):
    """测试账号配置持久化到磁盘。"""
    manager1 = ProfileManager(temp_profiles_file)
    manager1.load()
    manager1.switch_profile("test")
    manager1.add_treasure_matrix_entry(
        TreasureMatrixEntry(weapon_id="wpn_001", weapon_name="Test")
    )

    # 创建新管理器并从同一文件加载
    manager2 = ProfileManager(temp_profiles_file)
    manager2.load()
    assert manager2.get_active_profile_name() == "test"
    assert len(manager2.get_active_profile().treasure_matrix) == 1
