#!/usr/bin/env python3
"""
宝藏基质矩阵编码工具演示脚本

演示如何使用矩阵编码工具进行编码、解码和组合生成。
"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from endfield_essence_recognizer.utils.matrix_codec import (
    encode_matrix,
    decode_matrix,
    get_all_combinations,
    get_code_description,
    count_combinations,
    MatrixCode,
    ATTRIBUTE_IDS,
    SECONDARY_IDS,
    SKILL_IDS,
    ATTRIBUTE_NAMES,
    SECONDARY_NAMES,
    SKILL_NAMES,
)


def demo_basic_encoding():
    """演示基本编码功能"""
    print("=" * 60)
    print("1. 基本编码演示")
    print("=" * 60)

    # 示例1：智识3 + 攻击提升3 + 夜幕1
    code1 = encode_matrix(
        attribute_id="gat_passive_attr_wisd",
        secondary_id="gat_passive_attr_atk",
        skill_id="gst_passive_ult",
        attribute_level=3,
        secondary_level=3,
        skill_level=1,
    )
    print(f"智识3 + 攻击提升3 + 夜幕1 = {code1}")

    # 示例2：主能力3 + 暴击3 + 切骨1
    code2 = encode_matrix(
        attribute_id="gat_passive_attr_main",
        secondary_id="gat_passive_attr_crirate",
        skill_id="gst_passive_crit",
        attribute_level=3,
        secondary_level=3,
        skill_level=1,
    )
    print(f"主能力3 + 暴击3 + 切骨1 = {code2}")

    # 示例3：力量5 + 生命提升6 + 粉碎2
    code3 = encode_matrix(
        attribute_id="gat_passive_attr_str",
        secondary_id="gat_passive_attr_hp",
        skill_id="gst_passive_smash",
        attribute_level=5,
        secondary_level=6,
        skill_level=2,
    )
    print(f"力量5 + 生命提升6 + 粉碎2 = {code3}")

    # 示例4：满级组合
    code4 = encode_matrix(
        attribute_id="gat_passive_attr_will",
        secondary_id="gat_passive_attr_firedam",
        skill_id="gst_passive_force",
        attribute_level=6,
        secondary_level=6,
        skill_level=3,
    )
    print(f"意志6 + 灼热伤害6 + 强攻3 = {code4} (满级)")

    print()


def demo_basic_decoding():
    """演示基本解码功能"""
    print("=" * 60)
    print("2. 基本解码演示")
    print("=" * 60)

    codes = ["40D331", "113331", "249562", "324663"]

    for code in codes:
        matrix = decode_matrix(code)
        print(f"\n编码: {code}")
        print(f"  基础属性: {matrix.attribute_name} (Lv.{matrix.attribute_level})")
        print(f"  附加属性: {matrix.secondary_name} (Lv.{matrix.secondary_level})")
        print(f"  技能属性: {matrix.skill_name} (Lv.{matrix.skill_level})")

    print()


def demo_encode_decode_roundtrip():
    """演示编码-解码往返"""
    print("=" * 60)
    print("3. 编码-解码往返演示")
    print("=" * 60)

    test_cases = [
        ("gat_passive_attr_agi", "gat_passive_attr_atk", "gst_passive_break", 1, 1, 1),
        ("gat_passive_attr_main", "gat_passive_attr_crirate", "gst_passive_crit", 6, 6, 3),
        ("gat_passive_attr_str", "gat_passive_attr_hp", "gst_passive_heal", 4, 5, 2),
        ("gat_passive_attr_will", "gat_passive_attr_firedam", "gst_passive_force", 2, 3, 1),
        ("gat_passive_attr_wisd", "gat_passive_attr_magicdam", "gst_passive_keyword", 5, 4, 3),
    ]

    for attr_id, sec_id, skill_id, attr_level, sec_level, skill_level in test_cases:
        # 编码
        code = encode_matrix(attr_id, sec_id, skill_id, attr_level, sec_level, skill_level)

        # 解码
        matrix = decode_matrix(code)

        # 验证
        assert matrix.attribute_id == attr_id
        assert matrix.secondary_id == sec_id
        assert matrix.skill_id == skill_id
        assert matrix.attribute_level == attr_level
        assert matrix.secondary_level == sec_level
        assert matrix.skill_level == skill_level

        print(f"✓ {code} - {matrix.attribute_name}{matrix.attribute_level} + {matrix.secondary_name}{matrix.secondary_level} + {matrix.skill_name}{matrix.skill_level}")

    print()


def demo_code_description():
    """演示获取编码描述"""
    print("=" * 60)
    print("4. 编码描述演示")
    print("=" * 60)

    codes = ["40D331", "113331", "249562", "324663"]

    for code in codes:
        description = get_code_description(code)
        print(f"{code}: {description}")

    print()


def demo_combinations():
    """演示组合生成"""
    print("=" * 60)
    print("5. 组合生成演示")
    print("=" * 60)

    # 不包含等级的组合
    combinations_no_levels = get_all_combinations(include_levels=False)
    print(f"不含等级的组合数: {len(combinations_no_levels)}")
    print(f"前5个组合: {combinations_no_levels[:5]}")

    # 包含等级的组合
    combinations_with_levels = get_all_combinations(include_levels=True)
    print(f"\n包含等级的组合数: {len(combinations_with_levels)}")
    print(f"前5个组合: {combinations_with_levels[:5]}")

    # 统计信息
    stats = count_combinations()
    print(f"\n统计信息:")
    print(f"  总组合数: {stats['total']}")
    print(f"  基础属性类型: {stats['attribute_types']}")
    print(f"  附加属性类型: {stats['secondary_types']}")
    print(f"  技能属性类型: {stats['skill_types']}")
    print(f"  基础属性等级: {stats['attribute_levels']}")
    print(f"  附加属性等级: {stats['secondary_levels']}")
    print(f"  技能属性等级: {stats['skill_levels']}")
    print(f"  唯一组合数: {stats['unique_combinations']}")

    print()


def demo_matrix_code_class():
    """演示MatrixCode数据类"""
    print("=" * 60)
    print("6. MatrixCode数据类演示")
    print("=" * 60)

    # 创建MatrixCode对象
    matrix = MatrixCode(
        attribute_id="gat_passive_attr_wisd",
        secondary_id="gat_passive_attr_atk",
        skill_id="gst_passive_ult",
        attribute_level=3,
        secondary_level=3,
        skill_level=1,
    )

    print(f"编码: {matrix.encode()}")
    print(f"基础属性: {matrix.attribute_name} (Lv.{matrix.attribute_level})")
    print(f"附加属性: {matrix.secondary_name} (Lv.{matrix.secondary_level})")
    print(f"技能属性: {matrix.skill_name} (Lv.{matrix.skill_level})")

    # 转换为字典
    data = matrix.to_dict()
    print(f"\n转换为字典:")
    for key, value in data.items():
        print(f"  {key}: {value}")

    print()


def demo_attribute_mapping():
    """演示属性映射"""
    print("=" * 60)
    print("7. 属性映射演示")
    print("=" * 60)

    print("基础属性映射:")
    for attr_id in ATTRIBUTE_IDS:
        name = ATTRIBUTE_NAMES[attr_id]
        print(f"  {attr_id}: {name}")

    print("\n附加属性映射:")
    for sec_id in SECONDARY_IDS:
        name = SECONDARY_NAMES[sec_id]
        print(f"  {sec_id}: {name}")

    print("\n技能属性映射:")
    for skill_id in SKILL_IDS:
        name = SKILL_NAMES[skill_id]
        print(f"  {skill_id}: {name}")

    print()


def demo_error_handling():
    """演示错误处理"""
    print("=" * 60)
    print("8. 错误处理演示")
    print("=" * 60)

    # 测试无效的基础属性ID
    try:
        encode_matrix(
            attribute_id="invalid_id",
            secondary_id="gat_passive_attr_atk",
            skill_id="gst_passive_break",
            attribute_level=1,
            secondary_level=1,
            skill_level=1,
        )
    except ValueError as e:
        print(f"✓ 捕获无效基础属性错误: {e}")

    # 测试无效的等级
    try:
        encode_matrix(
            attribute_id="gat_passive_attr_agi",
            secondary_id="gat_passive_attr_atk",
            skill_id="gst_passive_break",
            attribute_level=7,  # 超出范围
            secondary_level=1,
            skill_level=1,
        )
    except ValueError as e:
        print(f"✓ 捕获无效等级错误: {e}")

    # 测试无效的编码长度
    try:
        decode_matrix("12345")  # 长度不足
    except ValueError as e:
        print(f"✓ 捕获无效编码长度错误: {e}")

    # 测试无效的编码字符
    try:
        decode_matrix("X0D331")  # 无效字符
    except ValueError as e:
        print(f"✓ 捕获无效编码字符错误: {e}")

    print()


def demo_practical_example():
    """演示实际应用示例"""
    print("=" * 60)
    print("9. 实际应用示例")
    print("=" * 60)

    # 假设用户拥有以下武器
    user_weapons = [
        {"weapon_id": "wpn_wand_0005", "name": "星极", "rarity": 5, "type": "WAND"},
        {"weapon_id": "wpn_sword_0012", "name": "银灰", "rarity": 6, "type": "SWORD"},
        {"weapon_id": "wpn_claym_0006", "name": "陈", "rarity": 6, "type": "CLAYM"},
    ]

    # 武器的属性组合
    weapon_stats = {
        "wpn_wand_0005": {
            "attribute": "gat_passive_attr_wisd",
            "secondary": "gat_passive_attr_atk",
            "skill": "gst_passive_ult",
        },
        "wpn_sword_0012": {
            "attribute": "gat_passive_attr_str",
            "secondary": "gat_passive_attr_crirate",
            "skill": "gst_passive_crit",
        },
        "wpn_claym_0006": {
            "attribute": "gat_passive_attr_main",
            "secondary": "gat_passive_attr_hp",
            "skill": "gst_passive_smash",
        },
    }

    # 用户的等级配置
    user_levels = {
        "wpn_wand_0005": (3, 3, 1),
        "wpn_sword_0012": (6, 6, 3),
        "wpn_claym_0006": (4, 5, 2),
    }

    print("用户武器和基质配置:")
    for weapon in user_weapons:
        weapon_id = weapon["weapon_id"]
        stats = weapon_stats[weapon_id]
        levels = user_levels[weapon_id]

        # 编码
        code = encode_matrix(
            stats["attribute"],
            stats["secondary"],
            stats["skill"],
            levels[0],
            levels[1],
            levels[2],
        )

        # 获取描述
        description = get_code_description(code)

        print(f"\n{weapon['name']} ({weapon['rarity']}★ {weapon['type']})")
        print(f"  编码: {code}")
        print(f"  属性: {description}")
        print(f"  等级: {levels[0]}/{levels[1]}/{levels[2]}")

    print()


def main():
    """主函数"""
    print("宝藏基质矩阵编码工具演示")
    print()

    demo_basic_encoding()
    demo_basic_decoding()
    demo_encode_decode_roundtrip()
    demo_code_description()
    demo_combinations()
    demo_matrix_code_class()
    demo_attribute_mapping()
    demo_error_handling()
    demo_practical_example()

    print("=" * 60)
    print("演示完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
