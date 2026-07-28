"""
宝藏基质矩阵编码工具模块

编码格式：6位混合编码
[基础属性ID][附加属性ID][技能属性ID][基础等级][附加等级][技能等级]
└─1位十六进制─┘└─1位十六进制─┘└─1位十六进制─┘└─1位十进制─┘└─1位十进制─┘└─1位十进制─┘

示例：
- 智识3 + 攻击提升3 + 夜幕1 → 40D331
- 主能力3 + 暴击3 + 切骨1 → 113331
"""

from __future__ import annotations

from dataclasses import dataclass

# ============================================================================
# 编码映射表
# ============================================================================

# 基础属性（ATTRIBUTE）- 第1位
ATTRIBUTE_CODE_MAP: dict[str, str] = {
    "gat_passive_attr_agi": "0",   # 敏捷提升
    "gat_passive_attr_main": "1",  # 主能力提升
    "gat_passive_attr_str": "2",   # 力量提升
    "gat_passive_attr_will": "3",  # 意志提升
    "gat_passive_attr_wisd": "4",  # 智识提升
}

# 附加属性（SECONDARY）- 第2位
SECONDARY_CODE_MAP: dict[str, str] = {
    "gat_passive_attr_atk": "0",       # 攻击提升
    "gat_passive_attr_crirate": "1",   # 暴击率提升
    "gat_passive_attr_firedam": "2",   # 灼热伤害提升
    "gat_passive_attr_heal": "3",      # 治疗效率提升
    "gat_passive_attr_hp": "4",        # 生命提升
    "gat_passive_attr_icedam": "5",    # 寒冷伤害提升
    "gat_passive_attr_magicdam": "6",  # 法术伤害提升
    "gat_passive_attr_naturaldam": "7", # 自然伤害提升
    "gat_passive_attr_phydam": "8",    # 物理伤害提升
    "gat_passive_attr_physpell": "9",  # 源石技艺提升
    "gat_passive_attr_pulsedam": "A",  # 电磁伤害提升
    "gat_passive_attr_usp": "B",       # 终结技充能效率提升
}

# 技能属性（SKILL）- 第3位
SKILL_CODE_MAP: dict[str, str] = {
    "gst_passive_break": "0",      # 残暴
    "gst_passive_burst": "1",      # 迸发
    "gst_passive_combo": "2",      # 追袭
    "gst_passive_crit": "3",       # 切骨
    "gst_passive_force": "4",      # 强攻
    "gst_passive_heal": "5",       # 医疗
    "gst_passive_keyword": "6",    # 效益
    "gst_passive_magabn": "7",     # 附术
    "gst_passive_phyabn": "8",     # 巧技
    "gst_passive_smash": "9",      # 粉碎
    "gst_passive_spirit": "A",     # 昂扬
    "gst_passive_tacafter": "B",   # 流转
    "gst_passive_tactic": "C",     # 压制
    "gst_passive_ult": "D",        # 夜幕
}

# 反向映射表（编码 -> ID）
ATTRIBUTE_ID_MAP: dict[str, str] = {v: k for k, v in ATTRIBUTE_CODE_MAP.items()}
SECONDARY_ID_MAP: dict[str, str] = {v: k for k, v in SECONDARY_CODE_MAP.items()}
SKILL_ID_MAP: dict[str, str] = {v: k for k, v in SKILL_CODE_MAP.items()}

# 属性名称映射
ATTRIBUTE_NAMES: dict[str, str] = {
    "gat_passive_attr_agi": "敏捷提升",
    "gat_passive_attr_main": "主能力提升",
    "gat_passive_attr_str": "力量提升",
    "gat_passive_attr_will": "意志提升",
    "gat_passive_attr_wisd": "智识提升",
}

SECONDARY_NAMES: dict[str, str] = {
    "gat_passive_attr_atk": "攻击提升",
    "gat_passive_attr_crirate": "暴击率提升",
    "gat_passive_attr_firedam": "灼热伤害提升",
    "gat_passive_attr_heal": "治疗效率提升",
    "gat_passive_attr_hp": "生命提升",
    "gat_passive_attr_icedam": "寒冷伤害提升",
    "gat_passive_attr_magicdam": "法术伤害提升",
    "gat_passive_attr_naturaldam": "自然伤害提升",
    "gat_passive_attr_phydam": "物理伤害提升",
    "gat_passive_attr_physpell": "源石技艺提升",
    "gat_passive_attr_pulsedam": "电磁伤害提升",
    "gat_passive_attr_usp": "终结技充能效率提升",
}

SKILL_NAMES: dict[str, str] = {
    "gst_passive_break": "残暴",
    "gst_passive_burst": "迸发",
    "gst_passive_combo": "追袭",
    "gst_passive_crit": "切骨",
    "gst_passive_force": "强攻",
    "gst_passive_heal": "医疗",
    "gst_passive_keyword": "效益",
    "gst_passive_magabn": "附术",
    "gst_passive_phyabn": "巧技",
    "gst_passive_smash": "粉碎",
    "gst_passive_spirit": "昂扬",
    "gst_passive_tacafter": "流转",
    "gst_passive_tactic": "压制",
    "gst_passive_ult": "夜幕",
}

# 按类型分组的属性 ID 列表（有序）
ATTRIBUTE_IDS: list[str] = list(ATTRIBUTE_CODE_MAP.keys())
SECONDARY_IDS: list[str] = list(SECONDARY_CODE_MAP.keys())
SKILL_IDS: list[str] = list(SKILL_CODE_MAP.keys())


# ============================================================================
# 数据类
# ============================================================================

@dataclass
class MatrixCode:
    """矩阵编码结构"""
    attribute_id: str      # 基础属性 ID
    secondary_id: str      # 附加属性 ID
    skill_id: str          # 技能属性 ID
    attribute_level: int   # 基础属性等级 (1-6)
    secondary_level: int   # 附加属性等级 (1-6)
    skill_level: int       # 技能属性等级 (1-3)

    @property
    def attribute_name(self) -> str:
        return ATTRIBUTE_NAMES.get(self.attribute_id, self.attribute_id)

    @property
    def secondary_name(self) -> str:
        return SECONDARY_NAMES.get(self.secondary_id, self.secondary_id)

    @property
    def skill_name(self) -> str:
        return SKILL_NAMES.get(self.skill_id, self.skill_id)

    def encode(self) -> str:
        """编码为6位字符串"""
        return encode_matrix(
            self.attribute_id,
            self.secondary_id,
            self.skill_id,
            self.attribute_level,
            self.secondary_level,
            self.skill_level,
        )

    def to_dict(self) -> dict:
        return {
            "code": self.encode(),
            "attribute_id": self.attribute_id,
            "attribute_name": self.attribute_name,
            "attribute_level": self.attribute_level,
            "secondary_id": self.secondary_id,
            "secondary_name": self.secondary_name,
            "secondary_level": self.secondary_level,
            "skill_id": self.skill_id,
            "skill_name": self.skill_name,
            "skill_level": self.skill_level,
        }


# ============================================================================
# 编码/解码函数
# ============================================================================

def encode_matrix(
    attribute_id: str,
    secondary_id: str,
    skill_id: str,
    attribute_level: int,
    secondary_level: int,
    skill_level: int,
) -> str:
    """
    编码基质组合为6位字符串

    Args:
        attribute_id: 基础属性 ID
        secondary_id: 附加属性 ID
        skill_id: 技能属性 ID
        attribute_level: 基础属性等级 (1-6)
        secondary_level: 附加属性等级 (1-6)
        skill_level: 技能属性等级 (1-3)

    Returns:
        6位编码字符串

    Raises:
        ValueError: 如果属性 ID 无效或等级超出范围
    """
    # 验证属性 ID
    if attribute_id not in ATTRIBUTE_CODE_MAP:
        raise ValueError(f"无效的基础属性 ID: {attribute_id}")
    if secondary_id not in SECONDARY_CODE_MAP:
        raise ValueError(f"无效的附加属性 ID: {secondary_id}")
    if skill_id not in SKILL_CODE_MAP:
        raise ValueError(f"无效的技能属性 ID: {skill_id}")

    # 验证等级范围
    if not (1 <= attribute_level <= 6):
        raise ValueError(f"基础属性等级必须在 1-6 之间，当前值: {attribute_level}")
    if not (1 <= secondary_level <= 6):
        raise ValueError(f"附加属性等级必须在 1-6 之间，当前值: {secondary_level}")
    if not (1 <= skill_level <= 3):
        raise ValueError(f"技能属性等级必须在 1-3 之间，当前值: {skill_level}")

    # 编码
    code = (
        ATTRIBUTE_CODE_MAP[attribute_id]
        + SECONDARY_CODE_MAP[secondary_id]
        + SKILL_CODE_MAP[skill_id]
        + str(attribute_level)
        + str(secondary_level)
        + str(skill_level)
    )
    return code


def decode_matrix(code: str) -> MatrixCode:
    """
    解码6位编码字符串为 MatrixCode 对象

    Args:
        code: 6位编码字符串

    Returns:
        MatrixCode 对象

    Raises:
        ValueError: 如果编码格式无效
    """
    if len(code) != 6:
        raise ValueError(f"编码长度必须为6，当前长度: {len(code)}")

    # 解析各部分
    attr_code = code[0]
    sec_code = code[1]
    skill_code = code[2]
    attr_level = code[3]
    sec_level = code[4]
    skill_level = code[5]

    # 验证编码有效性
    if attr_code not in ATTRIBUTE_ID_MAP:
        raise ValueError(f"无效的基础属性编码: {attr_code}")
    if sec_code not in SECONDARY_ID_MAP:
        raise ValueError(f"无效的附加属性编码: {sec_code}")
    if skill_code not in SKILL_ID_MAP:
        raise ValueError(f"无效的技能属性编码: {skill_code}")

    # 验证等级
    try:
        attr_level_int = int(attr_level)
        sec_level_int = int(sec_level)
        skill_level_int = int(skill_level)
    except ValueError as e:
        raise ValueError(f"等级必须是数字，当前值: {attr_level}{sec_level}{skill_level}") from e

    if not (1 <= attr_level_int <= 6):
        raise ValueError(f"基础属性等级必须在 1-6 之间，当前值: {attr_level_int}")
    if not (1 <= sec_level_int <= 6):
        raise ValueError(f"附加属性等级必须在 1-6 之间，当前值: {sec_level_int}")
    if not (1 <= skill_level_int <= 3):
        raise ValueError(f"技能属性等级必须在 1-3 之间，当前值: {skill_level_int}")

    return MatrixCode(
        attribute_id=ATTRIBUTE_ID_MAP[attr_code],
        secondary_id=SECONDARY_ID_MAP[sec_code],
        skill_id=SKILL_ID_MAP[skill_code],
        attribute_level=attr_level_int,
        secondary_level=sec_level_int,
        skill_level=skill_level_int,
    )


def get_all_combinations(include_levels: bool = True) -> list[str]:
    """
    生成所有可能的基质组合编码

    Args:
        include_levels: 是否包含所有等级组合

    Returns:
        编码字符串列表
    """
    combinations = []

    if include_levels:
        # 包含所有等级组合：5 × 12 × 14 × 6 × 6 × 3 = 840 种
        for attr_id in ATTRIBUTE_IDS:
            for sec_id in SECONDARY_IDS:
                for skill_id in SKILL_IDS:
                    for attr_level in range(1, 7):
                        for sec_level in range(1, 7):
                            for skill_level in range(1, 4):
                                code = encode_matrix(
                                    attr_id, sec_id, skill_id,
                                    attr_level, sec_level, skill_level
                                )
                                combinations.append(code)
    else:
        # 仅属性组合：5 × 12 × 14 = 840 种（不含等级）
        for attr_id in ATTRIBUTE_IDS:
            for sec_id in SECONDARY_IDS:
                for skill_id in SKILL_IDS:
                    # 使用等级 1 作为占位
                    code = encode_matrix(attr_id, sec_id, skill_id, 1, 1, 1)
                    combinations.append(code)

    return combinations


def get_combinations_by_attribute(attribute_id: str) -> list[str]:
    """获取指定基础属性的所有组合"""
    if attribute_id not in ATTRIBUTE_CODE_MAP:
        raise ValueError(f"无效的基础属性 ID: {attribute_id}")

    combinations = []
    for sec_id in SECONDARY_IDS:
        for skill_id in SKILL_IDS:
            for attr_level in range(1, 7):
                for sec_level in range(1, 7):
                    for skill_level in range(1, 4):
                        code = encode_matrix(
                            attribute_id, sec_id, skill_id,
                            attr_level, sec_level, skill_level
                        )
                        combinations.append(code)
    return combinations


def get_combinations_by_secondary(secondary_id: str) -> list[str]:
    """获取指定附加属性的所有组合"""
    if secondary_id not in SECONDARY_CODE_MAP:
        raise ValueError(f"无效的附加属性 ID: {secondary_id}")

    combinations = []
    for attr_id in ATTRIBUTE_IDS:
        for skill_id in SKILL_IDS:
            for attr_level in range(1, 7):
                for sec_level in range(1, 7):
                    for skill_level in range(1, 4):
                        code = encode_matrix(
                            attr_id, secondary_id, skill_id,
                            attr_level, sec_level, skill_level
                        )
                        combinations.append(code)
    return combinations


def get_combinations_by_skill(skill_id: str) -> list[str]:
    """获取指定技能属性的所有组合"""
    if skill_id not in SKILL_CODE_MAP:
        raise ValueError(f"无效的技能属性 ID: {skill_id}")

    combinations = []
    for attr_id in ATTRIBUTE_IDS:
        for sec_id in SECONDARY_IDS:
            for attr_level in range(1, 7):
                for sec_level in range(1, 7):
                    for skill_level in range(1, 4):
                        code = encode_matrix(
                            attr_id, sec_id, skill_id,
                            attr_level, sec_level, skill_level
                        )
                        combinations.append(code)
    return combinations


# ============================================================================
# 辅助函数
# ============================================================================

def get_attribute_code(attribute_id: str) -> str:
    """获取基础属性的编码"""
    if attribute_id not in ATTRIBUTE_CODE_MAP:
        raise ValueError(f"无效的基础属性 ID: {attribute_id}")
    return ATTRIBUTE_CODE_MAP[attribute_id]


def get_secondary_code(secondary_id: str) -> str:
    """获取附加属性的编码"""
    if secondary_id not in SECONDARY_CODE_MAP:
        raise ValueError(f"无效的附加属性 ID: {secondary_id}")
    return SECONDARY_CODE_MAP[secondary_id]


def get_skill_code(skill_id: str) -> str:
    """获取技能属性的编码"""
    if skill_id not in SKILL_CODE_MAP:
        raise ValueError(f"无效的技能属性 ID: {skill_id}")
    return SKILL_CODE_MAP[skill_id]


def get_attribute_id(code: str) -> str:
    """根据编码获取基础属性 ID"""
    if code not in ATTRIBUTE_ID_MAP:
        raise ValueError(f"无效的基础属性编码: {code}")
    return ATTRIBUTE_ID_MAP[code]


def get_secondary_id(code: str) -> str:
    """根据编码获取附加属性 ID"""
    if code not in SECONDARY_ID_MAP:
        raise ValueError(f"无效的附加属性编码: {code}")
    return SECONDARY_ID_MAP[code]


def get_skill_id(code: str) -> str:
    """根据编码获取技能属性 ID"""
    if code not in SKILL_ID_MAP:
        raise ValueError(f"无效的技能属性编码: {code}")
    return SKILL_ID_MAP[code]


def get_code_description(code: str) -> str:
    """获取编码的可读描述"""
    matrix = decode_matrix(code)
    return (
        f"{matrix.attribute_name}{matrix.attribute_level} + "
        f"{matrix.secondary_name}{matrix.secondary_level} + "
        f"{matrix.skill_name}{matrix.skill_level}"
    )


# ============================================================================
# 统计函数
# ============================================================================

def count_combinations() -> dict:
    """统计各类型的组合数量"""
    return {
        "total": 5 * 12 * 14 * 6 * 6 * 3,  # 90720（包含所有等级组合）
        "attribute_types": len(ATTRIBUTE_IDS),
        "secondary_types": len(SECONDARY_IDS),
        "skill_types": len(SKILL_IDS),
        "attribute_levels": 6,
        "secondary_levels": 6,
        "skill_levels": 3,
        "unique_combinations": 5 * 12 * 14,  # 840（不含等级）
    }
