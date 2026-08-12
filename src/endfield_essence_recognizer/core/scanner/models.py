from dataclasses import dataclass, field
from enum import StrEnum

from endfield_essence_recognizer.core.recognition import (
    AbandonStatusLabel,
    LockStatusLabel,
    RarityLabel,
)
from endfield_essence_recognizer.game_data.models.v2 import (
    StatId,
    StatType,
    WeaponId,
)

# 词条等级三元组（基础属性, 附加属性, 技能属性）
LevelTuple = tuple[int, int, int]


class EssenceQuality(StrEnum):
    """Enumeration of identified essence qualities."""

    TREASURE = "treasure"
    """Identified as a valuable item based on user settings."""

    TRASH = "trash"
    """Identified as junk or unwanted item."""

    SKIP = "skip"
    """Item should be ignored by automatic actions."""


@dataclass
class EssenceData:
    """Raw recognition data for a single essence."""

    stats: list[StatId | None]
    """List of identified attribute IDs on the essence (positional: index 0/1/2)."""

    stat_types: list[StatType | None]
    """Semantic type for each position: ATTRIBUTE / SECONDARY / SKILL / None (unrecognized)."""

    levels: list[int | None]
    """List of identified attribute levels/enhancement values."""

    rarity: RarityLabel
    """The identified rarity of the essence."""

    abandon_label: AbandonStatusLabel
    """The identified 'abandon' (deprecate) button state."""

    lock_label: LockStatusLabel
    """The identified 'lock' button state."""


@dataclass
class EvaluationResult:
    """The judgement result of an essence after evaluation against user settings."""

    quality: EssenceQuality
    """The overall judged quality (Treasure or Trash)."""

    log_message: str
    """The formatted log message to show to the user (contains color tags)."""

    matched_weapons: set[WeaponId] = field(default_factory=set)
    """Set of weapon IDs that this essence is suitable for."""

    matched_weapons_all_blocked: bool = False
    """True if all weapons in matched_weapons are blocked by the user (trash_weapon_ids)."""

    is_high_level: bool = False
    """Whether any attribute on the essence exceeded a high-level threshold."""

    stop_scan: bool = False
    """Whether the scanner should stop after this evaluation."""


class RejectReason(StrEnum):
    """认领被拒绝的原因。"""

    LIMIT = "limit"
    """达到数量上限。"""

    WORSE_LEVEL = "worse_level"
    """等级劣于已保存最佳。"""

    NON_DOWNGRADE = "non_downgrade"
    """非降级原则过滤：无法升级任何匹配武器已有基质。"""


@dataclass
class ClassificationResult:
    """Layer 1 输出：纯分类结果，不含认领决策。"""

    quality: EssenceQuality
    """分类结果（TREASURE / TRASH / SKIP）。"""

    matched_weapon_ids: set[WeaponId] = field(default_factory=set)
    """匹配到的武器 ID（已排除 trash_weapon_ids 中的）。"""

    all_matched_weapon_ids: set[WeaponId] = field(default_factory=set)
    """全部匹配到的武器 ID（含被用户拦截的）。"""

    all_blocked: bool = False
    """所有匹配武器均被用户手动拦截。"""

    is_high_level: bool = False
    """是否含高等级属性词条。"""

    stop_scan: bool = False
    """是否应停止扫描。"""

    high_level_info: str = ""
    """高等级属性描述文本（如"（含高等级属性词条：攻击提升+6）"）。"""

    custom_treasure_name: str | None = None
    """自定义宝藏基质的显示名称（如有匹配）。"""


@dataclass
class ClaimResult:
    """Layer 2 输出：单枚基质的认领结果，纯数据无副作用。"""

    accepted_weapon_id: str | None = None
    """被认领的武器 ID（None = 未认领）。"""

    updated_levels: dict[str, LevelTuple] = field(default_factory=dict)
    """本次直接认领更新的武器等级映射。"""

    cascade_updated: dict[str, LevelTuple] = field(default_factory=dict)
    """级联更新的武器等级映射（升级释放旧等级给其他武器）。"""

    reject_reason: RejectReason | None = None
    """拒绝原因（None = 认领成功或未被拒绝）。"""

    current_count: int = 0
    """拒绝时的当前保有量（LIMIT 拒绝日志用）。"""

    group_stat_key: tuple | None = None
    """属性组合 key（展示计数用）。"""
