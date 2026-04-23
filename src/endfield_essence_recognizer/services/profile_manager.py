"""
Profile manager service.

Manages multi-account profiles with their treasure matrix configurations.
Profiles are stored in a JSON file alongside the main config.
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
    """Load profiles from a JSON file."""
    if not path.is_file():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
        return ProfileCollection.model_validate(obj)
    except Exception as e:
        logger.error("Failed to load profiles from {}: {}", path, e)
        return None


def _save_profiles_to_file(collection: ProfileCollection, path: Path) -> bool:
    """Save profiles to a JSON file."""
    try:
        path.write_text(
            collection.model_dump_json(indent=4, ensure_ascii=False),
            encoding="utf-8",
        )
        return True
    except Exception as e:
        logger.error("Failed to save profiles to {}: {}", path, e)
        return False


class ProfileManager:
    """
    Manages multi-account profiles.

    - Holds a ProfileCollection in memory.
    - Provides CRUD operations for profiles.
    - Persists to disk on changes.
    """

    def __init__(self, profiles_file: Path) -> None:
        """Initialize the profile manager.

        Args:
            profiles_file: Path to the JSON file where profiles are persisted.
        """
        self._profiles_file = profiles_file
        self._collection = ProfileCollection()

    def load(self) -> None:
        """Load profiles from disk."""
        result = _load_profiles_from_file(self._profiles_file)
        if result is not None:
            self._collection = result
            self._collection.ensure_default()
            logger.info("加载账号配置成功，当前账号: {}", self._collection.active_profile)
        else:
            logger.info("未找到账号配置文件，使用默认配置。")
            self._collection.ensure_default()
            self.save()

    def save(self) -> None:
        """Save profiles to disk."""
        _save_profiles_to_file(self._collection, self._profiles_file)

    def get_collection(self) -> ProfileCollection:
        """Get the current profile collection."""
        return self._collection

    def get_active_profile(self) -> ProfileData:
        """Get the active profile data."""
        return self._collection.get_active()

    def get_active_profile_name(self) -> str:
        """Get the name of the active profile."""
        return self._collection.active_profile

    def switch_profile(self, name: str) -> ProfileData:
        """Switch to a profile, creating it if it doesn't exist.

        Args:
            name: The profile name to switch to. Must be non-empty after
                stripping whitespace, at most 32 characters, and must not
                contain path separators or newlines.

        Returns:
            The ProfileData of the switched-to profile.

        Raises:
            ValueError: If the name is invalid.
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
        """Validate and normalize a profile name.

        Rules:
        - Non-empty after stripping whitespace
        - At most 32 characters
        - Must not contain path separators, newlines, or null bytes

        Args:
            name: The raw profile name.

        Returns:
            The stripped profile name.

        Raises:
            ValueError: If the name violates any rule.
        """
        stripped = name.strip()
        if not stripped:
            raise ValueError("账号名称不能为空")
        if len(stripped) > 32:
            raise ValueError("账号名称不能超过 32 个字符")
        forbidden = set('/\\\x00\n\r\t')
        bad_chars = forbidden & set(stripped)
        if bad_chars:
            raise ValueError(
                f"账号名称包含非法字符: {''.join(sorted(repr(c) for c in bad_chars))}"
            )
        return stripped

    def rename_profile(self, old_name: str, new_name: str) -> ProfileData:
        """Rename a profile.

        Args:
            old_name: The current profile name. Must exist.
            new_name: The new profile name. Must be valid and not already in use.

        Returns:
            The renamed ProfileData.

        Raises:
            ValueError: If old_name does not exist, new_name is already taken,
                or new_name is invalid.
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
        """Delete a profile.

        The 'default' profile and the currently active profile cannot be deleted.

        Args:
            name: The profile name to delete.

        Raises:
            ValueError: If the profile is 'default', is the active profile,
                or does not exist.
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

    def update_treasure_matrix(
        self, entries: list[TreasureMatrixEntry]
    ) -> ProfileData:
        """Replace the entire treasure matrix for the active profile.

        Args:
            entries: The new list of treasure matrix entries.

        Returns:
            The updated ProfileData.
        """
        profile = self.get_active_profile()
        profile.treasure_matrix = entries
        self.save()
        return profile

    def add_treasure_matrix_entry(self, entry: TreasureMatrixEntry) -> ProfileData:
        """Add or update a single treasure matrix entry.

        If an entry for the same weapon_id already exists, it is replaced.

        Args:
            entry: The treasure matrix entry to add or update.

        Returns:
            The updated ProfileData.
        """
        profile = self.get_active_profile()
        profile.treasure_matrix = [
            e for e in profile.treasure_matrix if e.weapon_id != entry.weapon_id
        ]
        profile.treasure_matrix.append(entry)
        self.save()
        return profile

    def remove_treasure_matrix_entry(self, weapon_id: str) -> ProfileData:
        """Remove a treasure matrix entry by weapon ID.

        Args:
            weapon_id: The weapon ID of the entry to remove.

        Returns:
            The updated ProfileData.
        """
        profile = self.get_active_profile()
        profile.treasure_matrix = [
            e for e in profile.treasure_matrix if e.weapon_id != weapon_id
        ]
        self.save()
        return profile
