"""
多账号系统。

每个账号代表一个独立的游戏账号，拥有自己的设置和宝藏基质配置。
"""

from __future__ import annotations

from typing import ClassVar

from pydantic import BaseModel, Field


class MatrixViewConfig(BaseModel):
    """矩阵视图配置。"""

    show_owned_only: bool = False
    """是否只显示已拥有的基质组合。"""

    filter_weapon_type: str | None = None
    """武器类型过滤器（SWORD/CLAYM/LANCE/PISTOL/WAND），None 表示显示全部。"""

    filter_rarity: int | None = None
    """稀有度过滤器（3/4/5/6），None 表示显示全部。"""

    highlight_max_level: bool = True
    """是否高亮显示满级组合（6/6/3）。"""

    color_mode: str = "level"
    """颜色模式：'level'=按等级着色, 'rarity'=按稀有度着色, 'type'=按武器类型着色。"""

    cell_size: int = 60
    """单元格大小（像素）。"""

    show_code: bool = True
    """是否显示编码。"""

    show_level: bool = True
    """是否显示等级。"""

    show_weapon_icon: bool = True
    """是否显示武器图标。"""


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

    include_in_calculation: bool = True
    """是否参与刷取建议计算，满级（6/6/3）默认为False。"""

    priority: int = Field(default=0, ge=0)
    """武器优先级，数值越大优先级越高。默认值0表示使用稀有度作为默认优先级。"""


class ProfileData(BaseModel):
    """单个账号存储的数据。"""

    _VERSION: ClassVar[int] = 1

    version: int = _VERSION

    name: str = "default"
    """账号显示名称。"""

    treasure_matrix: list[TreasureMatrixEntry] = Field(default_factory=list)
    """此账号保存的宝藏基质配置。"""

    weapon_overview_filters: dict[str, bool] = Field(
        default_factory=lambda: {
            "3star": True,
            "4star": True,
            "5star": True,
            "6star": True,
            "custom": True,
        }
    )
    """武器总览的星级过滤器配置。"""

    weapon_priorities: dict[str, int] = Field(default_factory=dict)
    """武器优先级配置，允许未拥有宝藏基质的武器也设置优先级。"""

    switch_display_mode: str = "chip"
    """武器总览"可切换"提示的显示模式：'chip'=标签, 'dot'=小圆点, 'off'=关闭。"""

    matrix_badge_display_mode: str = "small"
    """武器总览基质图标显示模式：'small'=小号(默认), 'medium'=中号(2倍), 'off'=关闭。"""

    matrix_view_config: MatrixViewConfig = Field(default_factory=MatrixViewConfig)
    """矩阵视图配置。"""


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
