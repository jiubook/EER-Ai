from endfield_essence_recognizer.core.recognition import RarityLabel
from endfield_essence_recognizer.core.scanner.models import (
    EssenceData,
    EssenceQuality,
    EvaluationResult,
)
from endfield_essence_recognizer.game_data.static_game_data import StaticGameData
from endfield_essence_recognizer.schemas.user_setting import (
    EssenceStats,
    NonFiveStarBehavior,
    TreasureMatchMode,
    UserSetting,
)

STAT_SLOTS = ("attribute", "secondary", "skill")


def _matches_by_mode(matches: list[bool], configured_count: int, mode: TreasureMatchMode) -> bool:
    if configured_count == 0:
        return False
    if mode == TreasureMatchMode.ANY:
        return any(matches)
    if mode == TreasureMatchMode.ALL:
        return configured_count == len(STAT_SLOTS) and all(matches)
    return all(matches)


def _matches_treasure_stats(
    treasure_stat: EssenceStats, stats: list[str | None], mode: TreasureMatchMode
) -> bool:
    configured_values = [
        treasure_stat.attribute,
        treasure_stat.secondary,
        treasure_stat.skill,
    ]
    matches = [
        expected == actual
        for expected, actual in zip(configured_values, stats, strict=True)
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

    if setting.high_level_treasure_stats:
        for treasure_stat in setting.high_level_treasure_stats:
            configured_values = [
                treasure_stat.attribute,
                treasure_stat.secondary,
                treasure_stat.skill,
            ]
            thresholds = [
                treasure_stat.attribute_threshold,
                treasure_stat.secondary_threshold,
                treasure_stat.skill_threshold,
            ]
            slot_matches: list[bool] = []
            matched_indexes: list[int] = []
            for index, (expected, actual, level, threshold) in enumerate(
                zip(configured_values, stats, levels, thresholds, strict=True)
            ):
                if expected is None:
                    continue
                is_match = expected == actual and level is not None and level >= threshold
                slot_matches.append(is_match)
                if is_match:
                    matched_indexes.append(index)

            if _matches_by_mode(slot_matches, len(slot_matches), mode):
                return True, _format_high_level_info(
                    static_game_data, stats, levels, matched_indexes
                )
        return False, ""

    thresholds = [
        setting.high_level_treasure_attribute_threshold,
        setting.high_level_treasure_secondary_threshold,
        setting.high_level_treasure_skill_threshold,
    ]
    slot_matches = [
        stat_id is not None and level is not None and level >= threshold
        for stat_id, level, threshold in zip(stats, levels, thresholds, strict=True)
    ]

    if mode == TreasureMatchMode.ANY:
        matched_indexes = [index for index, is_match in enumerate(slot_matches) if is_match]
    else:
        matched_indexes = list(range(len(STAT_SLOTS))) if all(slot_matches) else []

    if not _matches_by_mode(slot_matches, len(slot_matches), mode):
        return False, ""

    return True, _format_high_level_info(static_game_data, stats, levels, matched_indexes)


def _apply_same_type_treasure_limit(
    data: EssenceData,
    setting: UserSetting,
    evaluation: EvaluationResult,
) -> EvaluationResult:
    if (
        evaluation.quality != EssenceQuality.TREASURE
        or not setting.same_type_treasure_limit_enabled
    ):
        return evaluation

    stat_key = tuple(data.stats)
    current_count = setting._same_type_treasure_counts.get(stat_key, 0)
    limit = setting.same_type_treasure_limit
    if current_count >= limit:
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

    setting._same_type_treasure_counts[stat_key] = current_count + 1
    return evaluation


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

    stats = data.stats

    is_high_level_treasure, high_level_info = _evaluate_high_level_treasure(
        data, setting, static_game_data
    )

    # 尝试匹配用户自定义的宝藏基质条件
    for treasure_stat in setting.treasure_essence_stats:
        if _matches_treasure_stats(
            treasure_stat, stats, setting.treasure_essence_match_mode
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
            )
        else:
            return EvaluationResult(
                quality=EssenceQuality.TRASH,
                log_message=f"这个基质虽然匹配武器{weapons_description_str}，但匹配的所有武器均已被用户手动拦截，因此这个基质是<red><bold><underline>养成材料</></></>。",
                matched_weapons=matched_weapon_ids,
                matched_weapons_all_blocked=True,
                is_high_level=False,
            )
