"""
账号管理服务。

管理多账号及其宝藏基质配置。
账号存储在主配置文件旁的 JSON 文件中。
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from endfield_essence_recognizer.schemas.profile import (
    ProfileCollection,
    ProfileData,
    TreasureMatrixEntry,
)
from endfield_essence_recognizer.utils.log import logger

if TYPE_CHECKING:
    from pathlib import Path

__all__ = ["ProfileManager"]


def _load_profiles_from_file(path: Path) -> ProfileCollection | None:
    """从 JSON 文件加载账号配置。"""
    if not path.is_file():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
        return ProfileCollection.model_validate(obj)
    except Exception as e:
        logger.error("Failed to load profiles from {}: {}", path, e)
        return None


def _save_profiles_to_file(collection: ProfileCollection, path: Path) -> bool:
    """原子性地保存账号配置到 JSON 文件。"""
    try:
        # 先写入临时文件
        temp_path = path.with_suffix(".tmp")
        temp_path.write_text(
            collection.model_dump_json(indent=4, ensure_ascii=False),
            encoding="utf-8",
        )
        # 原子替换
        temp_path.replace(path)
        return True
    except Exception as e:
        logger.error("Failed to save profiles to {}: {}", path, e)
        return False


class ProfileManager:
    """
    管理多账号。

    - 在内存中保存 ProfileCollection。
    - 提供账号的 CRUD 操作。
    - 在更改时持久化到磁盘。
    """

    def __init__(self, profiles_file: Path) -> None:
        """初始化账号管理器。

        Args:
            profiles_file: 账号持久化的 JSON 文件路径。
        """
        self._profiles_file = profiles_file
        self._collection = ProfileCollection()

    def load(self) -> None:
        """从磁盘加载账号配置。"""
        result = _load_profiles_from_file(self._profiles_file)
        if result is not None:
            self._collection = result
            self._collection.ensure_default()
            logger.info(
                "加载账号配置成功，当前账号: {}", self._collection.active_profile
            )
        else:
            logger.info("未找到账号配置文件，使用默认配置。")
            self._collection.ensure_default()
            self.save()

    def save(self) -> None:
        """保存账号配置到磁盘。"""
        _save_profiles_to_file(self._collection, self._profiles_file)

    def get_collection(self) -> ProfileCollection:
        """获取当前账号集合。"""
        return self._collection

    def get_active_profile(self) -> ProfileData:
        """获取激活的账号数据。"""
        return self._collection.get_active()

    def get_active_profile_name(self) -> str:
        """获取激活的账号名称。"""
        return self._collection.active_profile

    def switch_profile(self, name: str) -> ProfileData:
        """切换到指定账号，如果不存在则创建。

        Args:
            name: 要切换到的账号名称。必须在去除空白后非空，
                最多 32 个字符，且不能包含路径分隔符或换行符。

        Returns:
            切换到的账号的 ProfileData。

        Raises:
            ValueError: 如果名称无效。
        """
        name = self._validate_profile_name(name)
        if name not in self._collection.profiles:
            self._collection.profiles[name] = ProfileData(name=name)
        self._collection.active_profile = name
        self.save()
        logger.info("切换到账号: {}", name)
        return self._collection.profiles[name]

    @staticmethod
    def _validate_profile_name(name: str) -> str:
        """验证并规范化账号名称。

        规则：
        - 去除空白后非空
        - 最多 32 个字符
        - 不能包含路径分隔符、换行符或空字节

        Args:
            name: 原始账号名称。

        Returns:
            去除空白后的账号名称。

        Raises:
            ValueError: 如果名称违反任何规则。
        """
        stripped = name.strip()
        if not stripped:
            raise ValueError("账号名称不能为空")
        if len(stripped) > 32:
            raise ValueError("账号名称不能超过 32 个字符")
        forbidden = set("/\\\x00\n\r\t")
        bad_chars = forbidden & set(stripped)
        if bad_chars:
            raise ValueError(
                f"账号名称包含非法字符: {''.join(sorted(repr(c) for c in bad_chars))}"
            )
        return stripped

    def rename_profile(self, old_name: str, new_name: str) -> ProfileData:
        """重命名账号。

        Args:
            old_name: 当前账号名称。必须存在。
            new_name: 新账号名称。必须有效且未被使用。

        Returns:
            重命名后的 ProfileData。

        Raises:
            ValueError: 如果 old_name 不存在、new_name 已被占用或 new_name 无效。
        """
        if old_name not in self._collection.profiles:
            raise ValueError(f"账号 '{old_name}' 不存在")
        new_name = self._validate_profile_name(new_name)
        if new_name in self._collection.profiles:
            raise ValueError(f"账号 '{new_name}' 已存在")

        profile = self._collection.profiles.pop(old_name)
        profile.name = new_name
        self._collection.profiles[new_name] = profile

        if self._collection.active_profile == old_name:
            self._collection.active_profile = new_name

        self.save()
        logger.info("重命名账号: {} -> {}", old_name, new_name)
        return profile

    def delete_profile(self, name: str) -> None:
        """删除账号。

        不能删除 'default' 账号和当前激活的账号。

        Args:
            name: 要删除的账号名称。

        Raises:
            ValueError: 如果账号是 'default'、是激活账号或不存在。
        """
        if name == "default":
            raise ValueError("不能删除默认账号")
        if name not in self._collection.profiles:
            raise ValueError(f"账号 '{name}' 不存在")
        if self._collection.active_profile == name:
            raise ValueError("不能删除当前正在使用的账号")

        del self._collection.profiles[name]
        self.save()
        logger.info("删除账号: {}", name)

    def update_treasure_matrix(self, entries: list[TreasureMatrixEntry]) -> ProfileData:
        """替换激活账号的完整宝藏基质配置。

        Args:
            entries: 新的宝藏基质条目列表。

        Returns:
            更新后的 ProfileData。
        """
        profile = self.get_active_profile()
        profile.treasure_matrix = entries
        self.save()
        return profile

    def add_treasure_matrix_entry(self, entry: TreasureMatrixEntry) -> ProfileData:
        """添加或更新单个宝藏基质条目。

        如果相同 weapon_id 的条目已存在，则替换它。

        Args:
            entry: 要添加或更新的宝藏基质条目。

        Returns:
            更新后的 ProfileData。
        """
        profile = self.get_active_profile()
        profile.treasure_matrix = [
            e for e in profile.treasure_matrix if e.weapon_id != entry.weapon_id
        ]
        profile.treasure_matrix.append(entry)
        self.save()
        return profile

    def remove_treasure_matrix_entry(self, weapon_id: str) -> ProfileData:
        """根据武器 ID 移除宝藏基质条目。

        Args:
            weapon_id: 要移除的条目的武器 ID。

        Returns:
            更新后的 ProfileData。
        """
        profile = self.get_active_profile()
        profile.treasure_matrix = [
            e for e in profile.treasure_matrix if e.weapon_id != weapon_id
        ]
        self.save()
        return profile

    def update_weapon_overview_filters(self, filters: dict[str, bool]) -> ProfileData:
        """更新激活账号的武器总览过滤器配置。

        Args:
            filters: 星级过滤器配置字典。

        Returns:
            更新后的 ProfileData。
        """
        profile = self.get_active_profile()
        profile.weapon_overview_filters = filters
        self.save()
        return profile
