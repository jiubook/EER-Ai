"""
多账号系统。

每个账号代表一个独立的游戏账号，拥有自己的设置和宝藏基质配置。
"""

from __future__ import annotations

from typing import ClassVar

from pydantic import BaseModel, Field


class TreasureMatrixEntry(BaseModel):
    """单个武器的宝藏基质配置及词条等级。"""

    weapon_id: str
    """武器 ID（例如 wpn_funnel_0009）。"""

    weapon_name: str = ""
    """武器显示名称（缓存以便使用）。"""

    affix1_level: int = Field(default=1, ge=1, le=6)
    """第一词条（属性）等级：1-6。"""

    affix2_level: int = Field(default=1, ge=1, le=6)
    """第二词条（副属性）等级：1-6。"""

    affix3_level: int = Field(default=1, ge=1, le=3)
    """第三词条（技能）等级：1-3。"""


class ProfileData(BaseModel):
    """单个账号存储的数据。"""

    _VERSION: ClassVar[int] = 1

    version: int = _VERSION

    name: str = "default"
    """账号显示名称。"""

    treasure_matrix: list[TreasureMatrixEntry] = []
    """此账号保存的宝藏基质配置。"""


class ProfileCollection(BaseModel):
    """所有账号的集合。"""

    _VERSION: ClassVar[int] = 1

    version: int = _VERSION

    active_profile: str = "default"
    """当前激活的账号名称。"""

    profiles: dict[str, ProfileData] = Field(default_factory=dict)
    """账号名称 -> 账号数据的映射。"""

    def get_active(self) -> ProfileData:
        """获取激活的账号数据，如果需要则创建默认账号。"""
        if self.active_profile not in self.profiles:
            self.profiles[self.active_profile] = ProfileData(name=self.active_profile)
        return self.profiles[self.active_profile]

    def ensure_default(self) -> None:
        """确保默认账号存在。"""
        if "default" not in self.profiles:
            self.profiles["default"] = ProfileData(name="default")
