"""账号管理器服务的测试。"""

from pathlib import Path

import pytest

from endfield_essence_recognizer.schemas.profile import (
    TreasureMatrixEntry,
)
from endfield_essence_recognizer.services import (
    profile_manager as profile_manager_module,
)
from endfield_essence_recognizer.services.profile_manager import (
    ProfileLoadError,
    ProfileManager,
    ProfileSaveError,
)


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


def test_load_corrupted_profiles_does_not_overwrite_existing_file(
    temp_profiles_file: Path,
):
    """损坏的账号配置不能被默认配置静默覆盖。"""
    temp_profiles_file.write_text("{bad json", encoding="utf-8")

    manager = ProfileManager(temp_profiles_file)

    with pytest.raises(ProfileLoadError):
        manager.load()

    broken_files = list(temp_profiles_file.parent.glob("profiles.json.broken*"))
    assert broken_files
    assert broken_files[0].read_text(encoding="utf-8") == "{bad json"
    assert not temp_profiles_file.exists()


def test_save_failure_does_not_update_in_memory_collection(
    profile_manager: ProfileManager, monkeypatch: pytest.MonkeyPatch
):
    """保存失败时不能让内存状态伪装成已经切换成功。"""
    profile_manager.load()

    def fake_save(*args, **kwargs):
        raise ProfileSaveError("disk full")

    monkeypatch.setattr(profile_manager_module, "_save_profiles_to_file", fake_save)

    with pytest.raises(ProfileSaveError):
        profile_manager.switch_profile("new_account")

    assert profile_manager.get_active_profile_name() == "default"
    assert "new_account" not in profile_manager.get_collection().profiles


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


def test_update_weapon_priority_without_matrix(profile_manager: ProfileManager):
    """测试未拥有宝藏基质的武器也可以保存优先级。"""
    profile_manager.load()

    profile = profile_manager.update_weapon_priority("wpn_003", 7)
    assert profile.weapon_priorities["wpn_003"] == 7
    assert profile.treasure_matrix == []

    profile = profile_manager.update_weapon_priority("wpn_003", 0)
    assert "wpn_003" not in profile.weapon_priorities


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


def test_sync_treasure_matrix_entries_saves_once(
    profile_manager: ProfileManager, monkeypatch: pytest.MonkeyPatch
):
    """批量同步多把新武器时，只执行一次持久化。"""
    profile_manager.load()
    save_count = 0

    def fake_save(*args, **kwargs):
        nonlocal save_count
        save_count += 1
        return True

    monkeypatch.setattr(profile_manager_module, "_save_profiles_to_file", fake_save)

    result = profile_manager.sync_treasure_matrix_entries(
        [
            TreasureMatrixEntry(weapon_id="wpn_001", weapon_name="Weapon 1"),
            TreasureMatrixEntry(weapon_id="wpn_002", weapon_name="Weapon 2"),
            TreasureMatrixEntry(weapon_id="wpn_003", weapon_name="Weapon 3"),
        ]
    )

    assert [entry.weapon_id for entry in result.added] == [
        "wpn_001",
        "wpn_002",
        "wpn_003",
    ]
    assert result.updated == []
    assert save_count == 1
    assert len(profile_manager.get_active_profile().treasure_matrix) == 3


def test_sync_treasure_matrix_entries_updates_only_higher_levels(
    profile_manager: ProfileManager, monkeypatch: pytest.MonkeyPatch
):
    """扫描同步只提升等级，不用较低扫描结果覆盖用户已有数据。"""
    profile_manager.load()
    profile_manager.add_treasure_matrix_entry(
        TreasureMatrixEntry(
            weapon_id="wpn_001",
            weapon_name="Weapon 1",
            affix1_level=3,
            affix2_level=3,
            affix3_level=2,
            include_in_calculation=True,
        )
    )
    save_count = 0

    def fake_save(*args, **kwargs):
        nonlocal save_count
        save_count += 1
        return True

    monkeypatch.setattr(profile_manager_module, "_save_profiles_to_file", fake_save)

    no_change = profile_manager.sync_treasure_matrix_entries(
        [
            TreasureMatrixEntry(
                weapon_id="wpn_001",
                weapon_name="Weapon 1",
                affix1_level=2,
                affix2_level=3,
                affix3_level=1,
            )
        ]
    )
    assert no_change.added == []
    assert no_change.updated == []
    assert save_count == 0

    changed = profile_manager.sync_treasure_matrix_entries(
        [
            TreasureMatrixEntry(
                weapon_id="wpn_001",
                weapon_name="Weapon 1",
                affix1_level=6,
                affix2_level=6,
                affix3_level=3,
            )
        ]
    )

    entry = profile_manager.get_active_profile().treasure_matrix[0]
    assert changed.added == []
    assert [updated.weapon_id for updated in changed.updated] == ["wpn_001"]
    assert (entry.affix1_level, entry.affix2_level, entry.affix3_level) == (6, 6, 3)
    assert entry.include_in_calculation is False
    assert save_count == 1


def test_clear_profile_data_active(profile_manager: ProfileManager):
    """清空激活账号：treasure_matrix 与 weapon_priorities 清空，其它保留。"""
    profile_manager.load()
    profile_manager.add_treasure_matrix_entry(
        TreasureMatrixEntry(weapon_id="wpn_001", weapon_name="W1", affix1_level=3)
    )
    profile_manager.update_weapon_priority("wpn_001", 5)
    profile_manager.update_weapon_overview_filters(
        {"3star": False, "4star": True, "5star": True, "6star": True, "custom": True}
    )

    cleared = profile_manager.clear_profile_data()

    assert cleared.treasure_matrix == []
    assert cleared.weapon_priorities == {}
    # 展示偏好（过滤器）、名称与版本保留
    assert cleared.weapon_overview_filters["3star"] is False
    assert cleared.name == "default"
    assert cleared.version == 1


def test_clear_profile_data_named_keeps_active(profile_manager: ProfileManager):
    """按名清空非激活账号时，不改变当前激活账号。"""
    profile_manager.load()
    # 给 default 加数据
    profile_manager.add_treasure_matrix_entry(
        TreasureMatrixEntry(weapon_id="wpn_default", weapon_name="D", affix1_level=2)
    )
    # 切换到 alt 并加数据
    profile_manager.switch_profile("alt")
    profile_manager.add_treasure_matrix_entry(
        TreasureMatrixEntry(weapon_id="wpn_alt", weapon_name="A", affix1_level=4)
    )

    cleared = profile_manager.clear_profile_data("default")

    assert cleared.name == "default"
    assert cleared.treasure_matrix == []
    # 激活账号仍为 alt，且其数据未受影响
    assert profile_manager.get_active_profile_name() == "alt"
    alt = profile_manager.get_collection().profiles["alt"]
    assert [e.weapon_id for e in alt.treasure_matrix] == ["wpn_alt"]


def test_clear_profile_data_nonexistent(profile_manager: ProfileManager):
    """清空不存在的账号会抛出 ValueError。"""
    profile_manager.load()
    with pytest.raises(ValueError, match="不存在"):
        profile_manager.clear_profile_data("no_such_profile")


def test_clear_profile_data_save_failure_keeps_memory(
    profile_manager: ProfileManager, monkeypatch: pytest.MonkeyPatch
):
    """保存失败时内存数据不能被清空。"""
    profile_manager.load()
    profile_manager.add_treasure_matrix_entry(
        TreasureMatrixEntry(weapon_id="wpn_001", weapon_name="W1", affix1_level=3)
    )

    def fake_save(*args, **kwargs):
        raise ProfileSaveError("disk full")

    monkeypatch.setattr(profile_manager_module, "_save_profiles_to_file", fake_save)

    with pytest.raises(ProfileSaveError):
        profile_manager.clear_profile_data()

    entries = profile_manager.get_active_profile().treasure_matrix
    assert [e.weapon_id for e in entries] == ["wpn_001"]
