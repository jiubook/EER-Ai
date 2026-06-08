from itertools import accumulate

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
    KeepBestMode,
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


# 冷却脂消耗模式下的累计冷却脂权重
# 从 1 级升到该等级所需的冷却脂总量（1/1/1 视作 0）
# 基础属性/附加属性（词条 1&2）：阈值 {1→2:30, 2→3:60, 3→4:120, 4→5:250, 5→6:450}
_GREASE_AFFIX_12 = tuple(
    accumulate((0, 0, 30, 60, 120, 250, 450))
)  # 索引 = 等级（1~6）
# 技能属性（词条 3）：阈值 {1→2:120, 2→3:300}
_GREASE_AFFIX_3 = tuple(accumulate((0, 0, 120, 300)))  # 索引 = 等级（1~3）

# 概率和值模式下的升级难度权重
# 累计期望基质数：从 1 级升到该等级所需的期望基质数量（等级越高越难升）
# 基础属性/附加属性（词条 1&2）：升级概率 {1→2:0.6, 2→3:0.24, 3→4:0.109, 4→5:0.05, 5→6:0.027}
_WEIGHTS_AFFIX_12 = tuple(
    accumulate((0, 0, 1 / 0.6, 1 / 0.24, 1 / 0.109, 1 / 0.05, 1 / 0.027))
)  # 索引 = 等级（1~6）
# 技能属性（词条 3）：升级概率 {1→2:0.109, 2→3:0.042}
_WEIGHTS_AFFIX_3 = tuple(accumulate((0, 0, 1 / 0.109, 1 / 0.042)))  # 索引 = 等级（1~3）


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
        for expected, expected_type in zip(
            configured_values, expected_types, strict=True
        )
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

    thresholds = [
        setting.high_level_treasure_attribute_threshold,
        setting.high_level_treasure_secondary_threshold,
        setting.high_level_treasure_skill_threshold,
    ]
    original_slot_matches = [
        stat_id is not None and level is not None and level >= threshold
        for stat_id, level, threshold in zip(stats, levels, thresholds, strict=True)
    ]

    if mode == TreasureMatchMode.ONLY:
        only_flags = [
            setting.high_level_treasure_only_check_attribute,
            setting.high_level_treasure_only_check_secondary,
            setting.high_level_treasure_only_check_skill,
        ]
        eval_matches = [
            m for m, f in zip(original_slot_matches, only_flags, strict=True) if f
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
        # 使用非无暇基质专用的高等级判定设置
        thresholds = [
            setting.non_five_star_high_level_attribute_threshold,
            setting.non_five_star_high_level_secondary_threshold,
            setting.non_five_star_high_level_skill_threshold,
        ]
        mode = setting.non_five_star_high_level_match_mode
        sum_threshold = setting.non_five_star_high_level_sum_threshold
        only_flags = [
            setting.non_five_star_high_level_only_check_attribute,
            setting.non_five_star_high_level_only_check_secondary,
            setting.non_five_star_high_level_only_check_skill,
        ]
    else:
        # 使用宝藏基质判定规则中的高等级设置
        if not setting.high_level_treasure_enabled:
            return False, ""
        thresholds = [
            setting.high_level_treasure_attribute_threshold,
            setting.high_level_treasure_secondary_threshold,
            setting.high_level_treasure_skill_threshold,
        ]
        mode = setting.high_level_treasure_match_mode
        sum_threshold = setting.high_level_treasure_sum_threshold
        only_flags = [
            setting.high_level_treasure_only_check_attribute,
            setting.high_level_treasure_only_check_secondary,
            setting.high_level_treasure_only_check_skill,
        ]

    stats = data.stats
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

    original_slot_matches = [
        stat_id is not None and level is not None and level >= threshold
        for stat_id, level, threshold in zip(stats, levels, thresholds, strict=True)
    ]

    if mode == TreasureMatchMode.ONLY:
        eval_matches = [
            m for m, f in zip(original_slot_matches, only_flags, strict=True) if f
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


def _weighted_sum(levels: tuple[int, int, int]) -> float:
    """计算等级元组的加权和（按升级难度加权）。

    权重为从 1 级升到该等级所需的期望基质数，等级越高越难升，权重越大。
    前两个词条（基础/附加）使用 _WEIGHTS_AFFIX_12，第三个词条（技能）使用 _WEIGHTS_AFFIX_3。
    """
    # 防止 OCR 识别出的异常等级值导致数组越界
    lv0 = min(max(levels[0], 0), len(_WEIGHTS_AFFIX_12) - 1)
    lv1 = min(max(levels[1], 0), len(_WEIGHTS_AFFIX_12) - 1)
    lv2 = min(max(levels[2], 0), len(_WEIGHTS_AFFIX_3) - 1)
    return _WEIGHTS_AFFIX_12[lv0] + _WEIGHTS_AFFIX_12[lv1] + _WEIGHTS_AFFIX_3[lv2]


def _grease_sum(levels: tuple[int, int, int]) -> float:
    """计算等级元组的冷却脂消耗总量（1/1/1 视作 0）。

    前两个词条（基础/附加）使用 _GREASE_AFFIX_12，第三个词条（技能）使用 _GREASE_AFFIX_3。
    """
    lv0 = min(max(levels[0], 0), len(_GREASE_AFFIX_12) - 1)
    lv1 = min(max(levels[1], 0), len(_GREASE_AFFIX_12) - 1)
    lv2 = min(max(levels[2], 0), len(_GREASE_AFFIX_3) - 1)
    return _GREASE_AFFIX_12[lv0] + _GREASE_AFFIX_12[lv1] + _GREASE_AFFIX_3[lv2]


def _level_cmp(
    current: tuple[int, int, int],
    existing: tuple[int, int, int],
    mode: KeepBestMode = KeepBestMode.SEQUENTIAL,
) -> int:
    """比较等级元组，返回 1（更优）/ 0（相等）/ -1（更差）。

    Args:
        current: 当前基质的三个词条等级。
        existing: 已保存的最佳基质的三个词条等级。
        mode: 比较模式：
            - SEQUENTIAL: 从左到右逐维度比较 A → B → C（原有行为）。
            - SUM: 比较三个词条等级之和 A + B + C。
            - GREASE: 按从 1 级升到该等级所需的冷却脂总量比较（1/1/1 视作 0）。
            - WEIGHTED_SUM: 按升级难度加权比较，等级越高越难升，权重越大。
    """
    if mode == KeepBestMode.SUM:
        # 和值比对：直接比较三词条等级之和
        cs, es = sum(current), sum(existing)
        if cs > es:
            return 1
        if cs < es:
            return -1
        return 0
    if mode == KeepBestMode.GREASE:
        # 冷却脂消耗：按从 1 级升到该等级的冷却脂总量比较
        cg, eg = _grease_sum(current), _grease_sum(existing)
        if cg > eg:
            return 1
        if cg < eg:
            return -1
        return 0
    if mode == KeepBestMode.WEIGHTED_SUM:
        # 概率和值：用升级期望基质数加权后比较
        cw = _weighted_sum(current)
        ew = _weighted_sum(existing)
        if cw > ew:
            return 1
        if cw < ew:
            return -1
        return 0
    # 依次比对（默认）：逐维度从左到右比较 A → B → C
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
    mode: KeepBestMode = KeepBestMode.SEQUENTIAL,
) -> bool:
    """留大弃小：判断当前基质是否属于该组"已保存"的那一枚（或其升级版）。

    - 相等：说明就是 profile 里保存的那一枚，在仍有跳过名额时直接认领（不占用数量上限）。
    - 更优：说明保存的那枚升级了，认领并把阈值提升到新等级，同时消耗一个已存名额。
    - 更差：返回 False，交由数量上限逻辑判断。

    Args:
        mode: 等级比较方式，由用户设置中的 same_type_keep_best_mode 决定。
    """
    best = setting._same_type_best_levels.get(key)
    if best is None:
        return False

    cmp = _level_cmp(current_levels, best, mode)
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
    mode: KeepBestMode = KeepBestMode.SEQUENTIAL,
) -> bool:
    """按数量上限认领当前基质：未达上限则保留并计数，同时维护最佳等级。

    Args:
        mode: 等级比较方式，用于判断新基质是否比已记录的最佳等级更优。
    """
    count = setting._same_type_treasure_counts.get(key, 0)
    if count >= limit:
        return False
    setting._same_type_treasure_counts[key] = count + 1
    best = setting._same_type_best_levels.get(key)
    if best is None or _level_cmp(current_levels, best, mode) > 0:
        setting._same_type_best_levels[key] = current_levels
    return True


def _apply_stat_group_limit(
    setting: UserSetting,
    evaluation: EvaluationResult,
    stat_key: tuple[str | None, ...],
    current_levels: tuple[int, int, int],
    limit: int,
    keep_best: bool,
    mode: KeepBestMode = KeepBestMode.SEQUENTIAL,
) -> EvaluationResult:
    """按基质分组（属性组合相同即为同类型）的限制逻辑。

    Args:
        mode: 等级比较方式，仅在 keep_best=True 时生效。
    """
    if keep_best and _claim_as_owned(setting, stat_key, current_levels, mode):
        return evaluation
    if _claim_by_limit(setting, stat_key, current_levels, limit, mode):
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
    mode: KeepBestMode = KeepBestMode.SEQUENTIAL,
) -> EvaluationResult:
    """按武器分组（每把武器独立计数）的限制逻辑。

    Args:
        mode: 等级比较方式，仅在 keep_best=True 时生效。
    """
    weapon_ids = sorted(matched_weapon_ids)

    # 第一轮：优先认领属于某把武器的"已保存"基质（相等跳过 / 更优升级）。
    if keep_best:
        for weapon_id in weapon_ids:
            if _claim_as_owned(setting, weapon_id, current_levels, mode):
                return evaluation

    # 第二轮：按数量上限分配给第一把未达上限的武器。
    for weapon_id in weapon_ids:
        if _claim_by_limit(setting, weapon_id, current_levels, limit, mode):
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
    mode = (
        setting.same_type_keep_best_mode
    )  # 留大弃小的等级比较方式（依次比对/和值比对/冷却脂消耗/概率和值）
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
            setting,
            evaluation,
            matched_weapon_ids,
            current_levels,
            limit,
            keep_best,
            mode,
        )

    # 默认按基质分组（包括自定义基质匹配和无匹配武器的情况）
    stat_key = tuple(data.stats)
    return _apply_stat_group_limit(
        setting, evaluation, stat_key, current_levels, limit, keep_best, mode
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

    is_high_level_treasure, high_level_info = _evaluate_high_level_treasure(
        data, setting, static_game_data
    )

    # 尝试匹配用户自定义的宝藏基质条件
    for treasure_stat in setting.treasure_essence_stats:
        if _matches_treasure_stats(
            treasure_stat, stats, data.stat_types, setting.treasure_essence_match_mode
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

    # 尝试匹配已实装武器
    matched_weapon_ids = set(
        static_game_data.find_weapons_by_stats(stats[0], stats[1], stats[2])
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
