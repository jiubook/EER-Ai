from endfield_essence_recognizer.core.recognition import RarityLabel
from endfield_essence_recognizer.core.scanner.models import (
    EssenceData,
    EssenceQuality,
    EvaluationResult,
)
from endfield_essence_recognizer.game_data.models.v2 import StatType
from endfield_essence_recognizer.game_data.static_game_data import StaticGameData
from endfield_essence_recognizer.schemas.user_setting import (
    EssenceStats,
    NonFiveStarBehavior,
    SameTypeGroupMode,
    TreasureMatchMode,
    UserSetting,
)

STAT_SLOTS = ("attribute", "secondary", "skill")

# StatType → 对应 EssenceStats / 阈值配置中的字段名
_TYPE_TO_SLOT: dict[StatType, str] = {
    StatType.ATTRIBUTE: "attribute",
    StatType.SECONDARY: "secondary",
    StatType.SKILL: "skill",
}


def _get_threshold_for_type(
    stat_type: StatType | None,
    thresholds_by_type: dict[str, int],
) -> int | None:
    """根据 stat 的语义类型查找对应的判定阈值。"""
    if stat_type is None:
        return None
    slot = _TYPE_TO_SLOT.get(stat_type)
    if slot is None:
        return None
    return thresholds_by_type.get(slot)


def _matches_by_mode(
    matches: list[bool], configured_count: int, mode: TreasureMatchMode
) -> bool:
    if configured_count == 0:
        return False
    if mode == TreasureMatchMode.ANY:
        return any(matches)
    if mode == TreasureMatchMode.ALL:
        return configured_count == len(STAT_SLOTS) and all(matches)
    return all(matches)


def _matches_treasure_stats(
    treasure_stat: EssenceStats,
    stats: list[str | None],
    stat_types: list[StatType | None],
    mode: TreasureMatchMode,
) -> bool:
    # 按类型构建查找表：type → 实际 stat_id
    type_to_actual: dict[StatType, str | None] = {}
    for stat_id, stat_type in zip(stats, stat_types, strict=True):
        if stat_type is not None and stat_type not in type_to_actual:
            type_to_actual[stat_type] = stat_id

    # 用户配置的期望值按类型查找
    configured_values = [
        treasure_stat.attribute,
        treasure_stat.secondary,
        treasure_stat.skill,
    ]
    expected_types = [StatType.ATTRIBUTE, StatType.SECONDARY, StatType.SKILL]

    matches = [
        expected == type_to_actual.get(expected_type)
        for expected, expected_type in zip(configured_values, expected_types, strict=True)
        if expected is not None
    ]
    return _matches_by_mode(matches, len(matches), mode)


def _stat_display_name(static_game_data: StaticGameData, stat_id: str | None) -> str:
    if stat_id is None:
        return "未知属性"
    stat = static_game_data.get_stat(stat_id)
    return stat.name if stat is not None else stat_id


def _format_high_level_info(
    static_game_data: StaticGameData,
    stats: list[str | None],
    levels: list[int | None],
    indexes: list[int],
) -> str:
    parts = [
        f"{_stat_display_name(static_game_data, stats[index])}+{levels[index]}"
        for index in indexes
        if stats[index] is not None and levels[index] is not None
    ]
    if not parts:
        return ""
    return f"（含高等级属性词条：{'、'.join(parts)}）"


def _evaluate_high_level_treasure(
    data: EssenceData,
    setting: UserSetting,
    static_game_data: StaticGameData,
) -> tuple[bool, str]:
    if not setting.high_level_treasure_enabled:
        return False, ""

    stats = data.stats
    stat_types = data.stat_types
    levels = data.levels
    mode = setting.high_level_treasure_match_mode

    if mode == TreasureMatchMode.SUM:
        present_indexes = [
            i
            for i, (stat_id, level) in enumerate(zip(stats, levels, strict=True))
            if stat_id is not None and level is not None
        ]
        total = sum(levels[i] for i in present_indexes)  # type: ignore[misc]
        if total < setting.high_level_treasure_sum_threshold:
            return False, ""
        return True, _format_high_level_info(
            static_game_data, stats, levels, present_indexes
        )

    # 按类型构建阈值和 only_check 查找表
    thresholds_by_type: dict[str, int] = {
        "attribute": setting.high_level_treasure_attribute_threshold,
        "secondary": setting.high_level_treasure_secondary_threshold,
        "skill": setting.high_level_treasure_skill_threshold,
    }
    only_flags_by_type: dict[str, bool] = {
        "attribute": setting.high_level_treasure_only_check_attribute,
        "secondary": setting.high_level_treasure_only_check_secondary,
        "skill": setting.high_level_treasure_only_check_skill,
    }

    # 按每个位置的语义类型查找对应阈值进行判定
    original_slot_matches: list[bool] = []
    for stat_id, stat_type, level in zip(stats, stat_types, levels, strict=True):
        threshold = _get_threshold_for_type(stat_type, thresholds_by_type)
        if threshold is None or stat_id is None or level is None:
            original_slot_matches.append(False)
        else:
            original_slot_matches.append(level >= threshold)

    if mode == TreasureMatchMode.ONLY:
        eval_matches = [
            m
            for m, st in zip(original_slot_matches, stat_types, strict=True)
            if st is not None and only_flags_by_type.get(_TYPE_TO_SLOT.get(st, ""), False)
        ]
    else:
        eval_matches = original_slot_matches

    if mode == TreasureMatchMode.ANY:
        matched_indexes = [i for i, m in enumerate(original_slot_matches) if m]
    else:
        matched_indexes = (
            list(range(len(STAT_SLOTS))) if all(original_slot_matches) else []
        )

    if not _matches_by_mode(eval_matches, len(eval_matches), mode):
        return False, ""

    return True, _format_high_level_info(
        static_game_data, stats, levels, matched_indexes
    )


def _evaluate_non_five_star_high_level(
    data: EssenceData,
    setting: UserSetting,
    static_game_data: StaticGameData,
) -> tuple[bool, str]:
    """评估非无瑕基质的高等级属性词条。

    如果启用了独立设置，使用非无暇基质专用的高等级判定设置；
    否则使用宝藏基质判定规则中的高等级设置。
    """
    # 判断是否使用独立设置
    if setting.non_five_star_separate_high_level_settings:
        thresholds_by_type: dict[str, int] = {
            "attribute": setting.non_five_star_high_level_attribute_threshold,
            "secondary": setting.non_five_star_high_level_secondary_threshold,
            "skill": setting.non_five_star_high_level_skill_threshold,
        }
        mode = setting.non_five_star_high_level_match_mode
        sum_threshold = setting.non_five_star_high_level_sum_threshold
        only_flags_by_type: dict[str, bool] = {
            "attribute": setting.non_five_star_high_level_only_check_attribute,
            "secondary": setting.non_five_star_high_level_only_check_secondary,
            "skill": setting.non_five_star_high_level_only_check_skill,
        }
    else:
        # 使用宝藏基质判定规则中的高等级设置
        if not setting.high_level_treasure_enabled:
            return False, ""
        thresholds_by_type = {
            "attribute": setting.high_level_treasure_attribute_threshold,
            "secondary": setting.high_level_treasure_secondary_threshold,
            "skill": setting.high_level_treasure_skill_threshold,
        }
        mode = setting.high_level_treasure_match_mode
        sum_threshold = setting.high_level_treasure_sum_threshold
        only_flags_by_type = {
            "attribute": setting.high_level_treasure_only_check_attribute,
            "secondary": setting.high_level_treasure_only_check_secondary,
            "skill": setting.high_level_treasure_only_check_skill,
        }

    stats = data.stats
    stat_types = data.stat_types
    levels = data.levels

    if mode == TreasureMatchMode.SUM:
        present_indexes = [
            i
            for i, (stat_id, level) in enumerate(zip(stats, levels, strict=True))
            if stat_id is not None and level is not None
        ]
        total = sum(levels[i] for i in present_indexes)  # type: ignore[misc]
        if total < sum_threshold:
            return False, ""
        return True, _format_high_level_info(
            static_game_data, stats, levels, present_indexes
        )

    # 按每个位置的语义类型查找对应阈值进行判定
    original_slot_matches: list[bool] = []
    for stat_id, stat_type, level in zip(stats, stat_types, levels, strict=True):
        threshold = _get_threshold_for_type(stat_type, thresholds_by_type)
        if threshold is None or stat_id is None or level is None:
            original_slot_matches.append(False)
        else:
            original_slot_matches.append(level >= threshold)

    if mode == TreasureMatchMode.ONLY:
        eval_matches = [
            m
            for m, st in zip(original_slot_matches, stat_types, strict=True)
            if st is not None and only_flags_by_type.get(_TYPE_TO_SLOT.get(st, ""), False)
        ]
    else:
        eval_matches = original_slot_matches

    if mode == TreasureMatchMode.ANY:
        matched_indexes = [i for i, m in enumerate(original_slot_matches) if m]
    else:
        matched_indexes = (
            list(range(len(STAT_SLOTS))) if all(original_slot_matches) else []
        )

    if not _matches_by_mode(eval_matches, len(eval_matches), mode):
        return False, ""

    return True, _format_high_level_info(
        static_game_data, stats, levels, matched_indexes
    )


def _level_cmp(current: tuple[int, int, int], existing: tuple[int, int, int]) -> int:
    """逐维度从左到右比较等级，返回 1（更优）/ 0（相等）/ -1（更差）。"""
    for c, e in zip(current, existing, strict=True):
        if c > e:
            return 1
        if c < e:
            return -1
    return 0


def _make_trash_by_limit(
    evaluation: EvaluationResult, current_count: int, limit: int
) -> EvaluationResult:
    """构造因达到数量上限而降级为养成材料的结果。"""
    return EvaluationResult(
        quality=EssenceQuality.TRASH,
        log_message=(
            "这个基质是<red><bold><underline>养成材料</></></>，"
            f"因为同类型宝藏基质已扫描到 {current_count} 个，达到设置上限 {limit} 个。"
        ),
        matched_weapons=evaluation.matched_weapons,
        matched_weapons_all_blocked=True,
        is_high_level=evaluation.is_high_level,
    )


def _claim_as_owned(
    setting: UserSetting,
    key: tuple[str | None, ...] | str,
    current_levels: tuple[int, int, int],
) -> bool:
    """留大弃小：判断当前基质是否属于该组“已保存”的那一枚（或其升级版）。

    - 相等：说明就是 profile 里保存的那一枚，在仍有跳过名额时直接认领（不占用数量上限）。
    - 更优：说明保存的那枚升级了，认领并把阈值提升到新等级，同时消耗一个已存名额。
    - 更差：返回 False，交由数量上限逻辑判断。
    """
    best = setting._same_type_best_levels.get(key)
    if best is None:
        return False

    cmp = _level_cmp(current_levels, best)
    if cmp > 0:
        setting._same_type_best_levels[key] = current_levels
        skip = setting._same_type_equal_skips.get(key, 0)
        if skip > 0:
            setting._same_type_equal_skips[key] = skip - 1
        return True
    if cmp == 0:
        skip = setting._same_type_equal_skips.get(key, 0)
        if skip > 0:
            setting._same_type_equal_skips[key] = skip - 1
            return True
    return False


def _claim_by_limit(
    setting: UserSetting,
    key: tuple[str | None, ...] | str,
    current_levels: tuple[int, int, int],
    limit: int,
) -> bool:
    """按数量上限认领当前基质：未达上限则保留并计数，同时维护最佳等级。"""
    count = setting._same_type_treasure_counts.get(key, 0)
    if count >= limit:
        return False
    setting._same_type_treasure_counts[key] = count + 1
    best = setting._same_type_best_levels.get(key)
    if best is None or _level_cmp(current_levels, best) > 0:
        setting._same_type_best_levels[key] = current_levels
    return True


def _apply_stat_group_limit(
    setting: UserSetting,
    evaluation: EvaluationResult,
    stat_key: tuple[str | None, ...],
    current_levels: tuple[int, int, int],
    limit: int,
    keep_best: bool,
) -> EvaluationResult:
    """按基质分组（属性组合相同即为同类型）的限制逻辑。"""
    if keep_best and _claim_as_owned(setting, stat_key, current_levels):
        return evaluation
    if _claim_by_limit(setting, stat_key, current_levels, limit):
        return evaluation
    return _make_trash_by_limit(
        evaluation, setting._same_type_treasure_counts.get(stat_key, 0), limit
    )


def _apply_weapon_group_limit(
    setting: UserSetting,
    evaluation: EvaluationResult,
    matched_weapon_ids: set[str],
    current_levels: tuple[int, int, int],
    limit: int,
    keep_best: bool,
) -> EvaluationResult:
    """按武器分组（每把武器独立计数）的限制逻辑。"""
    weapon_ids = sorted(matched_weapon_ids)

    # 第一轮：优先认领属于某把武器的“已保存”基质（相等跳过 / 更优升级）。
    if keep_best:
        for weapon_id in weapon_ids:
            if _claim_as_owned(setting, weapon_id, current_levels):
                return evaluation

    # 第二轮：按数量上限分配给第一把未达上限的武器。
    for weapon_id in weapon_ids:
        if _claim_by_limit(setting, weapon_id, current_levels, limit):
            return evaluation

    # 所有匹配武器都已达上限
    return _make_trash_by_limit(evaluation, limit, limit)


def _apply_same_type_treasure_limit(
    data: EssenceData,
    setting: UserSetting,
    evaluation: EvaluationResult,
    matched_weapon_ids: set[str] | None = None,
) -> EvaluationResult:
    if (
        evaluation.quality != EssenceQuality.TREASURE
        or not setting.same_type_treasure_limit_enabled
    ):
        return evaluation

    limit = setting.same_type_treasure_limit
    keep_best = setting.same_type_keep_best
    current_levels = (
        data.levels[0] or 1,
        data.levels[1] or 1,
        data.levels[2] or 1,
    )

    if (
        setting.same_type_group_mode == SameTypeGroupMode.BY_WEAPON
        and matched_weapon_ids
    ):
        return _apply_weapon_group_limit(
            setting, evaluation, matched_weapon_ids, current_levels, limit, keep_best
        )

    # 默认按基质分组（包括自定义基质匹配和无匹配武器的情况）
    stat_key = tuple(data.stats)
    return _apply_stat_group_limit(
        setting, evaluation, stat_key, current_levels, limit, keep_best
    )


def evaluate_essence(
    data: EssenceData,
    setting: UserSetting,
    static_game_data: StaticGameData,
) -> EvaluationResult:
    """
    Pure function to judge the quality of an essence based on settings and game data.

    Logic:
    1. Checks high-level attributes thresholds (if enabled).
    2. Checks custom treasure stats (if configured).
    3. Matches against game data (weapons).
    4. Cross-references matched weapons with user's 'trash_weapon_ids'.
    5. Constructs the user-facing log message with color tags.

    Args:
        data: The raw recognition data (stats, levels).
        setting: The current user settings (thresholds, custom rules).
        static_game_data: The static game data for reference.
    Returns:
        EvaluationResult containing the decision, log message, and reasoning.
    """
    if data.rarity != RarityLabel.FIVE:
        if setting.non_five_star_behavior == NonFiveStarBehavior.SKIP:
            return EvaluationResult(
                quality=EssenceQuality.SKIP,
                log_message="这个基质是<dim>非无瑕基质</>，已根据设置跳过处理。",
            )
        if setting.non_five_star_behavior == NonFiveStarBehavior.STOP:
            return EvaluationResult(
                quality=EssenceQuality.SKIP,
                log_message="这个基质是<dim>非无瑕基质</>，已根据设置结束本次扫描。",
                stop_scan=True,
            )
        if setting.non_five_star_behavior == NonFiveStarBehavior.HIGH_LEVEL_ONLY:
            # 仅对非无瑕基质进行高等级属性词条判定，不判定武器匹配
            is_high_level, high_level_info = _evaluate_non_five_star_high_level(
                data, setting, static_game_data
            )
            if is_high_level:
                return _apply_same_type_treasure_limit(
                    data,
                    setting,
                    EvaluationResult(
                        quality=EssenceQuality.TREASURE,
                        log_message=f"这个基质是<green><bold><underline>宝藏</></></>（非无瑕基质），因为它有高等级属性词条{high_level_info}。",
                        is_high_level=True,
                    ),
                )
            else:
                return EvaluationResult(
                    quality=EssenceQuality.TRASH,
                    log_message="这个基质是<red><bold><underline>养成材料</></></>（非无瑕基质），它没有高等级属性词条。",
                    is_high_level=False,
                )

    stats = data.stats
    stat_types = data.stat_types

    is_high_level_treasure, high_level_info = _evaluate_high_level_treasure(
        data, setting, static_game_data
    )

    # 尝试匹配用户自定义的宝藏基质条件
    for treasure_stat in setting.treasure_essence_stats:
        if _matches_treasure_stats(
            treasure_stat, stats, stat_types, setting.treasure_essence_match_mode
        ):
            return _apply_same_type_treasure_limit(
                data,
                setting,
                EvaluationResult(
                    quality=EssenceQuality.TREASURE,
                    log_message=f"这个基质是<green><bold><underline>宝藏</></></>，因为它符合你设定的宝藏基质条件{high_level_info}。",
                    is_high_level=is_high_level_treasure,
                ),
            )

    # 按语义类型构建武器匹配三元组（每种类型取第一个出现的 stat）
    # 如果某类型缺失或重复，对应的字段为 None
    type_to_stat: dict[StatType, str | None] = {}
    for stat_id, stat_type in zip(stats, stat_types, strict=True):
        if stat_type is not None and stat_id is not None and stat_type not in type_to_stat:
            type_to_stat[stat_type] = stat_id
    weapon_attr = type_to_stat.get(StatType.ATTRIBUTE)
    weapon_sec = type_to_stat.get(StatType.SECONDARY)
    weapon_skill = type_to_stat.get(StatType.SKILL)

    # 尝试匹配已实装武器
    matched_weapon_ids = set(
        static_game_data.find_weapons_by_stats(weapon_attr, weapon_sec, weapon_skill)
    )

    if not matched_weapon_ids:
        # 未匹配到任何已实装武器
        if is_high_level_treasure:
            return _apply_same_type_treasure_limit(
                data,
                setting,
                EvaluationResult(
                    quality=EssenceQuality.TREASURE,
                    log_message=f"这个基质是<green><bold><underline>宝藏</></></>，因为它有高等级属性词条{high_level_info}。<dim>（但不匹配任何已实装武器）</>",
                    is_high_level=True,
                ),
            )
        else:
            return EvaluationResult(
                quality=EssenceQuality.TRASH,
                log_message="这个基质是<red><bold><underline>养成材料</></></>，它不匹配任何已实装武器。",
                is_high_level=False,
            )

    # 检查匹配到的武器中，是否有不在 trash_weapon_ids 中的
    non_trash_weapon_ids = matched_weapon_ids - set(setting.trash_weapon_ids)

    def format_weapon_description(weapon_id: str) -> str:
        """格式化武器描述，如`名称（稀有度★ 类型）`"""
        weapon = static_game_data.get_weapon(weapon_id)
        if not weapon:
            return f"<bold>{weapon_id}</>"

        weapon_type = static_game_data.get_weapon_type(weapon.weapon_type)
        type_name = weapon_type.name if weapon_type else "未知类型"

        rarity_color = static_game_data.get_rarity_color(weapon.rarity)
        return f"<fg {rarity_color}><bold>{weapon.name}（{weapon.rarity}★ {type_name}）</></>"

    if non_trash_weapon_ids:
        # 只要有一个匹配武器未被拦截，就是宝藏

        # 输出所有匹配到且未被拦截的武器列表
        weapon_descriptions = [
            format_weapon_description(wid) for wid in non_trash_weapon_ids
        ]
        weapons_description_str = "、".join(weapon_descriptions)

        return _apply_same_type_treasure_limit(
            data,
            setting,
            EvaluationResult(
                quality=EssenceQuality.TREASURE,
                log_message=f"这个基质是<green><bold><underline>宝藏</></></>，它完美契合武器{weapons_description_str}{high_level_info}。",
                matched_weapons=non_trash_weapon_ids,
                matched_weapons_all_blocked=False,
                is_high_level=is_high_level_treasure,
            ),
            matched_weapon_ids=non_trash_weapon_ids,
        )
    else:
        # 所有匹配到的武器都在 trash_weapon_ids 中

        # 输出所有匹配到的武器列表
        weapon_descriptions = [
            format_weapon_description(wid) for wid in matched_weapon_ids
        ]
        weapons_description_str = "、".join(weapon_descriptions)

        if is_high_level_treasure:
            return _apply_same_type_treasure_limit(
                data,
                setting,
                EvaluationResult(
                    quality=EssenceQuality.TREASURE,
                    log_message=f"这个基质是<green><bold><underline>宝藏</></></>，因为它有高等级属性词条{high_level_info}。<yellow>即使它匹配的所有武器{weapons_description_str}均已被用户手动拦截。</>",
                    matched_weapons=matched_weapon_ids,
                    matched_weapons_all_blocked=True,
                    is_high_level=True,
                ),
                matched_weapon_ids=matched_weapon_ids,
            )
        else:
            return EvaluationResult(
                quality=EssenceQuality.TRASH,
                log_message=f"这个基质虽然匹配武器{weapons_description_str}，但匹配的所有武器均已被用户手动拦截，因此这个基质是<red><bold><underline>养成材料</></></>。",
                matched_weapons=matched_weapon_ids,
                matched_weapons_all_blocked=True,
                is_high_level=False,
            )
