# 宝藏基质矩阵视图组件

这个模块提供了宝藏基质的矩阵可视化功能，可以直观地展示所有 840 种基质组合。

## 功能特性

### 1. 矩阵可视化
- **横轴**: 基础属性（5种）
- **纵轴**: 附加属性（12种）× 技能属性（14种）
- **单元格**: 显示编码、等级、武器图标
- **颜色编码**: 根据等级或稀有度着色

### 2. 编码系统

采用6位混合编码格式：

```
格式：[基础属性ID][附加属性ID][技能属性ID][基础等级][附加等级][技能等级]
      └─1位十六进制─┘└─1位十六进制─┘└─1位十六进制─┘└─1位十进制─┘└─1位十进制─┘└─1位十进制─┘
```

#### 编码示例

| 组合 | 编码 | 说明 |
|------|------|------|
| 智识3 + 攻击提升3 + 夜幕1 | `40D331` | 基础4=智识, 附加0=攻击, 技能D=夜幕, 等级3-3-1 |
| 主能力3 + 暴击3 + 切骨1 | `113331` | 基础1=主能力, 附加1=暴击, 技能3=切骨, 等级3-3-1 |
| 力量5 + 生命提升6 + 粉碎2 | `249562` | 基础2=力量, 附加4=生命, 技能9=粉碎, 等级5-6-2 |

### 3. 交互功能

- **悬停提示**: 显示完整的基质信息
- **点击详情**: 查看武器信息和等级
- **筛选器**: 按属性、已拥有状态筛选
- **搜索**: 按编码搜索
- **视图切换**: 网格视图/表格视图

### 4. 统计功能

- **总体统计**: 总组合数、已拥有数、满级数、完成度
- **按属性统计**: 按基础/附加/技能属性分别统计
- **按武器类型统计**: SWORD/CLAYM/LANCE/PISTOL/WAND
- **按稀有度统计**: 3★/4★/5★/6★

### 5. 导出功能

- **CSV**: 可在 Excel 中打开分析
- **JSON**: 包含完整数据结构
- **图片**: 截取当前矩阵视图

## 组件结构

```
frontend/src/components/matrix/
├── index.ts              # 组件导出
├── MatrixView.vue        # 主矩阵视图组件
├── MatrixFilters.vue     # 筛选器组件
├── MatrixLegend.vue      # 图例组件
├── MatrixStats.vue       # 统计面板组件
├── MatrixExport.vue      # 导出功能组件
└── README.md             # 本文件
```

## 使用方法

### 1. 在页面中集成

```vue
<template>
  <MatrixView
    ref="matrixViewRef"
    style="height: 600px;"
  />
</template>

<script setup>
import { MatrixView } from '@/components/matrix'
</script>
```

### 2. 使用筛选器

```vue
<template>
  <MatrixFilters
    v-model:filters="filters"
    :attribute-ids="attributeIds"
    :secondary-ids="secondaryIds"
    :skill-ids="skillIds"
    :attribute-names="attributeNames"
    :secondary-names="secondaryNames"
    :skill-names="skillNames"
  />
</template>
```

### 3. 显示统计信息

```vue
<template>
  <MatrixStats
    :attribute-names="attributeNames"
    :secondary-names="secondaryNames"
    :skill-names="skillNames"
    @update:stats="stats = $event"
  />
</template>
```

### 4. 导出数据

```vue
<template>
  <MatrixExport
    :target-element="matrixViewRef?.$el"
    :matrix-data="matrixData"
  />
</template>
```

## API 接口

### 1. 获取矩阵视图数据

```http
GET /api/profiles/matrix_view?profile={name}
```

**响应:**
```json
{
  "matrix": {
    "40D331": {
      "code": "40D331",
      "weapon_id": "wpn_wand_0005",
      "weapon_name": "星极",
      "attribute_id": "gat_passive_attr_wisd",
      "attribute_name": "智识提升",
      "attribute_level": 3,
      "secondary_id": "gat_passive_attr_atk",
      "secondary_name": "攻击提升",
      "secondary_level": 3,
      "skill_id": "gst_passive_ult",
      "skill_name": "夜幕",
      "skill_level": 1,
      "owned": true,
      "is_max_level": false
    }
  },
  "stats": {
    "total": 840,
    "owned": 156,
    "max_level": 12,
    "completion_rate": 18.57
  },
  "attribute_ids": ["gat_passive_attr_agi", ...],
  "secondary_ids": ["gat_passive_attr_atk", ...],
  "skill_ids": ["gst_passive_break", ...],
  "attribute_names": {"gat_passive_attr_agi": "敏捷提升", ...},
  "secondary_names": {"gat_passive_attr_atk": "攻击提升", ...},
  "skill_names": {"gst_passive_break": "残暴", ...}
}
```

### 2. 获取统计信息

```http
GET /api/profiles/matrix_stats?profile={name}
```

**响应:**
```json
{
  "total_combinations": 840,
  "owned_combinations": 156,
  "max_level_combinations": 12,
  "completion_rate": 18.57,
  "by_attribute": {
    "gat_passive_attr_agi": {
      "total": 168,
      "owned": 32,
      "max_level": 3,
      "completion_rate": 19.05
    }
  },
  "by_secondary": {...},
  "by_skill": {...},
  "by_weapon_type": {...},
  "by_rarity": {...}
}
```

### 3. 更新矩阵视图配置

```http
POST /api/profiles/matrix_view_config
Content-Type: application/json

{
  "show_owned_only": false,
  "filter_weapon_type": null,
  "filter_rarity": null,
  "highlight_max_level": true,
  "color_mode": "level",
  "cell_size": 60,
  "show_code": true,
  "show_level": true,
  "show_weapon_icon": true
}
```

## 数据模型

### MatrixCellData

```typescript
interface MatrixCellData {
  code: string                    // 6位编码
  weapon_id: string | null        // 武器ID
  weapon_name: string | null      // 武器名称
  weapon_rarity: number | null    // 武器稀有度
  weapon_type: string | null      // 武器类型
  attribute_id: string            // 基础属性ID
  attribute_name: string          // 基础属性名称
  attribute_level: number         // 基础属性等级
  secondary_id: string            // 附加属性ID
  secondary_name: string          // 附加属性名称
  secondary_level: number         // 附加属性等级
  skill_id: string                // 技能属性ID
  skill_name: string              // 技能属性名称
  skill_level: number             // 技能属性等级
  owned: boolean                  // 是否已拥有
  is_max_level: boolean           // 是否满级
}
```

### MatrixViewConfig

```typescript
interface MatrixViewConfig {
  show_owned_only: boolean        // 只显示已拥有
  filter_weapon_type: string | null  // 武器类型过滤
  filter_rarity: number | null    // 稀有度过滤
  highlight_max_level: boolean    // 高亮满级
  color_mode: 'level' | 'rarity' | 'type'  // 颜色模式
  cell_size: number               // 单元格大小
  show_code: boolean              // 显示编码
  show_level: boolean             // 显示等级
  show_weapon_icon: boolean       // 显示武器图标
}
```

## 技术实现

### 1. 性能优化

- **虚拟滚动**: 只渲染可视区域的行
- **Canvas 渲染**: 对于840个单元格，Canvas 比 DOM 更高效
- **数据缓存**: 使用 localStorage 缓存矩阵数据
- **懒加载**: 首次加载时只加载拥有数据

### 2. 响应式设计

```css
@media (max-width: 1200px) {
  .matrix-cell { width: 60px; height: 60px; }
}
@media (max-width: 960px) {
  .matrix-cell { width: 50px; height: 50px; }
  .matrix-code { font-size: 10px; }
}
```

### 3. 无障碍设计

- **键盘导航**: 使用方向键在矩阵中移动
- **屏幕阅读器**: 为每个单元格添加 ARIA 标签
- **高对比度模式**: 支持系统高对比度设置

## 扩展功能

### 1. 热力图模式

用颜色深浅表示拥有率，可以直观地看到哪些属性组合更容易获得。

### 2. 推荐系统

基于用户现有组合推荐下一步目标，帮助用户优化收集策略。

### 3. 社区对比

匿名统计全服玩家的拥有情况，让用户了解自己的收集进度。

### 4. 历史追踪

记录用户随时间的收集进度，生成收集趋势图。

## 依赖项

- **Vue 3**: 前端框架
- **Vuetify 3**: UI 组件库
- **html2canvas**: 图片导出功能（可选）

## 注意事项

1. **数据同步**: 矩阵数据与宝藏基质配置同步，修改配置后需要刷新矩阵视图
2. **性能考虑**: 840个单元格的渲染可能需要优化，建议使用虚拟滚动
3. **导出功能**: 图片导出需要 html2canvas 库，如果未安装会提示错误
4. **浏览器兼容**: 需要支持 ES6+ 的现代浏览器

## 更新日志

### v1.0.0 (2026-07-28)
- 初始版本
- 实现基础矩阵视图
- 实现筛选和搜索功能
- 实现统计面板
- 实现导出功能
