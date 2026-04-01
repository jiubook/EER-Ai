from __future__ import annotations

from enum import StrEnum
from typing import Any, ClassVar

from pydantic import BaseModel, Field


class Action(StrEnum):
    KEEP = "keep"
    LOCK = "lock"
    DEPRECATE = "deprecate"
    UNLOCK = "unlock"
    UNDEPRECATE = "undeprecate"
    UNLOCK_AND_UNDEPRECATE = "unlock_and_undeprecate"
    DEPRECATE_IF_NOT_LOCKED = "deprecate_if_not_locked"
    LOCK_IF_NOT_DEPRECATED = "lock_if_not_deprecated"


class NonFiveStarBehavior(StrEnum):
    """Enumeration of behaviors for non-5-star essences.

    5-star 即高纯基质（黄色），非5-star即非高纯基质。
    """

    PROCESS = "process"
    """Process non-5-star essences normally according to other rules."""

    SKIP = "skip"
    """Skip any operations on non-5-star essences."""


class EssenceStats(BaseModel):
    attribute: str | None
    secondary: str | None
    skill: str | None


class UserSetting(BaseModel):
    _VERSION: ClassVar[int] = 4

    version: int = _VERSION

    trash_weapon_ids: list[str] = []
    treasure_essence_stats: list[EssenceStats] = []

    treasure_action: Action = Action.LOCK
    trash_action: Action = Action.UNLOCK

    non_five_star_behavior: NonFiveStarBehavior = NonFiveStarBehavior.PROCESS
    """如何处理非高纯基质：正常处理或直接跳过。"""

    high_level_treasure_enabled: bool = False
    """是否启用高等级基质属性词条判定为宝藏"""
    high_level_treasure_attribute_threshold: int = Field(default=3, ge=1, le=6)
    """高等级基础属性词条的等级阈值（+1~+6）"""
    high_level_treasure_secondary_threshold: int = Field(default=3, ge=1, le=6)
    """高等级附加属性词条的等级阈值（+1~+6）"""
    high_level_treasure_skill_threshold: int = Field(default=3, ge=1, le=3)
    """高等级技能属性词条的等级阈值（+1~+3）"""

    auto_page_flip: bool = True
    """扫描时是否自动翻页"""

    update_mirror: str = "github"
    """更新镜像源：github, ghproxy, fastgit"""
    update_proxy: str = ""
    """更新代理地址，如 http://127.0.0.1:7890"""

    @staticmethod
    def _migrate_v2_to_v3(data: dict) -> None:
        """v2 → v3: 补充 v2 期间新增但未更新版本号的字段"""
        data.setdefault("non_five_star_behavior", "process")
        data.setdefault("auto_page_flip", True)

    @staticmethod
    def _migrate_v3_to_v4(data: dict) -> None:
        """v3 → v4: 添加更新镜像源和代理配置"""
        data.setdefault("update_mirror", "github")
        data.setdefault("update_proxy", "")

    # 迁移函数映射表：版本号 -> 迁移函数
    _MIGRATIONS: ClassVar[dict[int, Any]] = {
        2: _migrate_v2_to_v3,
        3: _migrate_v3_to_v4,
    }

    @classmethod
    def migrate_from_old_version(cls, old_data: dict) -> UserSetting:
        """从旧版本配置迁移到当前版本

        Args:
            old_data: 旧版本的配置字典

        Returns:
            迁移后的 UserSetting 实例

        Raises:
            ValueError: 如果版本号无效或缺少迁移路径
        """
        old_version = old_data.get("version", 1)

        # 验证版本号有效性
        if old_version < 1:
            raise ValueError(f"无效的配置版本: {old_version}")
        if old_version > cls._VERSION:
            raise ValueError("配置文件版本过高，请更新程序")

        # 链式迁移：逐版本升级
        while old_version < cls._VERSION:
            if old_version not in cls._MIGRATIONS:
                raise ValueError(f"缺少迁移路径: v{old_version} → v{old_version + 1}")
            cls._MIGRATIONS[old_version](old_data)
            old_version += 1

        # 更新版本号
        old_data["version"] = cls._VERSION

        # 验证并返回
        return cls.model_validate(old_data)

    def update_from_model(self, other: UserSetting) -> None:
        for field in self.__class__.model_fields:
            setattr(self, field, getattr(other, field))

    def update_from_dict(self, data: dict[str, Any]) -> None:
        model = UserSetting.model_validate(data)
        self.update_from_model(model)
