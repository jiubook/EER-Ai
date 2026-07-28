"""
宝藏基质矩阵编码工具测试
"""

import pytest
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
)


class TestMatrixCodec:
    """测试矩阵编码工具"""

    def test_encode_matrix_basic(self):
        """测试基本编码功能"""
        # 智识3 + 攻击提升3 + 夜幕1
        code = encode_matrix(
            attribute_id="gat_passive_attr_wisd",
            secondary_id="gat_passive_attr_atk",
            skill_id="gst_passive_ult",
            attribute_level=3,
            secondary_level=3,
            skill_level=1,
        )
        assert code == "40D331"

    def test_encode_matrix_all_attributes(self):
        """测试所有基础属性编码"""
        expected_codes = {
            "gat_passive_attr_agi": "0",  # 敏捷
            "gat_passive_attr_main": "1",  # 主能力
            "gat_passive_attr_str": "2",   # 力量
            "gat_passive_attr_will": "3",  # 意志
            "gat_passive_attr_wisd": "4",  # 智识
        }

        for attr_id, expected_code in expected_codes.items():
            code = encode_matrix(
                attribute_id=attr_id,
                secondary_id="gat_passive_attr_atk",
                skill_id="gst_passive_break",
                attribute_level=1,
                secondary_level=1,
                skill_level=1,
            )
            assert code[0] == expected_code

    def test_encode_matrix_all_secondary(self):
        """测试所有附加属性编码"""
        expected_codes = {
            "gat_passive_attr_atk": "0",       # 攻击
            "gat_passive_attr_crirate": "1",   # 暴击率
            "gat_passive_attr_firedam": "2",   # 灼热伤害
            "gat_passive_attr_heal": "3",      # 治疗效率
            "gat_passive_attr_hp": "4",        # 生命
            "gat_passive_attr_icedam": "5",    # 寒冷伤害
            "gat_passive_attr_magicdam": "6",  # 法术伤害
            "gat_passive_attr_naturaldam": "7", # 自然伤害
            "gat_passive_attr_phydam": "8",    # 物理伤害
            "gat_passive_attr_physpell": "9",  # 源石技艺
            "gat_passive_attr_pulsedam": "A",  # 电磁伤害
            "gat_passive_attr_usp": "B",       # 终结技充能
        }

        for sec_id, expected_code in expected_codes.items():
            code = encode_matrix(
                attribute_id="gat_passive_attr_agi",
                secondary_id=sec_id,
                skill_id="gst_passive_break",
                attribute_level=1,
                secondary_level=1,
                skill_level=1,
            )
            assert code[1] == expected_code

    def test_encode_matrix_all_skills(self):
        """测试所有技能属性编码"""
        expected_codes = {
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

        for skill_id, expected_code in expected_codes.items():
            code = encode_matrix(
                attribute_id="gat_passive_attr_agi",
                secondary_id="gat_passive_attr_atk",
                skill_id=skill_id,
                attribute_level=1,
                secondary_level=1,
                skill_level=1,
            )
            assert code[2] == expected_code

    def test_encode_matrix_levels(self):
        """测试等级编码"""
        # 基础属性等级 1-6
        for level in range(1, 7):
            code = encode_matrix(
                attribute_id="gat_passive_attr_agi",
                secondary_id="gat_passive_attr_atk",
                skill_id="gst_passive_break",
                attribute_level=level,
                secondary_level=1,
                skill_level=1,
            )
            assert code[3] == str(level)

        # 附加属性等级 1-6
        for level in range(1, 7):
            code = encode_matrix(
                attribute_id="gat_passive_attr_agi",
                secondary_id="gat_passive_attr_atk",
                skill_id="gst_passive_break",
                attribute_level=1,
                secondary_level=level,
                skill_level=1,
            )
            assert code[4] == str(level)

        # 技能属性等级 1-3
        for level in range(1, 4):
            code = encode_matrix(
                attribute_id="gat_passive_attr_agi",
                secondary_id="gat_passive_attr_atk",
                skill_id="gst_passive_break",
                attribute_level=1,
                secondary_level=1,
                skill_level=level,
            )
            assert code[5] == str(level)

    def test_encode_matrix_invalid_attribute(self):
        """测试无效的基础属性ID"""
        with pytest.raises(ValueError, match="无效的基础属性 ID"):
            encode_matrix(
                attribute_id="invalid_id",
                secondary_id="gat_passive_attr_atk",
                skill_id="gst_passive_break",
                attribute_level=1,
                secondary_level=1,
                skill_level=1,
            )

    def test_encode_matrix_invalid_secondary(self):
        """测试无效的附加属性ID"""
        with pytest.raises(ValueError, match="无效的附加属性 ID"):
            encode_matrix(
                attribute_id="gat_passive_attr_agi",
                secondary_id="invalid_id",
                skill_id="gst_passive_break",
                attribute_level=1,
                secondary_level=1,
                skill_level=1,
            )

    def test_encode_matrix_invalid_skill(self):
        """测试无效的技能属性ID"""
        with pytest.raises(ValueError, match="无效的技能属性 ID"):
            encode_matrix(
                attribute_id="gat_passive_attr_agi",
                secondary_id="gat_passive_attr_atk",
                skill_id="invalid_id",
                attribute_level=1,
                secondary_level=1,
                skill_level=1,
            )

    def test_encode_matrix_invalid_level(self):
        """测试无效的等级"""
        # 基础属性等级超出范围
        with pytest.raises(ValueError, match="基础属性等级必须在 1-6 之间"):
            encode_matrix(
                attribute_id="gat_passive_attr_agi",
                secondary_id="gat_passive_attr_atk",
                skill_id="gst_passive_break",
                attribute_level=7,
                secondary_level=1,
                skill_level=1,
            )

        # 附加属性等级超出范围
        with pytest.raises(ValueError, match="附加属性等级必须在 1-6 之间"):
            encode_matrix(
                attribute_id="gat_passive_attr_agi",
                secondary_id="gat_passive_attr_atk",
                skill_id="gst_passive_break",
                attribute_level=1,
                secondary_level=0,
                skill_level=1,
            )

        # 技能属性等级超出范围
        with pytest.raises(ValueError, match="技能属性等级必须在 1-3 之间"):
            encode_matrix(
                attribute_id="gat_passive_attr_agi",
                secondary_id="gat_passive_attr_atk",
                skill_id="gst_passive_break",
                attribute_level=1,
                secondary_level=1,
                skill_level=4,
            )

    def test_decode_matrix_basic(self):
        """测试基本解码功能"""
        # 智识3 + 攻击提升3 + 夜幕1
        matrix = decode_matrix("40D331")

        assert matrix.attribute_id == "gat_passive_attr_wisd"
        assert matrix.secondary_id == "gat_passive_attr_atk"
        assert matrix.skill_id == "gst_passive_ult"
        assert matrix.attribute_level == 3
        assert matrix.secondary_level == 3
        assert matrix.skill_level == 1

    def test_decode_matrix_names(self):
        """测试解码后的名称属性"""
        matrix = decode_matrix("40D331")

        assert matrix.attribute_name == "智识提升"
        assert matrix.secondary_name == "攻击提升"
        assert matrix.skill_name == "夜幕"

    def test_decode_matrix_invalid_length(self):
        """测试无效长度的编码"""
        with pytest.raises(ValueError, match="编码长度必须为6"):
            decode_matrix("12345")

    def test_decode_matrix_invalid_code(self):
        """测试无效的编码字符"""
        with pytest.raises(ValueError, match="无效的基础属性编码"):
            decode_matrix("X0D331")

    def test_encode_decode_roundtrip(self):
        """测试编码-解码往返"""
        # 测试多个组合
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

    def test_get_all_combinations_with_levels(self):
        """测试获取所有组合（包含等级）"""
        combinations = get_all_combinations(include_levels=True)

        # 总数应该是 5 × 12 × 14 × 6 × 6 × 3 = 90720
        assert len(combinations) == 90720

        # 所有组合应该是唯一的
        assert len(set(combinations)) == 90720

        # 所有组合应该是6位
        for code in combinations:
            assert len(code) == 6

    def test_get_all_combinations_without_levels(self):
        """测试获取所有组合（不包含等级）"""
        combinations = get_all_combinations(include_levels=False)

        # 总数应该是 5 × 12 × 14 = 840
        assert len(combinations) == 840

        # 所有组合应该是唯一的
        assert len(set(combinations)) == 840

    def test_get_code_description(self):
        """测试获取编码描述"""
        description = get_code_description("40D331")
        assert description == "智识提升3 + 攻击提升3 + 夜幕1"

    def test_count_combinations(self):
        """测试组合统计"""
        stats = count_combinations()

        assert stats["total"] == 90720
        assert stats["attribute_types"] == 5
        assert stats["secondary_types"] == 12
        assert stats["skill_types"] == 14
        assert stats["attribute_levels"] == 6
        assert stats["secondary_levels"] == 6
        assert stats["skill_levels"] == 3
        assert stats["unique_combinations"] == 840

    def test_matrix_code_dataclass(self):
        """测试MatrixCode数据类"""
        matrix = MatrixCode(
            attribute_id="gat_passive_attr_wisd",
            secondary_id="gat_passive_attr_atk",
            skill_id="gst_passive_ult",
            attribute_level=3,
            secondary_level=3,
            skill_level=1,
        )

        # 测试属性
        assert matrix.attribute_name == "智识提升"
        assert matrix.secondary_name == "攻击提升"
        assert matrix.skill_name == "夜幕"

        # 测试编码方法
        assert matrix.encode() == "40D331"

        # 测试to_dict方法
        data = matrix.to_dict()
        assert data["code"] == "40D331"
        assert data["attribute_name"] == "智识提升"
        assert data["secondary_name"] == "攻击提升"
        assert data["skill_name"] == "夜幕"


class TestMatrixCodecIntegration:
    """集成测试"""

    def test_encode_decode_all_combinations(self):
        """测试编码-解码所有组合"""
        combinations = get_all_combinations(include_levels=True)

        for code in combinations:
            # 解码
            matrix = decode_matrix(code)

            # 重新编码
            re_encoded = encode_matrix(
                matrix.attribute_id,
                matrix.secondary_id,
                matrix.skill_id,
                matrix.attribute_level,
                matrix.secondary_level,
                matrix.skill_level,
            )

            # 验证一致性
            assert re_encoded == code

    def test_attribute_ids_consistency(self):
        """测试属性ID一致性"""
        # 确保所有属性ID都是唯一的
        assert len(ATTRIBUTE_IDS) == len(set(ATTRIBUTE_IDS))
        assert len(SECONDARY_IDS) == len(set(SECONDARY_IDS))
        assert len(SKILL_IDS) == len(set(SKILL_IDS))

    def test_code_format_consistency(self):
        """测试编码格式一致性"""
        combinations = get_all_combinations(include_levels=True)

        for code in combinations:
            # 验证长度
            assert len(code) == 6

            # 验证字符范围
            assert code[0] in "01234"  # 基础属性
            assert code[1] in "0123456789AB"  # 附加属性
            assert code[2] in "0123456789ABCD"  # 技能属性
            assert code[3] in "123456"  # 基础属性等级
            assert code[4] in "123456"  # 附加属性等级
            assert code[5] in "123"  # 技能属性等级


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
