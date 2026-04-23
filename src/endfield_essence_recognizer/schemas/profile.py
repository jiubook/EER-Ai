"""
Multi-account profile system.

Each profile represents a separate game account with its own settings
and treasure matrix configurations.
"""

from __future__ import annotations

from typing import Any, ClassVar

from pydantic import BaseModel, Field


class TreasureMatrixEntry(BaseModel):
    """A single weapon's treasure matrix configuration with affix levels."""

    weapon_id: str
    """The weapon ID (e.g. wpn_funnel_0009)."""

    weapon_name: str = ""
    """The weapon's display name (cached for convenience)."""

    affix1_level: int = Field(default=1, ge=1, le=6)
    """First affix (attribute) level: 1-6."""

    affix2_level: int = Field(default=1, ge=1, le=6)
    """Second affix (secondary) level: 1-6."""

    affix3_level: int = Field(default=1, ge=1, le=3)
    """Third affix (skill) level: 1-3."""


class ProfileData(BaseModel):
    """Data stored for a single profile."""

    _VERSION: ClassVar[int] = 1

    version: int = _VERSION

    name: str = "default"
    """Profile display name."""

    treasure_matrix: list[TreasureMatrixEntry] = []
    """Saved treasure matrix configurations for this profile."""


class ProfileCollection(BaseModel):
    """Collection of all profiles."""

    _VERSION: ClassVar[int] = 1

    version: int = _VERSION

    active_profile: str = "default"
    """Name of the currently active profile."""

    profiles: dict[str, ProfileData] = Field(default_factory=dict)
    """Map of profile name -> profile data."""

    def get_active(self) -> ProfileData:
        """Get the active profile data, creating default if needed."""
        if self.active_profile not in self.profiles:
            self.profiles[self.active_profile] = ProfileData(name=self.active_profile)
        return self.profiles[self.active_profile]

    def ensure_default(self) -> None:
        """Ensure the default profile exists."""
        if "default" not in self.profiles:
            self.profiles["default"] = ProfileData(name="default")
