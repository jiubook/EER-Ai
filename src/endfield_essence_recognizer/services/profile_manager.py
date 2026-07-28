"""
账号管理服务。

管理多账号及其宝藏基质配置。
账号存储在主配置文件旁的 JSON 文件中。
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
from dataclasses import dataclass
from json import JSONDecodeError
from typing import TYPE_CHECKING

from pydantic import ValidationError

from endfield_essence_recognizer.schemas.profile import (
    ProfileCollection,
    ProfileData,
    TreasureMatrixEntry,
)
from endfield_essence_recognizer.utils.log import logger

if TYPE_CHECKING:
    from pathlib import Path

__all__ = [
    "ProfileLoadError",
    "ProfileManager",
    "ProfileSaveError",
    "TreasureMatrixSyncResult",
]


class ProfileLoadError(RuntimeError):
    """账号配置文件存在但无法安全加载。"""


class ProfileSaveError(RuntimeError):
    """账号配置文件无法安全保存。"""


@dataclass(frozen=True)
class TreasureMatrixSyncResult:
    """扫描数据同步到宝藏基质后的变更摘要。"""

    profile: ProfileData
    added: list[TreasureMatrixEntry]
    updated: list[TreasureMatrixEntry]


def _load_profiles_from_file(path: Path) -> ProfileCollection | None:
    """从 JSON 文件加载账号配置。"""
    if not path.exists():
        return None
    if not path.is_file():
        raise ProfileLoadError(f"账号配置路径不是文件: {path}")

    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
        return ProfileCollection.model_validate(obj)
    except (OSError, JSONDecodeError, ValidationError) as exc:
        broken_path = path.with_suffix(f"{path.suffix}.broken")
        try:
            if broken_path.exists():
                broken_path = path.with_suffix(f"{path.suffix}.broken.{os.getpid()}")
            path.replace(broken_path)
            logger.error("账号配置文件无效，已备份到: {}", broken_path)
        except OSError:
            logger.exception("账号配置文件无效，且备份失败: {}", path)
        raise ProfileLoadError(f"账号配置文件无法加载: {path}") from exc


def _save_profiles_to_file(collection: ProfileCollection, path: Path) -> None:
    """原子性地保存账号配置到 JSON 文件。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    data = collection.model_dump_json(indent=4, ensure_ascii=False)

    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
        text=True,
    )
    tmp_path = type(path)(tmp_name)

    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as file:
            file.write(data)
            file.flush()
            os.fsync(file.fileno())

        os.replace(tmp_path, path)
    except Exception as exc:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            logger.exception("清理账号配置临时文件失败: {}", tmp_path)
        logger.exception("保存账号配置失败: {}", path)
        raise ProfileSaveError(f"账号配置文件无法保存: {path}") from exc


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
        self._lock = threading.RLock()

    def load(self) -> None:
        """从磁盘加载账号配置。"""
        with self._lock:
            result = _load_profiles_from_file(self._profiles_file)
            if result is not None:
                self._collection = result
                self._collection.ensure_default()
                logger.info(
                    "加载账号配置成功，当前账号: {}", self._collection.active_profile
                )
            else:
                logger.info("未找到账号配置文件，使用默认配置。")
                collection = ProfileCollection()
                collection.ensure_default()
                _save_profiles_to_file(collection, self._profiles_file)
                self._collection = collection

    def save(self) -> None:
        """保存账号配置到磁盘。"""
        with self._lock:
            self._save_unlocked()

    def _save_unlocked(self) -> None:
        """保存账号配置；调用方必须已经持有 `_lock`。"""
        _save_profiles_to_file(self._collection, self._profiles_file)

    def _commit_collection_unlocked(self, collection: ProfileCollection) -> None:
        """保存新集合并在成功后替换内存状态；调用方必须已经持有 `_lock`。"""
        _save_profiles_to_file(collection, self._profiles_file)
        self._collection = collection

    def _get_active_unlocked(self) -> ProfileData:
        """获取激活账号；调用方必须已经持有 `_lock`。"""
        return self._collection.get_active()

    def get_collection(self) -> ProfileCollection:
        """获取当前账号集合。"""
        with self._lock:
            return self._collection.model_copy(deep=True)

    def get_active_profile(self) -> ProfileData:
        """获取激活的账号数据。"""
        with self._lock:
            return self._get_active_unlocked().model_copy(deep=True)

    def get_active_profile_name(self) -> str:
        """获取激活的账号名称。"""
        with self._lock:
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
        with self._lock:
            collection = self._collection.model_copy(deep=True)
            name = self._validate_profile_name(name)
            if name not in collection.profiles:
                collection.profiles[name] = ProfileData(name=name)
            collection.active_profile = name
            self._commit_collection_unlocked(collection)
            logger.info("切换到账号: {}", name)
            return collection.profiles[name].model_copy(deep=True)

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
        forbidden = {
            "/": "正斜杠(/)",
            "\\": "反斜杠(\\)",
            "\x00": "空字节",
            "\n": "换行符",
            "\r": "回车符",
            "\t": "制表符",
        }
        bad_chars = [forbidden[c] for c in stripped if c in forbidden]
        if bad_chars:
            raise ValueError(f"账号名称包含非法字符: {', '.join(sorted(bad_chars))}")
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
        with self._lock:
            if old_name == "default":
                raise ValueError("不能重命名默认账号")
            collection = self._collection.model_copy(deep=True)
            if old_name not in collection.profiles:
                raise ValueError(f"账号 '{old_name}' 不存在")
            new_name = self._validate_profile_name(new_name)
            if new_name in collection.profiles:
                raise ValueError(f"账号 '{new_name}' 已存在")

            profile = collection.profiles.pop(old_name)
            profile.name = new_name
            collection.profiles[new_name] = profile

            if collection.active_profile == old_name:
                collection.active_profile = new_name

            self._commit_collection_unlocked(collection)
            logger.info("重命名账号: {} -> {}", old_name, new_name)
            return profile.model_copy(deep=True)

    def delete_profile(self, name: str) -> None:
        """删除账号。

        不能删除 'default' 账号和当前激活的账号。

        Args:
            name: 要删除的账号名称。

        Raises:
            ValueError: 如果账号是 'default'、是激活账号或不存在。
        """
        with self._lock:
            collection = self._collection.model_copy(deep=True)
            if name == "default":
                raise ValueError("不能删除默认账号")
            if name not in collection.profiles:
                raise ValueError(f"账号 '{name}' 不存在")
            if collection.active_profile == name:
                raise ValueError("不能删除当前正在使用的账号")

            del collection.profiles[name]
            self._commit_collection_unlocked(collection)
            logger.info("删除账号: {}", name)

    def update_treasure_matrix(self, entries: list[TreasureMatrixEntry]) -> ProfileData:
        """替换激活账号的完整宝藏基质配置。

        Args:
            entries: 新的宝藏基质条目列表。

        Returns:
            更新后的 ProfileData。
        """
        with self._lock:
            collection = self._collection.model_copy(deep=True)
            profile = collection.get_active()
            profile.treasure_matrix = [entry.model_copy(deep=True) for entry in entries]
            # 重建优先级映射：只保留当前矩阵中 priority > 0 的条目
            profile.weapon_priorities = {
                entry.weapon_id: entry.priority
                for entry in profile.treasure_matrix
                if entry.priority > 0
            }
            self._commit_collection_unlocked(collection)
            return profile.model_copy(deep=True)

    def add_treasure_matrix_entry(self, entry: TreasureMatrixEntry) -> ProfileData:
        """添加或更新单个宝藏基质条目。

        如果相同 weapon_id 的条目已存在，则替换它。

        Args:
            entry: 要添加或更新的宝藏基质条目。

        Returns:
            更新后的 ProfileData。
        """
        with self._lock:
            collection = self._collection.model_copy(deep=True)
            profile = collection.get_active()
            entry = entry.model_copy(deep=True)
            if entry.weapon_id in profile.weapon_priorities:
                entry.priority = profile.weapon_priorities[entry.weapon_id]
            elif entry.priority > 0:
                profile.weapon_priorities[entry.weapon_id] = entry.priority
            profile.treasure_matrix = [
                e for e in profile.treasure_matrix if e.weapon_id != entry.weapon_id
            ]
            profile.treasure_matrix.append(entry)
            self._commit_collection_unlocked(collection)
            return profile.model_copy(deep=True)

    def sync_treasure_matrix_entries(
        self, entries: list[TreasureMatrixEntry]
    ) -> TreasureMatrixSyncResult:
        """批量同步扫描得到的宝藏基质条目，并且最多只保存一次。

        扫描通常一次返回多把武器。逐个调用 `add_treasure_matrix_entry()` 会
        对同一个 JSON 文件重复序列化和写盘；这里先在内存中完成所有合并，最后
        在确实有变更时统一保存。
        """
        with self._lock:
            collection = self._collection.model_copy(deep=True)
            profile = collection.get_active()
            existing_by_weapon_id = {
                entry.weapon_id: entry for entry in profile.treasure_matrix
            }
            added: list[TreasureMatrixEntry] = []
            updated: list[TreasureMatrixEntry] = []

            for incoming in entries:
                incoming = incoming.model_copy(deep=True)
                existing = existing_by_weapon_id.get(incoming.weapon_id)
                if existing is None:
                    if incoming.weapon_id in profile.weapon_priorities:
                        incoming.priority = profile.weapon_priorities[
                            incoming.weapon_id
                        ]
                    elif incoming.priority > 0:
                        profile.weapon_priorities[incoming.weapon_id] = (
                            incoming.priority
                        )

                    profile.treasure_matrix.append(incoming)
                    existing_by_weapon_id[incoming.weapon_id] = incoming
                    added.append(incoming)
                    continue

                level_changed = False
                if existing.affix1_level < incoming.affix1_level:
                    existing.affix1_level = incoming.affix1_level
                    level_changed = True
                if existing.affix2_level < incoming.affix2_level:
                    existing.affix2_level = incoming.affix2_level
                    level_changed = True
                if existing.affix3_level < incoming.affix3_level:
                    existing.affix3_level = incoming.affix3_level
                    level_changed = True

                # 只在扫描到更高等级时自动关闭满级武器，避免无变更扫描覆盖用户选择。
                if level_changed and (
                    existing.affix1_level == 6
                    and existing.affix2_level == 6
                    and existing.affix3_level == 3
                ):
                    existing.include_in_calculation = False

                if level_changed:
                    if existing.priority > 0:
                        profile.weapon_priorities[existing.weapon_id] = (
                            existing.priority
                        )
                    updated.append(existing)

            if added or updated:
                self._commit_collection_unlocked(collection)

            return TreasureMatrixSyncResult(
                profile=profile.model_copy(deep=True),
                added=[entry.model_copy(deep=True) for entry in added],
                updated=[entry.model_copy(deep=True) for entry in updated],
            )

    def remove_treasure_matrix_entry(self, weapon_id: str) -> ProfileData:
        """根据武器 ID 移除宝藏基质条目。

        Args:
            weapon_id: 要移除的条目的武器 ID。

        Returns:
            更新后的 ProfileData。
        """
        with self._lock:
            collection = self._collection.model_copy(deep=True)
            profile = collection.get_active()
            profile.treasure_matrix = [
                e for e in profile.treasure_matrix if e.weapon_id != weapon_id
            ]
            self._commit_collection_unlocked(collection)
            return profile.model_copy(deep=True)

    def clear_profile_data(self, name: str | None = None) -> ProfileData:
        """清空指定账号的宝藏基质数据（保留账号本身、名称、版本与总览过滤器）。

        清空内容为 treasure_matrix 与 weapon_priorities，用于「数据有误、
        全量重新扫描」的场景；不删除账号，也不重置武器总览过滤器等展示偏好。

        Args:
            name: 要清空的账号名称；None 表示清空当前激活账号。

        Returns:
            清空后的 ProfileData。

        Raises:
            ValueError: 如果指定的账号不存在。
        """
        with self._lock:
            collection = self._collection.model_copy(deep=True)
            if name is None:
                profile = collection.get_active()
            elif name in collection.profiles:
                profile = collection.profiles[name]
            else:
                raise ValueError(f"账号 '{name}' 不存在")
            profile.treasure_matrix = []
            profile.weapon_priorities = {}
            self._commit_collection_unlocked(collection)
            logger.info("清空账号数据: {}", profile.name)
            return profile.model_copy(deep=True)

    def fix_weapon_id(self, old_weapon_id: str, new_weapon_id: str) -> None:
        """修正 profile 中错误的武器 ID（如名称 → 正确 ID）。

        同时迁移 weapon_priorities 中的对应条目。
        """
        with self._lock:
            collection = self._collection.model_copy(deep=True)
            profile = collection.get_active()
            changed = False
            for entry in profile.treasure_matrix:
                if entry.weapon_id == old_weapon_id:
                    entry.weapon_id = new_weapon_id
                    changed = True
            if old_weapon_id in profile.weapon_priorities:
                profile.weapon_priorities[new_weapon_id] = (
                    profile.weapon_priorities.pop(old_weapon_id)
                )
                changed = True
            if changed:
                self._commit_collection_unlocked(collection)

    def update_weapon_overview_filters(self, filters: dict[str, bool]) -> ProfileData:
        """更新激活账号的武器总览过滤器配置。

        Args:
            filters: 星级过滤器配置字典。

        Returns:
            更新后的 ProfileData。
        """
        with self._lock:
            collection = self._collection.model_copy(deep=True)
            profile = collection.get_active()
            profile.weapon_overview_filters = filters
            self._commit_collection_unlocked(collection)
            return profile.model_copy(deep=True)

    def update_switch_display_mode(self, mode: str) -> ProfileData:
        """更新激活账号的"可切换"提示显示模式。

        Args:
            mode: 显示模式，'chip' | 'dot' | 'off'。

        Returns:
            更新后的 ProfileData。
        """
        with self._lock:
            collection = self._collection.model_copy(deep=True)
            profile = collection.get_active()
            profile.switch_display_mode = mode
            self._commit_collection_unlocked(collection)
            return profile.model_copy(deep=True)

    def update_matrix_badge_display_mode(self, mode: str) -> ProfileData:
        """更新激活账号的基质图标显示模式。

        Args:
            mode: 显示模式，'small' | 'medium' | 'off'。

        Returns:
            更新后的 ProfileData。
        """
        with self._lock:
            collection = self._collection.model_copy(deep=True)
            profile = collection.get_active()
            profile.matrix_badge_display_mode = mode
            self._commit_collection_unlocked(collection)
            return profile.model_copy(deep=True)

    def update_weapon_priority(self, weapon_id: str, priority: int) -> ProfileData:
        """更新单个武器优先级，未拥有宝藏基质的武器也会保存。

        Args:
            weapon_id: 武器 ID。
            priority: 优先级。0 表示清除手动设置并回到稀有度默认值。

        Returns:
            更新后的 ProfileData。
        """
        with self._lock:
            collection = self._collection.model_copy(deep=True)
            profile = collection.get_active()
            if priority > 0:
                profile.weapon_priorities[weapon_id] = priority
            else:
                profile.weapon_priorities.pop(weapon_id, None)

            for entry in profile.treasure_matrix:
                if entry.weapon_id == weapon_id:
                    entry.priority = priority
                    break

            self._commit_collection_unlocked(collection)
            return profile.model_copy(deep=True)

    def update_matrix_view_config(self, config_updates: dict) -> ProfileData:
        """更新激活账号的矩阵视图配置。

        Args:
            config_updates: 配置更新字典，只包含需要更新的字段。

        Returns:
            更新后的 ProfileData。
        """
        with self._lock:
            collection = self._collection.model_copy(deep=True)
            profile = collection.get_active()

            # 更新配置
            for key, value in config_updates.items():
                if hasattr(profile.matrix_view_config, key):
                    setattr(profile.matrix_view_config, key, value)

            self._commit_collection_unlocked(collection)
            return profile.model_copy(deep=True)

    def get_profile(self, name: str) -> ProfileData:
        """获取指定账号的数据。

        Args:
            name: 账号名称。

        Returns:
            账号的 ProfileData。

        Raises:
            ValueError: 如果账号不存在。
        """
        with self._lock:
            if name not in self._collection.profiles:
                raise ValueError(f"账号 '{name}' 不存在")
            return self._collection.profiles[name].model_copy(deep=True)
