"""
账号管理 API 路由。

提供管理多账号配置及其宝藏基质配置的接口。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from pydantic import BaseModel, Field, field_validator

from endfield_essence_recognizer.core.farming_calculator import (
    FarmingRecommendation,
    compute_farming_recommendation,
)
from endfield_essence_recognizer.dependencies import get_static_game_data
from endfield_essence_recognizer.schemas.profile import (
    ProfileCollection,
    ProfileData,
    TreasureMatrixEntry,
)
from endfield_essence_recognizer.utils.matrix_codec import (
    ATTRIBUTE_IDS,
    ATTRIBUTE_NAMES,
    SECONDARY_IDS,
    SECONDARY_NAMES,
    SKILL_IDS,
    SKILL_NAMES,
    encode_matrix,
)

if TYPE_CHECKING:
    from endfield_essence_recognizer.game_data.static_game_data import StaticGameData
    from endfield_essence_recognizer.services.profile_manager import ProfileManager

router = APIRouter(prefix="/profiles", tags=["profiles"])

# 全局账号管理器实例（在应用启动时设置）
_profile_manager: ProfileManager | None = None


def get_profile_manager() -> ProfileManager:
    """获取全局账号管理器实例。"""
    if _profile_manager is None:
        raise HTTPException(status_code=503, detail="Profile manager not initialized")
    return _profile_manager


def set_profile_manager(manager: ProfileManager) -> None:
    """设置全局账号管理器实例。"""
    global _profile_manager
    _profile_manager = manager


# --- 账号 CRUD ---


@router.get("")
async def list_profiles(
    manager: ProfileManager = Depends(get_profile_manager),
) -> ProfileCollection:
    """获取所有账号及当前激活的账号名称。"""
    return manager.get_collection()


@router.get("/active")
async def get_active_profile(
    manager: ProfileManager = Depends(get_profile_manager),
) -> ProfileData:
    """获取当前激活的账号数据。"""
    return manager.get_active_profile()


class SwitchProfileRequest(BaseModel):
    """切换账号请求体。"""

    name: str


@router.post("/switch")
async def switch_profile(
    request: SwitchProfileRequest,
    manager: ProfileManager = Depends(get_profile_manager),
) -> ProfileData:
    """切换到不同的账号。"""
    try:
        return manager.switch_profile(request.name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


class RenameProfileRequest(BaseModel):
    """重命名账号请求体。"""

    old_name: str
    new_name: str


@router.post("/rename")
async def rename_profile(
    request: RenameProfileRequest,
    manager: ProfileManager = Depends(get_profile_manager),
) -> ProfileData:
    """重命名账号。"""
    try:
        return manager.rename_profile(request.old_name, request.new_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


class DeleteProfileRequest(BaseModel):
    """删除账号请求体。"""

    name: str


@router.post("/delete")
async def delete_profile(
    request: DeleteProfileRequest,
    manager: ProfileManager = Depends(get_profile_manager),
) -> dict[str, str]:
    """删除账号。"""
    try:
        manager.delete_profile(request.name)
        return {"status": "ok"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


class ClearProfileDataRequest(BaseModel):
    """清空账号数据请求体。"""

    name: str | None = None


@router.post("/clear_data")
async def clear_profile_data(
    request: ClearProfileDataRequest | None = None,
    manager: ProfileManager = Depends(get_profile_manager),
) -> ProfileData:
    """清空账号的宝藏基质数据（不删除账号）。

    name 为空时清空当前激活账号的数据。
    """
    try:
        return manager.clear_profile_data(request.name if request else None)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


# --- 宝藏基质 ---


@router.get("/treasure_matrix")
async def get_treasure_matrix(
    manager: ProfileManager = Depends(get_profile_manager),
) -> list[TreasureMatrixEntry]:
    """获取当前激活账号的宝藏基质配置。"""
    return manager.get_active_profile().treasure_matrix


class UpdateTreasureMatrixRequest(BaseModel):
    """更新完整宝藏基质配置的请求体。"""

    entries: list[TreasureMatrixEntry]


@router.post("/treasure_matrix")
async def update_treasure_matrix(
    request: UpdateTreasureMatrixRequest,
    manager: ProfileManager = Depends(get_profile_manager),
) -> ProfileData:
    """更新当前激活账号的完整宝藏基质配置。"""
    return manager.update_treasure_matrix(request.entries)


class AddTreasureMatrixEntryRequest(BaseModel):
    """新增或更新单个宝藏基质条目的请求体。"""

    weapon_id: str
    weapon_name: str = ""
    affix1_level: int = Field(default=1, ge=1, le=6)
    affix2_level: int = Field(default=1, ge=1, le=6)
    affix3_level: int = Field(default=1, ge=1, le=3)
    include_in_calculation: bool = True


@router.post("/treasure_matrix/add")
async def add_treasure_matrix_entry(
    request: AddTreasureMatrixEntryRequest,
    manager: ProfileManager = Depends(get_profile_manager),
) -> ProfileData:
    """添加或更新单个宝藏基质条目。"""
    entry = TreasureMatrixEntry(
        weapon_id=request.weapon_id,
        weapon_name=request.weapon_name,
        affix1_level=request.affix1_level,
        affix2_level=request.affix2_level,
        affix3_level=request.affix3_level,
        include_in_calculation=request.include_in_calculation,
    )
    return manager.add_treasure_matrix_entry(entry)


class RemoveTreasureMatrixEntryRequest(BaseModel):
    """移除单个宝藏基质条目的请求体。"""

    weapon_id: str


@router.post("/treasure_matrix/remove")
async def remove_treasure_matrix_entry(
    request: RemoveTreasureMatrixEntryRequest,
    manager: ProfileManager = Depends(get_profile_manager),
) -> ProfileData:
    """移除宝藏基质条目。"""
    return manager.remove_treasure_matrix_entry(request.weapon_id)


# --- 刷取建议 ---


class FarmingRequest(BaseModel):
    """计算单把武器刷取建议的请求体。"""

    weapon_id: str
    current_levels: tuple[int, int, int] = Field(
        default=(1, 1, 1),
        description="当前词条等级 (基础属性1-6, 附加属性1-6, 技能属性1-3)",
    )
    target_levels: tuple[int, int, int] = Field(
        default=(6, 6, 3),
        description="目标词条等级 (基础属性1-6, 附加属性1-6, 技能属性1-3)",
    )


@router.post("/farming_recommendation")
async def get_farming_recommendation(
    request: FarmingRequest,
    static_data: StaticGameData = Depends(get_static_game_data),
) -> FarmingRecommendation:
    """计算武器宝藏基质的刷取建议。"""
    weapon = static_data.get_weapon(request.weapon_id)
    if not weapon:
        raise HTTPException(status_code=404, detail="Weapon not found")

    try:
        return compute_farming_recommendation(
            weapon_id=request.weapon_id,
            weapon_name=weapon.name,
            current_levels=request.current_levels,
            target_levels=request.target_levels,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


class BatchFarmingRequest(BaseModel):
    """批量计算刷取建议的请求体。"""

    items: list[FarmingRequest] = Field(default_factory=list, max_length=100)


class BatchFarmingItemResult(BaseModel):
    """单个批量刷取建议的计算结果。"""

    weapon_id: str
    recommendation: FarmingRecommendation | None = None
    error: str | None = None


@router.post("/farming_recommendations")
async def get_batch_farming_recommendations(
    request: BatchFarmingRequest,
    static_data: StaticGameData = Depends(get_static_game_data),
) -> list[BatchFarmingItemResult]:
    """批量计算多个武器的刷取建议。"""
    results: list[BatchFarmingItemResult] = []
    for item in request.items:
        weapon = static_data.get_weapon(item.weapon_id)
        if weapon:
            weapon_name = weapon.name
        elif item.weapon_id.startswith("custom_stat_"):
            weapon_name = item.weapon_id
        else:
            results.append(
                BatchFarmingItemResult(
                    weapon_id=item.weapon_id,
                    error="Weapon not found",
                )
            )
            continue

        try:
            recommendation = compute_farming_recommendation(
                weapon_id=item.weapon_id,
                weapon_name=weapon_name,
                current_levels=item.current_levels,
                target_levels=item.target_levels,
            )
            results.append(
                BatchFarmingItemResult(
                    weapon_id=item.weapon_id,
                    recommendation=recommendation,
                )
            )
        except ValueError as e:
            logger.warning("Invalid batch entry {}: {}", item.weapon_id, e)
            results.append(
                BatchFarmingItemResult(
                    weapon_id=item.weapon_id,
                    error=str(e),
                )
            )
    return results


# --- 武器总览过滤器 ---


VALID_RARITY_FILTERS = ("3star", "4star", "5star", "6star", "custom")


class UpdateWeaponOverviewFiltersRequest(BaseModel):
    """更新武器总览星级过滤器的请求体。"""

    filters: dict[str, bool] = Field(
        default_factory=lambda: dict.fromkeys(VALID_RARITY_FILTERS, True)
    )

    @field_validator("filters")
    @classmethod
    def validate_filters(cls, value: dict[str, bool]) -> dict[str, bool]:
        """校验并补齐星级过滤器配置。"""
        unknown = set(value) - set(VALID_RARITY_FILTERS)
        if unknown:
            raise ValueError(f"未知星级过滤器: {sorted(unknown)}")
        return {key: bool(value.get(key, True)) for key in VALID_RARITY_FILTERS}


@router.post("/weapon_overview_filters")
async def update_weapon_overview_filters(
    request: UpdateWeaponOverviewFiltersRequest,
    manager: ProfileManager = Depends(get_profile_manager),
) -> ProfileData:
    """更新当前激活账号的武器总览过滤器配置。"""
    return manager.update_weapon_overview_filters(request.filters)


VALID_SWITCH_MODES = {"chip", "dot", "off"}


class UpdateSwitchDisplayModeRequest(BaseModel):
    """更新"可切换"提示显示模式的请求体。"""

    mode: str

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, value: str) -> str:
        if value not in VALID_SWITCH_MODES:
            raise ValueError(
                f"未知显示模式: {value}，可选: {sorted(VALID_SWITCH_MODES)}"
            )
        return value


@router.post("/switch_display_mode")
async def update_switch_display_mode(
    request: UpdateSwitchDisplayModeRequest,
    manager: ProfileManager = Depends(get_profile_manager),
) -> ProfileData:
    """更新当前激活账号的"可切换"提示显示模式。"""
    return manager.update_switch_display_mode(request.mode)


VALID_MATRIX_BADGE_MODES: Final = {"small", "medium", "off"}


class UpdateMatrixBadgeDisplayModeRequest(BaseModel):
    """更新基质图标显示模式的请求体。"""

    mode: str

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, value: str) -> str:
        if value not in VALID_MATRIX_BADGE_MODES:
            raise ValueError(
                f"未知显示模式: {value}，可选: {sorted(VALID_MATRIX_BADGE_MODES)}"
            )
        return value


@router.post("/matrix_badge_display_mode")
async def update_matrix_badge_display_mode(
    request: UpdateMatrixBadgeDisplayModeRequest,
    manager: ProfileManager = Depends(get_profile_manager),
) -> ProfileData:
    """更新当前激活账号的基质图标显示模式。"""
    return manager.update_matrix_badge_display_mode(request.mode)


class UpdateWeaponPriorityRequest(BaseModel):
    """更新单把武器优先级的请求体。"""

    weapon_id: str
    priority: int = Field(default=0, ge=0, le=9)


@router.post("/weapon_priority")
async def update_weapon_priority(
    request: UpdateWeaponPriorityRequest,
    manager: ProfileManager = Depends(get_profile_manager),
) -> ProfileData:
    """更新当前激活账号的单个武器优先级。"""
    return manager.update_weapon_priority(request.weapon_id, request.priority)


# --- 矩阵视图 ---


class MatrixCellData(BaseModel):
    """矩阵单元格数据。"""

    code: str
    """6位编码。"""

    weapon_id: str | None = None
    """武器ID（如果已拥有）。"""

    weapon_name: str | None = None
    """武器名称（如果已拥有）。"""

    weapon_rarity: int | None = None
    """武器稀有度（如果已拥有）。"""

    weapon_type: str | None = None
    """武器类型（如果已拥有）。"""

    attribute_id: str
    """基础属性 ID。"""

    attribute_name: str
    """基础属性名称。"""

    attribute_level: int
    """基础属性等级。"""

    secondary_id: str
    """附加属性 ID。"""

    secondary_name: str
    """附加属性名称。"""

    secondary_level: int
    """附加属性等级。"""

    skill_id: str
    """技能属性 ID。"""

    skill_name: str
    """技能属性名称。"""

    skill_level: int
    """技能属性等级。"""

    owned: bool = False
    """是否已拥有。"""

    is_max_level: bool = False
    """是否满级（6/6/3）。"""


class MatrixViewResponse(BaseModel):
    """矩阵视图响应。"""

    matrix: dict[str, MatrixCellData]
    """编码 -> 单元格数据的映射。"""

    stats: dict
    """统计信息。"""

    attribute_ids: list[str]
    """基础属性 ID 列表（有序）。"""

    secondary_ids: list[str]
    """附加属性 ID 列表（有序）。"""

    skill_ids: list[str]
    """技能属性 ID 列表（有序）。"""

    attribute_names: dict[str, str]
    """基础属性 ID -> 名称映射。"""

    secondary_names: dict[str, str]
    """附加属性 ID -> 名称映射。"""

    skill_names: dict[str, str]
    """技能属性 ID -> 名称映射。"""


@router.get("/matrix_view")
async def get_matrix_view(
    profile: str | None = None,
    manager: ProfileManager = Depends(get_profile_manager),
    static_data: StaticGameData = Depends(get_static_game_data),
) -> MatrixViewResponse:
    """获取矩阵视图数据。

    Args:
        profile: 账号名称，None 表示使用当前激活账号。
    """
    # 获取账号数据
    if profile:
        try:
            profile_data = manager.get_profile(profile)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e
    else:
        profile_data = manager.get_active_profile()

    # 构建武器查找表（weapon_id -> weapon_info）
    weapon_lookup: dict[str, dict] = {}
    for weapon in static_data.list_weapons():
        if weapon.stat1_id and weapon.stat2_id and weapon.stat3_id:
            weapon_lookup[weapon.weapon_id] = {
                "weapon_id": weapon.weapon_id,
                "weapon_name": weapon.name,
                "weapon_rarity": weapon.rarity,
                "weapon_type": weapon.weapon_type,
                "attribute_id": weapon.stat1_id,
                "secondary_id": weapon.stat2_id,
                "skill_id": weapon.stat3_id,
            }

    # 构建用户的基质配置查找表
    user_matrix: dict[str, TreasureMatrixEntry] = {}
    for entry in profile_data.treasure_matrix:
        user_matrix[entry.weapon_id] = entry

    # 生成矩阵数据
    matrix: dict[str, MatrixCellData] = {}
    total_count = 0
    owned_count = 0
    max_level_count = 0

    # 遍历所有可能的组合
    for attr_id in ATTRIBUTE_IDS:
        for sec_id in SECONDARY_IDS:
            for skill_id in SKILL_IDS:
                # 查找对应的武器
                weapon_info = None
                for w in weapon_lookup.values():
                    if (
                        w["attribute_id"] == attr_id
                        and w["secondary_id"] == sec_id
                        and w["skill_id"] == skill_id
                    ):
                        weapon_info = w
                        break

                # 遍历所有等级组合
                for attr_level in range(1, 7):
                    for sec_level in range(1, 7):
                        for skill_level in range(1, 4):
                            # 编码
                            code = encode_matrix(
                                attr_id,
                                sec_id,
                                skill_id,
                                attr_level,
                                sec_level,
                                skill_level,
                            )
                            total_count += 1

                            # 检查用户是否拥有
                            owned = False
                            weapon_id = None
                            weapon_name = None
                            weapon_rarity = None
                            weapon_type = None
                            is_max_level = False

                            if weapon_info:
                                weapon_id = weapon_info["weapon_id"]
                                if weapon_id in user_matrix:
                                    entry = user_matrix[weapon_id]
                                    # 检查等级是否匹配
                                    if (
                                        entry.affix1_level == attr_level
                                        and entry.affix2_level == sec_level
                                        and entry.affix3_level == skill_level
                                    ):
                                        owned = True
                                        weapon_name = weapon_info["weapon_name"]
                                        weapon_rarity = weapon_info["weapon_rarity"]
                                        weapon_type = weapon_info["weapon_type"]
                                        owned_count += 1

                                        # 检查是否满级
                                        if (
                                            attr_level == 6
                                            and sec_level == 6
                                            and skill_level == 3
                                        ):
                                            is_max_level = True
                                            max_level_count += 1

                            matrix[code] = MatrixCellData(
                                code=code,
                                weapon_id=weapon_id,
                                weapon_name=weapon_name,
                                weapon_rarity=weapon_rarity,
                                weapon_type=weapon_type,
                                attribute_id=attr_id,
                                attribute_name=ATTRIBUTE_NAMES.get(attr_id, attr_id),
                                attribute_level=attr_level,
                                secondary_id=sec_id,
                                secondary_name=SECONDARY_NAMES.get(sec_id, sec_id),
                                secondary_level=sec_level,
                                skill_id=skill_id,
                                skill_name=SKILL_NAMES.get(skill_id, skill_id),
                                skill_level=skill_level,
                                owned=owned,
                                is_max_level=is_max_level,
                            )

    return MatrixViewResponse(
        matrix=matrix,
        stats={
            "total": total_count,
            "owned": owned_count,
            "max_level": max_level_count,
            "completion_rate": round(owned_count / total_count * 100, 2)
            if total_count > 0
            else 0,
        },
        attribute_ids=ATTRIBUTE_IDS,
        secondary_ids=SECONDARY_IDS,
        skill_ids=SKILL_IDS,
        attribute_names=ATTRIBUTE_NAMES,
        secondary_names=SECONDARY_NAMES,
        skill_names=SKILL_NAMES,
    )


class UpdateMatrixViewConfigRequest(BaseModel):
    """更新矩阵视图配置的请求体。"""

    show_owned_only: bool | None = None
    filter_weapon_type: str | None = None
    filter_rarity: int | None = None
    highlight_max_level: bool | None = None
    color_mode: str | None = None
    cell_size: int | None = None
    show_code: bool | None = None
    show_level: bool | None = None
    show_weapon_icon: bool | None = None


@router.post("/matrix_view_config")
async def update_matrix_view_config(
    request: UpdateMatrixViewConfigRequest,
    manager: ProfileManager = Depends(get_profile_manager),
) -> ProfileData:
    """更新当前激活账号的矩阵视图配置。"""
    return manager.update_matrix_view_config(request.model_dump(exclude_none=True))


class MatrixStatsResponse(BaseModel):
    """矩阵统计响应。"""

    total_combinations: int
    """总组合数。"""

    owned_combinations: int
    """已拥有组合数。"""

    max_level_combinations: int
    """满级组合数。"""

    completion_rate: float
    """完成百分比。"""

    by_attribute: dict[str, dict]
    """按基础属性分组的统计。"""

    by_secondary: dict[str, dict]
    """按附加属性分组的统计。"""

    by_skill: dict[str, dict]
    """按技能属性分组的统计。"""

    by_weapon_type: dict[str, dict]
    """按武器类型分组的统计。"""

    by_rarity: dict[str, dict]
    """按稀有度分组的统计。"""


@router.get("/matrix_stats")
async def get_matrix_stats(
    profile: str | None = None,
    manager: ProfileManager = Depends(get_profile_manager),
    static_data: StaticGameData = Depends(get_static_game_data),
) -> MatrixStatsResponse:
    """获取矩阵统计信息。"""
    # 获取账号数据
    if profile:
        try:
            profile_data = manager.get_profile(profile)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e
    else:
        profile_data = manager.get_active_profile()

    # 构建武器查找表
    weapon_lookup: dict[str, dict] = {}
    for weapon in static_data.list_weapons():
        if weapon.stat1_id and weapon.stat2_id and weapon.stat3_id:
            weapon_lookup[weapon.weapon_id] = {
                "weapon_id": weapon.weapon_id,
                "weapon_name": weapon.name,
                "weapon_rarity": weapon.rarity,
                "weapon_type": weapon.weapon_type,
                "attribute_id": weapon.stat1_id,
                "secondary_id": weapon.stat2_id,
                "skill_id": weapon.stat3_id,
            }

    # 构建用户的基质配置查找表
    user_matrix: dict[str, TreasureMatrixEntry] = {}
    for entry in profile_data.treasure_matrix:
        user_matrix[entry.weapon_id] = entry

    # 统计
    total_combinations = 0
    owned_combinations = 0
    max_level_combinations = 0

    by_attribute: dict[str, dict] = {
        attr_id: {"total": 0, "owned": 0, "max_level": 0} for attr_id in ATTRIBUTE_IDS
    }
    by_secondary: dict[str, dict] = {
        sec_id: {"total": 0, "owned": 0, "max_level": 0} for sec_id in SECONDARY_IDS
    }
    by_skill: dict[str, dict] = {
        skill_id: {"total": 0, "owned": 0, "max_level": 0} for skill_id in SKILL_IDS
    }
    by_weapon_type: dict[str, dict] = {}
    by_rarity: dict[str, dict] = {}

    # 遍历所有可能的组合
    for attr_id in ATTRIBUTE_IDS:
        for sec_id in SECONDARY_IDS:
            for skill_id in SKILL_IDS:
                # 查找对应的武器
                weapon_info = None
                for w in weapon_lookup.values():
                    if (
                        w["attribute_id"] == attr_id
                        and w["secondary_id"] == sec_id
                        and w["skill_id"] == skill_id
                    ):
                        weapon_info = w
                        break

                # 遍历所有等级组合
                for attr_level in range(1, 7):
                    for sec_level in range(1, 7):
                        for skill_level in range(1, 4):
                            total_combinations += 1
                            by_attribute[attr_id]["total"] += 1
                            by_secondary[sec_id]["total"] += 1
                            by_skill[skill_id]["total"] += 1

                            # 检查用户是否拥有
                            if weapon_info:
                                weapon_id = weapon_info["weapon_id"]
                                if weapon_id in user_matrix:
                                    entry = user_matrix[weapon_id]
                                    if (
                                        entry.affix1_level == attr_level
                                        and entry.affix2_level == sec_level
                                        and entry.affix3_level == skill_level
                                    ):
                                        owned_combinations += 1
                                        by_attribute[attr_id]["owned"] += 1
                                        by_secondary[sec_id]["owned"] += 1
                                        by_skill[skill_id]["owned"] += 1

                                        # 按武器类型统计
                                        weapon_type = weapon_info["weapon_type"]
                                        if weapon_type not in by_weapon_type:
                                            by_weapon_type[weapon_type] = {
                                                "total": 0,
                                                "owned": 0,
                                                "max_level": 0,
                                            }
                                        by_weapon_type[weapon_type]["owned"] += 1

                                        # 按稀有度统计
                                        rarity = weapon_info["weapon_rarity"]
                                        rarity_key = f"{rarity}star"
                                        if rarity_key not in by_rarity:
                                            by_rarity[rarity_key] = {
                                                "total": 0,
                                                "owned": 0,
                                                "max_level": 0,
                                            }
                                        by_rarity[rarity_key]["owned"] += 1

                                        # 检查是否满级
                                        if (
                                            attr_level == 6
                                            and sec_level == 6
                                            and skill_level == 3
                                        ):
                                            max_level_combinations += 1
                                            by_attribute[attr_id]["max_level"] += 1
                                            by_secondary[sec_id]["max_level"] += 1
                                            by_skill[skill_id]["max_level"] += 1
                                            if weapon_type in by_weapon_type:
                                                by_weapon_type[weapon_type][
                                                    "max_level"
                                                ] += 1
                                            if rarity_key in by_rarity:
                                                by_rarity[rarity_key]["max_level"] += 1

    # 计算总数（用于百分比）
    for attr_id in ATTRIBUTE_IDS:
        by_attribute[attr_id]["completion_rate"] = (
            round(
                by_attribute[attr_id]["owned"] / by_attribute[attr_id]["total"] * 100, 2
            )
            if by_attribute[attr_id]["total"] > 0
            else 0
        )

    for sec_id in SECONDARY_IDS:
        by_secondary[sec_id]["completion_rate"] = (
            round(
                by_secondary[sec_id]["owned"] / by_secondary[sec_id]["total"] * 100, 2
            )
            if by_secondary[sec_id]["total"] > 0
            else 0
        )

    for skill_id in SKILL_IDS:
        by_skill[skill_id]["completion_rate"] = (
            round(by_skill[skill_id]["owned"] / by_skill[skill_id]["total"] * 100, 2)
            if by_skill[skill_id]["total"] > 0
            else 0
        )

    for _weapon_type, data in by_weapon_type.items():
        data["completion_rate"] = (
            round(data["owned"] / data["total"] * 100, 2) if data["total"] > 0 else 0
        )

    for _rarity_key, data in by_rarity.items():
        data["completion_rate"] = (
            round(data["owned"] / data["total"] * 100, 2) if data["total"] > 0 else 0
        )

    return MatrixStatsResponse(
        total_combinations=total_combinations,
        owned_combinations=owned_combinations,
        max_level_combinations=max_level_combinations,
        completion_rate=round(owned_combinations / total_combinations * 100, 2)
        if total_combinations > 0
        else 0,
        by_attribute=by_attribute,
        by_secondary=by_secondary,
        by_skill=by_skill,
        by_weapon_type=by_weapon_type,
        by_rarity=by_rarity,
    )
