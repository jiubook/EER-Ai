"""
账号管理 API 路由。

提供管理多账号配置及其宝藏基质配置的接口。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from pydantic import BaseModel, Field

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

if TYPE_CHECKING:
    from endfield_essence_recognizer.game_data.static_game_data import StaticGameData
    from endfield_essence_recognizer.services.profile_manager import ProfileManager

router = APIRouter(prefix="/profiles", tags=["profiles"])

# 全局账号管理器实例（在应用启动时设置）
_profile_manager: ProfileManager | None = None


def get_profile_manager() -> ProfileManager:
    """获取全局账号管理器实例。"""
    if _profile_manager is None:
        raise RuntimeError("ProfileManager not initialized")
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


# --- 宝藏基质 ---


@router.get("/treasure_matrix")
async def get_treasure_matrix(
    manager: ProfileManager = Depends(get_profile_manager),
) -> list[TreasureMatrixEntry]:
    """获取当前激活账号的宝藏基质配置。"""
    return manager.get_active_profile().treasure_matrix


class UpdateTreasureMatrixRequest(BaseModel):
    entries: list[TreasureMatrixEntry]


@router.post("/treasure_matrix")
async def update_treasure_matrix(
    request: UpdateTreasureMatrixRequest,
    manager: ProfileManager = Depends(get_profile_manager),
) -> ProfileData:
    """更新当前激活账号的完整宝藏基质配置。"""
    return manager.update_treasure_matrix(request.entries)


class AddTreasureMatrixEntryRequest(BaseModel):
    weapon_id: str
    weapon_name: str = ""
    affix1_level: int = Field(default=1, ge=1, le=6)
    affix2_level: int = Field(default=1, ge=1, le=6)
    affix3_level: int = Field(default=1, ge=1, le=3)


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
    )
    return manager.add_treasure_matrix_entry(entry)


class RemoveTreasureMatrixEntryRequest(BaseModel):
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
    items: list[FarmingRequest]


@router.post("/farming_recommendations")
async def get_batch_farming_recommendations(
    request: BatchFarmingRequest,
    static_data: StaticGameData = Depends(get_static_game_data),
) -> list[FarmingRecommendation]:
    """批量计算多个武器的刷取建议。"""
    results = []
    for item in request.items:
        weapon = static_data.get_weapon(item.weapon_id)
        if weapon:
            try:
                results.append(
                    compute_farming_recommendation(
                        weapon_id=item.weapon_id,
                        weapon_name=weapon.name,
                        current_levels=item.current_levels,
                        target_levels=item.target_levels,
                    )
                )
            except ValueError as e:
                logger.warning("Skipping invalid batch entry {}: {}", item.weapon_id, e)
                continue
    return results
