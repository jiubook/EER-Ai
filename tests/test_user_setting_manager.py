import json

import pytest
from pydantic import ValidationError

from endfield_essence_recognizer.exceptions import ConfigVersionMismatchError
from endfield_essence_recognizer.schemas.user_setting import UserSetting
from endfield_essence_recognizer.services.user_setting_manager import (
    UserSettingManager,
)


@pytest.fixture
def settings_file(tmp_path):
    return tmp_path / "settings.json"


@pytest.fixture
def manager(settings_file):
    return UserSettingManager(settings_file)


def test_manager_initial_state(manager, settings_file):
    """Test the initial state of the UserSettingManager."""
    assert manager._user_setting_file == settings_file
    assert isinstance(manager.get_user_setting(), UserSetting)


def test_get_user_setting_returns_copy(manager):
    """Test that get_user_setting returns a deep copy of the settings."""
    s1 = manager.get_user_setting()
    s2 = manager.get_user_setting()
    assert s1 == s2
    assert s1 is not s2


def test_load_user_setting_file_not_exists(manager, settings_file):
    """Test that loading from a non-existent file creates a default setting file."""
    assert not settings_file.exists()
    manager.load_user_setting()
    assert settings_file.exists()
    # Should be default settings
    assert manager.get_user_setting().trash_weapon_ids == []


def test_load_user_setting_valid_file(manager, settings_file):
    """Test that a valid setting file is correctly loaded into memory."""
    data = {
        "version": UserSetting._VERSION,
        "trash_weapon_ids": ["weapon_1"],
        "treasure_essence_stats": [
            {"attribute": "atk", "secondary": "crit", "skill": None}
        ],
    }
    settings_file.write_text(json.dumps(data), encoding="utf-8")

    manager.load_user_setting()
    setting = manager.get_user_setting()
    assert setting.trash_weapon_ids == ["weapon_1"]
    assert len(setting.treasure_essence_stats) == 1
    assert setting.treasure_essence_stats[0].attribute == "atk"


def test_load_user_setting_invalid_version_backups_file(manager, settings_file):
    """Test that a file with an invalid version is backed up and replaced with defaults."""
    data = {
        "version": -1,  # Wrong version
        "trash_weapon_ids": ["old_weapon"],
    }
    settings_file.write_text(json.dumps(data), encoding="utf-8")

    manager.load_user_setting()

    # Check backup exists (with timestamp)
    backup_files = list(settings_file.parent.glob("settings.backup.*.json"))
    assert len(backup_files) == 1
    backup_file = backup_files[0]
    assert json.loads(backup_file.read_text(encoding="utf-8"))["trash_weapon_ids"] == [
        "old_weapon"
    ]

    # Current setting should be default
    assert manager.get_user_setting().trash_weapon_ids == []
    # New file should be saved with defaults
    assert settings_file.exists()
    assert (
        json.loads(settings_file.read_text(encoding="utf-8"))["version"]
        == UserSetting._VERSION
    )


def test_load_user_setting_corrupt_json_backups_file(manager, settings_file):
    """Test that a corrupt JSON file is backed up and replaced with defaults."""
    settings_file.write_text("not a json", encoding="utf-8")

    manager.load_user_setting()

    # Check backup exists (with timestamp)
    backup_files = list(settings_file.parent.glob("settings.backup.*.json"))
    assert len(backup_files) == 1
    backup_file = backup_files[0]
    assert backup_file.read_text(encoding="utf-8") == "not a json"

    assert manager.get_user_setting().version == UserSetting._VERSION


def test_update_from_dict_version_mismatch(manager):
    """Test that update_from_dict raises ConfigVersionMismatchError on version mismatch."""
    data = {"version": -1, "trash_weapon_ids": ["test"]}
    with pytest.raises(ConfigVersionMismatchError) as excinfo:
        manager.update_from_dict(data)
    assert excinfo.value.expected == UserSetting._VERSION
    assert excinfo.value.got == -1


def test_update_from_user_setting_version_mismatch(manager):
    """Test that update_from_user_setting raises ConfigVersionMismatchError on version mismatch."""
    other = UserSetting()
    other.version = -1
    with pytest.raises(ConfigVersionMismatchError) as excinfo:
        manager.update_from_user_setting(other)
    assert excinfo.value.expected == UserSetting._VERSION
    assert excinfo.value.got == -1


def test_save_user_setting(manager, settings_file):
    """Test that save_user_setting correctly persists in-memory settings to disk."""
    # Accessing private member for test setup
    setting = manager._user_setting
    setting.trash_weapon_ids = ["test_save"]
    manager.save_user_setting()

    assert settings_file.exists()
    data = json.loads(settings_file.read_text(encoding="utf-8"))
    assert data["trash_weapon_ids"] == ["test_save"]


def test_update_from_dict(manager, settings_file):
    """Test that update_from_dict updates settings and saves to disk."""
    manager.update_from_dict({"trash_weapon_ids": ["dict_update"]})
    assert manager.get_user_setting().trash_weapon_ids == ["dict_update"]
    assert json.loads(settings_file.read_text(encoding="utf-8"))[
        "trash_weapon_ids"
    ] == ["dict_update"]


def test_update_from_user_setting(manager, settings_file):
    """Test that update_from_user_setting updates settings and saves to disk."""
    new_setting = UserSetting(trash_weapon_ids=["model_update"])
    manager.update_from_user_setting(new_setting)
    assert manager.get_user_setting().trash_weapon_ids == ["model_update"]
    assert json.loads(settings_file.read_text(encoding="utf-8"))[
        "trash_weapon_ids"
    ] == ["model_update"]


def test_update_from_dict_invalid_data(manager):
    """Test that update_from_dict raises an exception when provided with invalid data."""
    with pytest.raises(ValidationError):
        manager.update_from_dict({"trash_weapon_ids": "not a list"})


def test_config_migration_from_v3_to_current():
    """测试从 v3 迁移到当前版本"""
    old_config = {
        "version": 3,
        "trash_weapon_ids": ["weapon_1"],
        "treasure_essence_stats": [],
        "treasure_action": "lock",
        "trash_action": "unlock",
        "non_five_star_behavior": "process",
        "high_level_treasure_enabled": False,
        "high_level_treasure_attribute_threshold": 3,
        "high_level_treasure_secondary_threshold": 3,
        "high_level_treasure_skill_threshold": 3,
        "auto_page_flip": True,
        # v3 没有 update_mirror 和 update_proxy
    }

    migrated = UserSetting.migrate_from_old_version(old_config)

    # 验证旧数据保留
    assert migrated.trash_weapon_ids == ["weapon_1"]
    assert migrated.auto_page_flip is True
    # 验证新字段有默认值
    assert migrated.update_mirror == "github"
    assert migrated.update_proxy == ""
    assert migrated.treasure_essence_match_mode == "all"
    assert migrated.high_level_treasure_match_mode == "any"
    assert migrated.high_level_treasure_only_check_attribute is True
    assert migrated.high_level_treasure_only_check_secondary is True
    assert migrated.high_level_treasure_only_check_skill is True
    assert migrated.same_type_treasure_limit_enabled is False
    assert migrated.same_type_treasure_limit == 1
    # 验证版本更新
    assert migrated.version == UserSetting._VERSION


def test_config_migration_invalid_version():
    """测试无效版本号迁移失败"""
    from endfield_essence_recognizer.schemas.user_setting import UserSetting

    # 负数版本
    with pytest.raises(ValueError, match="无效的配置版本"):
        UserSetting.migrate_from_old_version({"version": -1})

    # 未来版本
    with pytest.raises(ValueError, match="配置文件版本过高"):
        UserSetting.migrate_from_old_version({"version": 999})


def test_load_user_setting_with_migration(manager, settings_file):
    """测试加载旧版本配置时自动迁移"""
    old_config = {
        "version": 3,
        "trash_weapon_ids": ["old_weapon"],
        "treasure_essence_stats": [],
        "treasure_action": "lock",
        "trash_action": "unlock",
        "non_five_star_behavior": "process",
        "high_level_treasure_enabled": False,
        "high_level_treasure_attribute_threshold": 3,
        "high_level_treasure_secondary_threshold": 3,
        "high_level_treasure_skill_threshold": 3,
        "auto_page_flip": True,
    }
    settings_file.write_text(json.dumps(old_config), encoding="utf-8")

    manager.load_user_setting()

    # 验证迁移成功
    setting = manager.get_user_setting()
    assert setting.version == UserSetting._VERSION
    assert setting.trash_weapon_ids == ["old_weapon"]
    assert setting.update_mirror == "github"
    assert setting.update_proxy == ""

    # 验证新版本已保存到文件
    saved_data = json.loads(settings_file.read_text(encoding="utf-8"))
    assert saved_data["version"] == UserSetting._VERSION
    assert saved_data["update_mirror"] == "github"


def test_user_setting_schema_stability():
    """检测 UserSetting schema 变更，提醒开发者更新迁移逻辑"""
    expected_fields = {
        "version",
        "trash_weapon_ids",
        "treasure_essence_stats",
        "treasure_essence_match_mode",
        "treasure_action",
        "trash_action",
        "non_five_star_behavior",
        "high_level_treasure_enabled",
        "high_level_treasure_attribute_threshold",
        "high_level_treasure_secondary_threshold",
        "high_level_treasure_skill_threshold",
        "high_level_treasure_match_mode",
        "high_level_treasure_only_check_attribute",
        "high_level_treasure_only_check_secondary",
        "high_level_treasure_only_check_skill",
        "same_type_treasure_limit_enabled",
        "same_type_treasure_limit",
        "auto_page_flip",
        "update_mirror",
        "update_proxy",
    }

    actual_fields = set(UserSetting.model_fields.keys())

    # 如果字段变化，测试失败并提示
    assert actual_fields == expected_fields, (
        f"UserSetting schema 已变更！\n"
        f"新增字段: {actual_fields - expected_fields}\n"
        f"删除字段: {expected_fields - actual_fields}\n"
        f"请执行以下步骤：\n"
        f"1. 更新 UserSetting._VERSION\n"
        f"2. 在 migrate_from_old_version() 添加迁移逻辑\n"
        f"3. 添加对应的迁移测试\n"
        f"4. 更新此测试的 expected_fields"
    )


def test_config_migration_chain_v2_to_current():
    """测试跨版本链式迁移：v2 → 当前版本（早期 v2，缺少后期新增字段）"""
    early_v2_config = {
        "version": 2,
        "trash_weapon_ids": ["weapon_v2"],
        "treasure_essence_stats": [],
        "treasure_action": "lock",
        "trash_action": "unlock",
        "high_level_treasure_enabled": False,
        "high_level_treasure_attribute_threshold": 3,
        "high_level_treasure_secondary_threshold": 3,
        "high_level_treasure_skill_threshold": 3,
        # 早期 v2 没有 non_five_star_behavior 和 auto_page_flip
    }

    migrated = UserSetting.migrate_from_old_version(early_v2_config)

    assert migrated.version == UserSetting._VERSION
    assert migrated.trash_weapon_ids == ["weapon_v2"]
    # v2→v3 补充的字段
    assert migrated.non_five_star_behavior == "process"
    assert migrated.auto_page_flip is True
    # v3→v4 补充的字段
    assert migrated.update_mirror == "github"
    assert migrated.update_proxy == ""
    # v4→v5 补充的字段
    assert migrated.treasure_essence_match_mode == "all"
    assert migrated.high_level_treasure_match_mode == "any"
    assert migrated.high_level_treasure_only_check_attribute is True
    assert migrated.high_level_treasure_only_check_secondary is True
    assert migrated.high_level_treasure_only_check_skill is True
    assert migrated.same_type_treasure_limit_enabled is False
    assert migrated.same_type_treasure_limit == 1


def test_migrations_completeness():
    """测试 _MIGRATIONS 字典完整性，确保所有中间版本都有迁移函数"""
    current_version = UserSetting._VERSION
    migrations = UserSetting._MIGRATIONS

    # 检查从版本 2 到当前版本的所有迁移路径
    for v in range(2, current_version):
        assert v in migrations, (
            f"缺少迁移函数：v{v} → v{v + 1}\n"
            f"请在 UserSetting 中添加 _migrate_v{v}_to_v{v + 1} 方法"
        )


def test_frontend_config_version_matches_backend():
    """确保前端 settings.vue 中的 config version 与后端 UserSetting._VERSION 一致。

    前端发送的 version 字段必须和后端校验的版本号匹配，否则配置将无法保存。
    如果此测试失败，请同步更新 frontend/src/pages/settings.vue 中的 version 值。
    """
    import re
    from pathlib import Path

    settings_vue = (
        Path(__file__).resolve().parent.parent
        / "frontend"
        / "src"
        / "pages"
        / "settings.vue"
    )
    assert settings_vue.exists(), f"找不到前端设置页面: {settings_vue}"

    content = settings_vue.read_text(encoding="utf-8")

    # 从 config computed 中提取 version: <number>
    # 匹配 return { version: N, ... } 内的 version 字段
    match = re.search(r"return\s*\{[^}]*version:\s*(\d+)", content)
    assert match, (
        "无法从 settings.vue 的 config computed 中提取 version 字段，"
        "请检查模板格式是否变更"
    )

    frontend_version = int(match.group(1))
    backend_version = UserSetting._VERSION

    assert frontend_version == backend_version, (
        f"前后端配置版本不一致！前端 version={frontend_version}，后端 _VERSION={backend_version}\n"
        f"请将 frontend/src/pages/settings.vue 中的 version 改为 {backend_version}，"
        f"或更新 UserSetting._VERSION 以匹配前端。"
    )
