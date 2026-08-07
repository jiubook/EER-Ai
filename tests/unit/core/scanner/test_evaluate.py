from unittest.mock import MagicMock

import pytest

from endfield_essence_recognizer.core.recognition import (
    AbandonStatusLabel,
    LockStatusLabel,
    RarityLabel,
)
from endfield_essence_recognizer.core.scanner.evaluate import (
    compare_levels,
    evaluate_essence,
    get_updated_weapon_ids,
    reset_scan_claims,
)
from endfield_essence_recognizer.core.scanner.models import (
    EssenceData,
    EssenceQuality,
)
from endfield_essence_recognizer.game_data.models.v2 import EssenceStatV2, StatType
from endfield_essence_recognizer.schemas.user_setting import (
    EssenceStats,
    KeepBestMode,
    NonFiveStarBehavior,
    SameTypeGroupMode,
    TreasureMatchMode,
    UserSetting,
)


def _make_stat(stat_id: str, stat_type: StatType) -> EssenceStatV2:
    """Create a mock EssenceStatV2 with the given type."""
    return EssenceStatV2(stat_id=stat_id, name=stat_id, type=stat_type)


# 预定义测试用的 stat 对象
_STAT_A = _make_stat("A", StatType.ATTRIBUTE)
_STAT_B = _make_stat("B", StatType.SECONDARY)
_STAT_C = _make_stat("C", StatType.SKILL)

_MOCK_STAT_TABLE: dict[str, EssenceStatV2] = {
    "A": _STAT_A,
    "B": _STAT_B,
    "C": _STAT_C,
}


@pytest.fixture
def mock_static_game_data():
    mock_data = MagicMock()

    # 按 stat_id 返回对应的 EssenceStatV2（含类型信息）
    mock_data.get_stat.side_effect = lambda sid: _MOCK_STAT_TABLE.get(sid)
    mock_data.find_weapons_by_stats.return_value = []
    mock_data.get_weapon.return_value = None
    mock_data.get_weapon_type.return_value = None

    return mock_data


@pytest.fixture
def default_settings():
    return UserSetting()


@pytest.fixture
def default_essence_data():
    return EssenceData(
        stats=["A", "B", "C"],
        stat_types=[StatType.ATTRIBUTE, StatType.SECONDARY, StatType.SKILL],
        levels=[0, 0, 0],
        rarity=RarityLabel.OTHER,
        abandon_label=AbandonStatusLabel.NOT_ABANDONED,
        lock_label=LockStatusLabel.NOT_LOCKED,
    )


def test_evaluate_trash(mock_static_game_data, default_settings, default_essence_data):
    """
    Test that an essence matching no rules and no weapons is evaluated as TRASH.

    Condition:
    - Tables are empty (no known weapons).
    - No custom rules.
    - No high level logic enabled.
    """
    # Setup nothing in tables -> Trash
    result = evaluate_essence(
        default_essence_data, default_settings, mock_static_game_data
    )
    assert result.quality == EssenceQuality.TRASH
    assert "养成材料" in result.log_message


def test_evaluate_treasure_custom(
    mock_static_game_data, default_settings, default_essence_data
):
    """
    Test that an essence matching a user-defined custom treasure rule is evaluated as TREASURE.

    Condition:
    - User setting has a custom treasure rule matching the stats (A, B, C).
    """
    # Setup custom treasure rule
    default_settings.treasure_essence_stats = [
        EssenceStats(attribute="A", secondary="B", skill="C")
    ]

    result = evaluate_essence(
        default_essence_data, default_settings, mock_static_game_data
    )
    assert result.quality == EssenceQuality.TREASURE
    assert "宝藏" in result.log_message
    assert "自定义基质" in result.log_message


def test_evaluate_custom_treasure_match_mode_any(
    mock_static_game_data, default_settings, default_essence_data
):
    """任一已设置槽位匹配即可视为自定义宝藏。"""
    default_settings.treasure_essence_match_mode = TreasureMatchMode.ANY
    default_settings.treasure_essence_stats = [
        EssenceStats(attribute="A", secondary=None, skill=None)
    ]

    result = evaluate_essence(
        default_essence_data, default_settings, mock_static_game_data
    )

    assert result.quality == EssenceQuality.TREASURE


def test_evaluate_custom_treasure_match_mode_only_checks_configured_slots(
    mock_static_game_data, default_settings, default_essence_data
):
    """仅模式只检查用户设置的槽位，未设置槽位会被忽略。"""
    default_settings.treasure_essence_match_mode = TreasureMatchMode.ONLY
    default_settings.treasure_essence_stats = [
        EssenceStats(attribute="A", secondary="B", skill=None)
    ]

    result = evaluate_essence(
        default_essence_data, default_settings, mock_static_game_data
    )

    assert result.quality == EssenceQuality.TREASURE


def test_evaluate_custom_treasure_match_mode_only_rejects_configured_mismatch(
    mock_static_game_data, default_settings, default_essence_data
):
    """仅模式要求所有已设置槽位都匹配。"""
    default_settings.treasure_essence_match_mode = TreasureMatchMode.ONLY
    default_settings.treasure_essence_stats = [
        EssenceStats(attribute="A", secondary="X", skill=None)
    ]

    result = evaluate_essence(
        default_essence_data, default_settings, mock_static_game_data
    )

    assert result.quality == EssenceQuality.TRASH


def test_evaluate_custom_treasure_match_mode_all_requires_three_slots(
    mock_static_game_data, default_settings, default_essence_data
):
    """和模式要求 1、2、3 三个槽位都设置且匹配。"""
    default_settings.treasure_essence_match_mode = TreasureMatchMode.ALL
    default_settings.treasure_essence_stats = [
        EssenceStats(attribute="A", secondary="B", skill=None)
    ]

    result = evaluate_essence(
        default_essence_data, default_settings, mock_static_game_data
    )

    assert result.quality == EssenceQuality.TRASH


def test_evaluate_custom_treasure_match_mode_all_matches_three_slots(
    mock_static_game_data, default_settings, default_essence_data
):
    """和模式下 1、2、3 三个槽位全部匹配时视为宝藏。"""
    default_settings.treasure_essence_match_mode = TreasureMatchMode.ALL
    default_settings.treasure_essence_stats = [
        EssenceStats(attribute="A", secondary="B", skill="C")
    ]

    result = evaluate_essence(
        default_essence_data, default_settings, mock_static_game_data
    )

    assert result.quality == EssenceQuality.TREASURE


def test_evaluate_treasure_weapon_match(
    mock_static_game_data, default_settings, default_essence_data
):
    """
    Test that an essence matching a known weapon is evaluated as TREASURE.
    """
    mock_static_game_data.find_weapons_by_stats.return_value = ["wpn_test"]
    weapon_mock = MagicMock()
    weapon_mock.weapon_id = "wpn_test"
    weapon_mock.name = "TestWeapon"
    weapon_mock.rarity = 6
    weapon_mock.weapon_type = 1
    mock_static_game_data.get_weapon.return_value = weapon_mock
    weapon_type_mock = MagicMock()
    weapon_type_mock.name = "TestType"
    mock_static_game_data.get_weapon_type.return_value = weapon_type_mock

    result = evaluate_essence(
        default_essence_data, default_settings, mock_static_game_data
    )
    assert result.quality == EssenceQuality.TREASURE
    assert "TestWeapon" in result.log_message
    assert "TestType" in result.log_message
    assert "wpn_test" in result.matched_weapons


def test_evaluate_weapon_match_trash_filter(
    mock_static_game_data, default_settings, default_essence_data
):
    """
    Test that an essence matching a known weapon is evaluated as TRASH if that weapon is filtered.
    """
    mock_static_game_data.find_weapons_by_stats.return_value = ["wpn_test"]
    weapon_mock = MagicMock()
    weapon_mock.weapon_id = "wpn_test"
    weapon_mock.name = "TestWeapon"
    weapon_mock.rarity = 6
    weapon_mock.weapon_type = "TestType"
    mock_static_game_data.get_weapon.return_value = weapon_mock
    weapon_type_mock = MagicMock()
    weapon_type_mock.name = "TestType"
    mock_static_game_data.get_weapon_type.return_value = weapon_type_mock

    # Filter it out
    default_settings.trash_weapon_ids = ["wpn_test"]

    result = evaluate_essence(
        default_essence_data, default_settings, mock_static_game_data
    )
    assert result.quality == EssenceQuality.TRASH
    assert "手动拦截" in result.log_message
    assert "wpn_test" in result.matched_weapons


def test_evaluate_high_level(
    mock_static_game_data, default_settings, default_essence_data
):
    """
    Test high-level attribute evaluation.
    """
    default_settings.high_level_treasure_enabled = True
    default_settings.high_level_treasure_attribute_threshold = 10

    stat = MagicMock()
    stat.stat_id = "A"
    stat.name = "AttrA"
    stat.type = "ATTRIBUTE"
    mock_static_game_data.get_stat.side_effect = None
    mock_static_game_data.get_stat.return_value = stat

    # Level 11 >= Threshold 10
    default_essence_data.levels = [11, 0, 0]

    result = evaluate_essence(
        default_essence_data, default_settings, mock_static_game_data
    )
    assert result.is_high_level is True
    assert "AttrA+11" in result.log_message


def test_evaluate_high_level_only_mode_with_category_toggles(
    mock_static_game_data, default_settings, default_essence_data
):
    """仅模式下，只有勾选的类别会被检查。"""
    default_settings.high_level_treasure_enabled = True
    default_settings.high_level_treasure_match_mode = TreasureMatchMode.ONLY
    default_settings.high_level_treasure_attribute_threshold = 3
    default_settings.high_level_treasure_secondary_threshold = 3
    default_settings.high_level_treasure_skill_threshold = 3
    # Only check attribute
    default_settings.high_level_treasure_only_check_attribute = True
    default_settings.high_level_treasure_only_check_secondary = False
    default_settings.high_level_treasure_only_check_skill = False
    # Attribute level meets threshold, others don't
    default_essence_data.levels = [3, 0, 0]

    result = evaluate_essence(
        default_essence_data, default_settings, mock_static_game_data
    )
    assert result.quality == EssenceQuality.TREASURE
    assert result.is_high_level is True


def test_evaluate_high_level_only_mode_unchecked_category_ignored(
    mock_static_game_data, default_settings, default_essence_data
):
    """仅模式下，未勾选的类别即使不达标也不影响判定。"""
    default_settings.high_level_treasure_enabled = True
    default_settings.high_level_treasure_match_mode = TreasureMatchMode.ONLY
    default_settings.high_level_treasure_attribute_threshold = 3
    default_settings.high_level_treasure_secondary_threshold = 5
    default_settings.high_level_treasure_skill_threshold = 3
    # Check attribute and skill, skip secondary
    default_settings.high_level_treasure_only_check_attribute = True
    default_settings.high_level_treasure_only_check_secondary = False
    default_settings.high_level_treasure_only_check_skill = True
    # Attribute=3 (meets), Secondary=0 (doesn't meet but unchecked), Skill=2 (doesn't meet)
    default_essence_data.levels = [3, 0, 2]

    result = evaluate_essence(
        default_essence_data, default_settings, mock_static_game_data
    )
    # Skill doesn't meet threshold so should be TRASH
    assert result.quality == EssenceQuality.TRASH


def test_evaluate_high_level_only_mode_all_categories_match(
    mock_static_game_data, default_settings, default_essence_data
):
    """仅模式下，所有勾选类别都达标时视为宝藏。"""
    default_settings.high_level_treasure_enabled = True
    default_settings.high_level_treasure_match_mode = TreasureMatchMode.ONLY
    default_settings.high_level_treasure_attribute_threshold = 3
    default_settings.high_level_treasure_secondary_threshold = 3
    default_settings.high_level_treasure_skill_threshold = 2
    default_settings.high_level_treasure_only_check_attribute = True
    default_settings.high_level_treasure_only_check_secondary = True
    default_settings.high_level_treasure_only_check_skill = True
    default_essence_data.levels = [3, 3, 2]

    stat = MagicMock()
    stat.name = "AttrA"
    mock_static_game_data.get_stat.return_value = stat

    result = evaluate_essence(
        default_essence_data, default_settings, mock_static_game_data
    )
    assert result.quality == EssenceQuality.TREASURE
    assert result.is_high_level is True


def test_evaluate_high_level_all_mode_requires_all_slots(
    mock_static_game_data, default_settings, default_essence_data
):
    """高等级和模式要求 1、2、3 三个槽位都满足阈值。"""
    default_settings.high_level_treasure_enabled = True
    default_settings.high_level_treasure_match_mode = TreasureMatchMode.ALL
    default_settings.high_level_treasure_attribute_threshold = 3
    default_settings.high_level_treasure_secondary_threshold = 3
    default_settings.high_level_treasure_skill_threshold = 3
    # Only attribute meets threshold
    default_essence_data.levels = [3, 0, 0]

    result = evaluate_essence(
        default_essence_data, default_settings, mock_static_game_data
    )

    assert result.quality == EssenceQuality.TRASH


def test_evaluate_same_type_treasure_limit_marks_later_items_as_trash(
    mock_static_game_data, default_settings, default_essence_data
):
    """同类型宝藏达到上限后，后续同属性组合会视为养成材料。"""
    default_settings.same_type_treasure_limit_enabled = True
    default_settings.same_type_treasure_limit = 1
    default_settings.treasure_essence_stats = [
        EssenceStats(attribute="A", secondary="B", skill="C")
    ]

    first = evaluate_essence(
        default_essence_data, default_settings, mock_static_game_data
    )
    second = evaluate_essence(
        default_essence_data, default_settings, mock_static_game_data
    )

    assert first.quality == EssenceQuality.TREASURE
    assert second.quality == EssenceQuality.TRASH
    assert "达到设置上限" in second.log_message


def test_evaluate_by_weapon_custom_matrix_claimed_first(
    mock_static_game_data, default_settings, default_essence_data
):
    """按武器划分：自定义基质与内置武器同时命中时，优先认领自定义基质条目。"""
    default_settings.same_type_group_mode = SameTypeGroupMode.BY_WEAPON
    default_settings.treasure_essence_stats = [
        EssenceStats(id="abc", name="自定义X", attribute="A", secondary="B", skill="C")
    ]
    _reset_scan_state(default_settings)
    kwargs = _set_weapon_match(mock_static_game_data, ["wpn_a"])

    result = evaluate_essence(
        default_essence_data, default_settings, mock_static_game_data, **kwargs
    )

    assert result.quality == EssenceQuality.TREASURE
    assert default_settings._same_type_best_levels == {"custom:abc": (1, 1, 1)}
    assert default_settings._same_type_treasure_counts == {"custom:abc": 1}
    assert "custom:abc" in get_updated_weapon_ids()
    assert "wpn_a" not in get_updated_weapon_ids()


def test_evaluate_by_weapon_custom_matrix_cap_falls_back_to_weapon(
    mock_static_game_data, default_settings, default_essence_data
):
    """按武器划分：自定义基质达到自身上限后，回退分配给匹配的内置武器。"""
    default_settings.same_type_group_mode = SameTypeGroupMode.BY_WEAPON
    default_settings.treasure_essence_stats = [
        EssenceStats(id="abc", name="自定义X", attribute="A", secondary="B", skill="C")
    ]
    _reset_scan_state(default_settings)
    kwargs = _set_weapon_match(mock_static_game_data, ["wpn_a"])

    evaluate_essence(
        default_essence_data, default_settings, mock_static_game_data, **kwargs
    )
    second = evaluate_essence(
        default_essence_data, default_settings, mock_static_game_data, **kwargs
    )

    assert second.quality == EssenceQuality.TREASURE
    assert default_settings._same_type_best_levels["custom:abc"] == (1, 1, 1)
    assert default_settings._same_type_best_levels["wpn_a"] == (1, 1, 1)
    assert default_settings._same_type_treasure_counts["wpn_a"] == 1
    assert "wpn_a" in get_updated_weapon_ids()


def test_evaluate_by_weapon_custom_keep_best_upgrade_syncs_custom_entry(
    mock_static_game_data, default_settings, default_essence_data
):
    """按武器划分 + 留大弃小：自定义基质升级时同步到自定义条目。"""
    default_settings.same_type_group_mode = SameTypeGroupMode.BY_WEAPON
    default_settings.same_type_keep_best = True
    default_settings.treasure_essence_stats = [
        EssenceStats(id="abc", name="自定义X", attribute="A", secondary="B", skill="C")
    ]
    _reset_scan_state(default_settings)
    # 模拟 profile 中已保存的自定义条目（含相等跳过名额）
    default_settings._same_type_best_levels["custom:abc"] = (1, 1, 1)
    default_settings._same_type_equal_skips["custom:abc"] = 1
    kwargs = _set_weapon_match(mock_static_game_data, ["wpn_a"])

    default_essence_data.levels = [2, 1, 1]
    result = evaluate_essence(
        default_essence_data, default_settings, mock_static_game_data, **kwargs
    )

    assert result.quality == EssenceQuality.TREASURE
    assert default_settings._same_type_best_levels["custom:abc"] == (2, 1, 1)
    assert "custom:abc" in get_updated_weapon_ids()


def test_evaluate_by_stat_custom_matrix_claimed_first_shared_count(
    mock_static_game_data, default_settings, default_essence_data
):
    """按基质划分：命中自定义基质时等级写入自定义条目，计数仍按属性组合共享。"""
    default_settings.same_type_group_mode = SameTypeGroupMode.BY_STAT
    default_settings.treasure_essence_stats = [
        EssenceStats(id="abc", name="自定义X", attribute="A", secondary="B", skill="C")
    ]
    _reset_scan_state(default_settings)
    kwargs = _set_weapon_match(mock_static_game_data, ["wpn_a"])

    first = evaluate_essence(
        default_essence_data, default_settings, mock_static_game_data, **kwargs
    )
    second = evaluate_essence(
        default_essence_data, default_settings, mock_static_game_data, **kwargs
    )

    assert first.quality == EssenceQuality.TREASURE
    assert default_settings._same_type_best_levels["custom:abc"] == (1, 1, 1)
    assert "custom:abc" in get_updated_weapon_ids()
    # 计数 key 为属性组合，与内置武器同组共享
    assert default_settings._same_type_treasure_counts[("A", "B", "C")] == 1
    assert second.quality == EssenceQuality.TRASH
    assert "达到设置上限" in second.log_message


def test_evaluate_by_stat_custom_only_match_writes_custom_entry(
    mock_static_game_data, default_settings, default_essence_data
):
    """按基质划分：仅命中自定义基质（无内置武器）时，等级写入自定义条目。"""
    default_settings.same_type_group_mode = SameTypeGroupMode.BY_STAT
    default_settings.treasure_essence_stats = [
        EssenceStats(id="abc", name="自定义X", attribute="A", secondary="B", skill="C")
    ]
    _reset_scan_state(default_settings)
    # 无内置武器命中，仅自定义基质
    kwargs = _set_weapon_match(mock_static_game_data, [])

    result = evaluate_essence(
        default_essence_data, default_settings, mock_static_game_data, **kwargs
    )

    assert result.quality == EssenceQuality.TREASURE
    assert default_settings._same_type_best_levels["custom:abc"] == (1, 1, 1)
    assert default_settings._same_type_treasure_counts[("A", "B", "C")] == 1
    assert "custom:abc" in get_updated_weapon_ids()


def test_evaluate_by_stat_worse_level_does_not_overwrite_saved_best(
    mock_static_game_data, default_settings, default_essence_data
):
    """按基质划分：更差基质跳过已保存更高等级的武器，回退给下一把武器，不降级。"""
    default_settings.same_type_group_mode = SameTypeGroupMode.BY_STAT
    default_settings.same_type_non_downgrade_filter = False
    _reset_scan_state(default_settings)
    # 模拟 profile 已保存 wpn_0 (3,3,3)
    default_settings._same_type_best_levels["wpn_0"] = (3, 3, 3)
    default_settings._same_type_equal_skips["wpn_0"] = 1
    kwargs = _set_weapon_match(mock_static_game_data, ["wpn_0", "wpn_1"])
    default_essence_data.levels = [2, 2, 2]

    result = evaluate_essence(
        default_essence_data, default_settings, mock_static_game_data, **kwargs
    )

    assert result.quality == EssenceQuality.TREASURE
    assert default_settings._same_type_best_levels["wpn_0"] == (3, 3, 3)
    assert default_settings._same_type_best_levels["wpn_1"] == (2, 2, 2)
    assert "wpn_1" in get_updated_weapon_ids()
    assert "wpn_0" not in get_updated_weapon_ids()


def test_evaluate_by_stat_worse_level_virtual_claim_keeps_profile(
    mock_static_game_data, default_settings, default_essence_data
):
    """按基质划分：仅一把武器且其已保存更高等级时，更差基质由虚拟槽接收，锁定但不落盘。"""
    default_settings.same_type_group_mode = SameTypeGroupMode.BY_STAT
    default_settings.same_type_non_downgrade_filter = False
    _reset_scan_state(default_settings)
    default_settings._same_type_best_levels["wpn_0"] = (3, 3, 3)
    default_settings._same_type_equal_skips["wpn_0"] = 1
    kwargs = _set_weapon_match(mock_static_game_data, ["wpn_0"])
    default_essence_data.levels = [2, 2, 2]

    result = evaluate_essence(
        default_essence_data, default_settings, mock_static_game_data, **kwargs
    )

    assert result.quality == EssenceQuality.TREASURE
    assert default_settings._same_type_best_levels["wpn_0"] == (3, 3, 3)
    assert "wpn_0" not in get_updated_weapon_ids()
    # 虚拟槽认领：消耗共享计数，但不落盘
    assert default_settings._same_type_treasure_counts[("A", "B", "C")] == 1


def test_evaluate_by_stat_worse_level_when_count_full_trashes(
    mock_static_game_data, default_settings, default_essence_data
):
    """按基质划分：共享计数已满且无武器可接收时，更差基质标记为养成材料。"""
    default_settings.same_type_group_mode = SameTypeGroupMode.BY_STAT
    default_settings.same_type_non_downgrade_filter = False
    _reset_scan_state(default_settings)
    default_settings._same_type_best_levels["wpn_0"] = (3, 3, 3)
    default_settings._same_type_equal_skips["wpn_0"] = 1
    # 共享计数已满
    default_settings._same_type_treasure_counts[("A", "B", "C")] = 1
    kwargs = _set_weapon_match(mock_static_game_data, ["wpn_0"])
    default_essence_data.levels = [2, 2, 2]

    result = evaluate_essence(
        default_essence_data, default_settings, mock_static_game_data, **kwargs
    )

    assert result.quality == EssenceQuality.TRASH
    assert default_settings._same_type_best_levels["wpn_0"] == (3, 3, 3)


def _reset_scan_state(settings: UserSetting) -> None:
    """模拟引擎扫描开始前的状态重置。"""
    reset_scan_claims()
    settings._same_type_treasure_counts = {}
    settings._same_type_best_levels = {}
    settings._same_type_equal_skips = {}


def _set_weapon_match(
    mock_static_game_data, weapon_ids: list[str], *, weapon_levels: dict | None = None
) -> dict:
    """配置武器匹配与各武器已有等级，返回 evaluate 所需的辅助参数。"""
    mock_static_game_data.find_weapons_by_stats.return_value = weapon_ids
    return {
        "weapon_essence_levels": weapon_levels or {},
        "weapon_priority_order": weapon_ids,
    }


def test_evaluate_limit_disabled_claims_single_weapon(
    mock_static_game_data, default_settings, default_essence_data
):
    """关闭数量上限后，匹配单武器时认领并写入最佳等级与计数。"""
    default_settings.same_type_treasure_limit_enabled = False
    _reset_scan_state(default_settings)
    kwargs = _set_weapon_match(mock_static_game_data, ["wpn_a"])

    result = evaluate_essence(
        default_essence_data, default_settings, mock_static_game_data, **kwargs
    )

    assert result.quality == EssenceQuality.TREASURE
    assert default_settings._same_type_best_levels["wpn_a"] == (1, 1, 1)
    assert default_settings._same_type_treasure_counts["wpn_a"] == 1
    assert "wpn_a" in get_updated_weapon_ids()


def test_evaluate_limit_disabled_claims_highest_priority_weapon_only(
    mock_static_game_data, default_settings, default_essence_data
):
    """关闭数量上限后，多武器匹配时按优先级只认领一把武器。"""
    default_settings.same_type_treasure_limit_enabled = False
    _reset_scan_state(default_settings)
    kwargs = _set_weapon_match(mock_static_game_data, ["wpn_b", "wpn_a"])

    result = evaluate_essence(
        default_essence_data, default_settings, mock_static_game_data, **kwargs
    )

    assert result.quality == EssenceQuality.TREASURE
    assert default_settings._same_type_best_levels == {"wpn_b": (1, 1, 1)}
    assert default_settings._same_type_treasure_counts == {"wpn_b": 1}


def test_evaluate_limit_disabled_keep_best_upgrades_keeps_worse(
    mock_static_game_data, default_settings, default_essence_data
):
    """关闭数量上限 + 留大弃小：更优的替换升级，更差的保留且不标记养成材料。"""
    default_settings.same_type_treasure_limit_enabled = False
    default_settings.same_type_keep_best = True
    _reset_scan_state(default_settings)
    kwargs = _set_weapon_match(mock_static_game_data, ["wpn_a"])

    default_essence_data.levels = [3, 3, 3]
    evaluate_essence(
        default_essence_data, default_settings, mock_static_game_data, **kwargs
    )
    assert default_settings._same_type_best_levels["wpn_a"] == (3, 3, 3)
    assert default_settings._same_type_treasure_counts["wpn_a"] == 1

    default_essence_data.levels = [4, 3, 3]
    upgraded = evaluate_essence(
        default_essence_data, default_settings, mock_static_game_data, **kwargs
    )
    assert upgraded.quality == EssenceQuality.TREASURE
    assert default_settings._same_type_best_levels["wpn_a"] == (4, 3, 3)
    assert default_settings._same_type_treasure_counts["wpn_a"] == 1

    default_essence_data.levels = [2, 2, 2]
    worse = evaluate_essence(
        default_essence_data, default_settings, mock_static_game_data, **kwargs
    )
    assert worse.quality == EssenceQuality.TREASURE
    assert default_settings._same_type_best_levels["wpn_a"] == (4, 3, 3)


def test_evaluate_limit_disabled_no_keep_best_first_come_first_served(
    mock_static_game_data, default_settings, default_essence_data
):
    """关闭数量上限且关闭留大弃小：无比较，首枚认领后锁定，更优的也不替换。"""
    default_settings.same_type_treasure_limit_enabled = False
    default_settings.same_type_keep_best = False
    _reset_scan_state(default_settings)
    kwargs = _set_weapon_match(mock_static_game_data, ["wpn_a"])

    default_essence_data.levels = [3, 3, 3]
    evaluate_essence(
        default_essence_data, default_settings, mock_static_game_data, **kwargs
    )
    assert default_settings._same_type_best_levels["wpn_a"] == (3, 3, 3)

    default_essence_data.levels = [4, 3, 3]
    result = evaluate_essence(
        default_essence_data, default_settings, mock_static_game_data, **kwargs
    )
    assert result.quality == EssenceQuality.TREASURE
    assert default_settings._same_type_best_levels["wpn_a"] == (3, 3, 3)


def test_evaluate_limit_disabled_exhausted_keeps_treasure(
    mock_static_game_data, default_settings, default_essence_data
):
    """关闭数量上限后，所有匹配武器各认领 1 枚后，多余的保留为宝藏基质。"""
    default_settings.same_type_treasure_limit_enabled = False
    _reset_scan_state(default_settings)
    kwargs = _set_weapon_match(mock_static_game_data, ["wpn_a", "wpn_b"])

    for _weapon_id in ("wpn_a", "wpn_b"):
        result = evaluate_essence(
            default_essence_data, default_settings, mock_static_game_data, **kwargs
        )
        assert result.quality == EssenceQuality.TREASURE

    extra = evaluate_essence(
        default_essence_data, default_settings, mock_static_game_data, **kwargs
    )
    assert extra.quality == EssenceQuality.TREASURE
    assert default_settings._same_type_best_levels == {
        "wpn_a": (1, 1, 1),
        "wpn_b": (1, 1, 1),
    }


def test_evaluate_limit_disabled_non_downgrade_filter_blocks_keeps(
    mock_static_game_data, default_settings, default_essence_data
):
    """关闭数量上限 + 非降级过滤：无可用武器时保留，不标记为养成材料。"""
    default_settings.same_type_treasure_limit_enabled = False
    default_settings.same_type_non_downgrade_filter = True
    _reset_scan_state(default_settings)
    kwargs = _set_weapon_match(
        mock_static_game_data,
        ["wpn_a"],
        weapon_levels={"wpn_a": (6, 6, 3)},
    )

    result = evaluate_essence(
        default_essence_data, default_settings, mock_static_game_data, **kwargs
    )

    assert result.quality == EssenceQuality.TREASURE
    assert default_settings._same_type_best_levels == {}


def test_evaluate_limit_disabled_non_downgrade_filter_passes_claims(
    mock_static_game_data, default_settings, default_essence_data
):
    """关闭数量上限 + 非降级过滤：满足非降级原则时正常认领。"""
    default_settings.same_type_treasure_limit_enabled = False
    default_settings.same_type_non_downgrade_filter = True
    _reset_scan_state(default_settings)
    kwargs = _set_weapon_match(
        mock_static_game_data,
        ["wpn_a"],
        weapon_levels={"wpn_a": (2, 2, 1)},
    )
    default_essence_data.levels = [3, 3, 2]

    result = evaluate_essence(
        default_essence_data, default_settings, mock_static_game_data, **kwargs
    )

    assert result.quality == EssenceQuality.TREASURE
    assert default_settings._same_type_best_levels["wpn_a"] == (3, 3, 2)
    assert "wpn_a" in get_updated_weapon_ids()


def test_evaluate_non_five_star_skip(
    mock_static_game_data, default_settings, default_essence_data
):
    """
    Test skipping non-5-star essence.
    """
    default_essence_data.rarity = RarityLabel.FOUR
    default_settings.non_five_star_behavior = NonFiveStarBehavior.SKIP

    result = evaluate_essence(
        default_essence_data, default_settings, mock_static_game_data
    )
    assert result.quality == EssenceQuality.SKIP
    assert "跳过" in result.log_message
    assert result.stop_scan is False


def test_evaluate_non_five_star_stop(
    mock_static_game_data, default_settings, default_essence_data
):
    """
    Test stopping scan when non-5-star essence is encountered.
    """
    default_essence_data.rarity = RarityLabel.FOUR
    default_settings.non_five_star_behavior = NonFiveStarBehavior.STOP

    result = evaluate_essence(
        default_essence_data, default_settings, mock_static_game_data
    )
    assert result.quality == EssenceQuality.SKIP
    assert result.stop_scan is True
    assert "结束本次扫描" in result.log_message


def test_evaluate_non_five_star_process(
    mock_static_game_data, default_settings, default_essence_data
):
    """
    Test processing non-5-star essence as normal.
    """
    default_essence_data.rarity = RarityLabel.FOUR
    default_settings.non_five_star_behavior = NonFiveStarBehavior.PROCESS

    result = evaluate_essence(
        default_essence_data, default_settings, mock_static_game_data
    )
    # Should fall through to normal evaluation (Trash in this blank case)
    assert result.quality == EssenceQuality.TRASH
    assert "养成材料" in result.log_message


# --- compare_levels 测试 ---


class TestCompareLevelsSequential:
    """sequential 模式：逐维度从左到右比较 A → B → C。"""

    def test_current_greater_first_dim(self):
        assert compare_levels((3, 1, 1), (2, 1, 1)) == 1

    def test_existing_greater_first_dim(self):
        assert compare_levels((2, 1, 1), (3, 1, 1)) == -1

    def test_equal(self):
        assert compare_levels((3, 3, 3), (3, 3, 3)) == 0

    def test_second_dim_decides(self):
        assert compare_levels((3, 4, 1), (3, 3, 1)) == 1

    def test_third_dim_decides(self):
        assert compare_levels((3, 3, 2), (3, 3, 1)) == 1

    def test_first_dim_overrides_later(self):
        """第一维度不等时，后续维度不影响结果。"""
        assert compare_levels((2, 6, 3), (3, 1, 1)) == -1


class TestCompareLevelsSum:
    """sum 模式：比较三词条等级之和。"""

    def test_current_sum_greater(self):
        assert compare_levels((6, 6, 3), (5, 5, 3), KeepBestMode.SUM) == 1

    def test_existing_sum_greater(self):
        assert compare_levels((1, 1, 1), (2, 2, 2), KeepBestMode.SUM) == -1

    def test_equal_sum(self):
        assert compare_levels((4, 4, 1), (3, 3, 3), KeepBestMode.SUM) == 0

    def test_different_distribution_same_sum(self):
        """分布不同但和相等时返回 0。"""
        assert compare_levels((6, 1, 1), (3, 3, 2), KeepBestMode.SUM) == 0


class TestCompareLevelsGrease:
    """grease 模式：按冷却脂消耗总量比较。"""

    def test_current_more_grease(self):
        """高等级消耗更多冷却脂，current 更优。"""
        assert (
            compare_levels(
                (6, 6, 3),
                (1, 1, 1),
                KeepBestMode.GREASE,
                [StatType.ATTRIBUTE, StatType.SECONDARY, StatType.SKILL],
            )
            == 1
        )

    def test_equal_grease(self):
        assert (
            compare_levels(
                (3, 3, 1),
                (3, 3, 1),
                KeepBestMode.GREASE,
                [StatType.ATTRIBUTE, StatType.SECONDARY, StatType.SKILL],
            )
            == 0
        )

    def test_existing_more_grease(self):
        assert (
            compare_levels(
                (1, 1, 1),
                (3, 3, 1),
                KeepBestMode.GREASE,
                [StatType.ATTRIBUTE, StatType.SECONDARY, StatType.SKILL],
            )
            == -1
        )

    def test_default_stat_types_when_none(self):
        """stat_types 为 None 时使用默认值 [ATTRIBUTE, SECONDARY, SKILL]。"""
        assert (
            compare_levels(
                (6, 6, 3),
                (1, 1, 1),
                KeepBestMode.GREASE,
            )
            == 1
        )


class TestCompareLevelsWeightedSum:
    """weighted_sum 模式：按升级难度加权比较。"""

    def test_current_higher_weight(self):
        assert (
            compare_levels(
                (6, 6, 3),
                (1, 1, 1),
                KeepBestMode.WEIGHTED_SUM,
                [StatType.ATTRIBUTE, StatType.SECONDARY, StatType.SKILL],
            )
            == 1
        )

    def test_equal_weight(self):
        assert (
            compare_levels(
                (3, 3, 1),
                (3, 3, 1),
                KeepBestMode.WEIGHTED_SUM,
                [StatType.ATTRIBUTE, StatType.SECONDARY, StatType.SKILL],
            )
            == 0
        )

    def test_existing_higher_weight(self):
        assert (
            compare_levels(
                (1, 1, 1),
                (3, 3, 1),
                KeepBestMode.WEIGHTED_SUM,
                [StatType.ATTRIBUTE, StatType.SECONDARY, StatType.SKILL],
            )
            == -1
        )

    def test_default_stat_types_when_none(self):
        """stat_types 为 None 时使用默认值。"""
        assert (
            compare_levels(
                (6, 6, 3),
                (1, 1, 1),
                KeepBestMode.WEIGHTED_SUM,
            )
            == 1
        )

    def test_skill_slot_uses_different_weights(self):
        """技能槽位使用不同的权重表，与基础/附加不同。"""
        # 同样是等级 3，技能属性的权重与基础属性不同
        # (1,1,3) vs (1,1,1) — 只有技能槽不同
        result = compare_levels(
            (1, 1, 3),
            (1, 1, 1),
            KeepBestMode.WEIGHTED_SUM,
            [StatType.ATTRIBUTE, StatType.SECONDARY, StatType.SKILL],
        )
        assert result == 1
