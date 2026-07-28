<template>
  <div ref="containerRef" class="matrix-view">
    <!-- 工具栏 -->
    <div class="matrix-toolbar">
      <v-btn-group density="compact" variant="outlined">
        <v-btn
          :color="viewMode === 'grid' ? 'primary' : undefined"
          size="small"
          @click="viewMode = 'grid'"
        >
          <v-icon size="small">mdi-grid</v-icon>
          <span class="ml-1">网格</span>
        </v-btn>
        <v-btn
          :color="viewMode === 'table' ? 'primary' : undefined"
          size="small"
          @click="viewMode = 'table'"
        >
          <v-icon size="small">mdi-table</v-icon>
          <span class="ml-1">表格</span>
        </v-btn>
      </v-btn-group>

      <v-spacer />

      <v-chip
        v-if="stats"
        color="info"
        size="small"
        variant="tonal"
      >
        已收集: {{ stats.owned }} / {{ stats.total }}
        ({{ stats.completion_rate }}%)
      </v-chip>

      <v-btn
        icon
        :loading="loading"
        size="small"
        variant="text"
        @click="refreshData"
      >
        <v-icon>mdi-refresh</v-icon>
      </v-btn>
    </div>

    <!-- 筛选器 -->
    <MatrixFilters
      v-model:filters="filters"
      :attribute-ids="attributeIds"
      :attribute-names="attributeNames"
      :secondary-ids="secondaryIds"
      :secondary-names="secondaryNames"
      :skill-ids="skillIds"
      :skill-names="skillNames"
      @update:filters="onFiltersChange"
    />

    <!-- 矩阵内容 -->
    <div v-if="!loading" class="matrix-content">
      <!-- 网格视图 -->
      <div
        v-if="viewMode === 'grid'"
        ref="gridRef"
        class="matrix-grid"
        @scroll="onGridScroll"
      >
        <!-- 固定表头：基础属性 -->
        <div class="matrix-header sticky-top">
          <div class="matrix-corner">
            <span class="text-caption">附加属性 \ 基础属性</span>
          </div>
          <div
            v-for="attrId in filteredAttributeIds"
            :key="attrId"
            class="matrix-header-cell"
          >
            <span class="text-caption font-weight-bold">
              {{ attributeNames[attrId] || attrId }}
            </span>
          </div>
        </div>

        <!-- 矩阵行 -->
        <div
          v-for="secId in filteredSecondaryIds"
          :key="secId"
          class="matrix-row-group"
        >
          <!-- 附加属性分组标题 -->
          <div class="matrix-secondary-header">
            <span class="text-subtitle-2 font-weight-bold">
              {{ secondaryNames[secId] || secId }}
            </span>
            <v-chip color="grey" size="x-small" variant="tonal">
              {{ getSecondaryOwnedCount(secId) }}/{{ getSecondaryTotalCount(secId) }}
            </v-chip>
          </div>

          <!-- 技能属性行 -->
          <div
            v-for="skillId in filteredSkillIds"
            :key="`${secId}-${skillId}`"
            class="matrix-row"
          >
            <!-- 技能属性标签 -->
            <div class="matrix-row-header">
              <span class="text-caption">
                {{ skillNames[skillId] || skillId }}
              </span>
            </div>

            <!-- 单元格 -->
            <div
              v-for="attrId in filteredAttributeIds"
              :key="attrId + '-' + secId + '-' + skillId"
              class="matrix-cell"
              :class="getCellClass(attrId, secId, skillId)"
              :style="getCellStyle()"
              @click="onCellClick(attrId, secId, skillId)"
              @mouseenter="onCellHover(attrId, secId, skillId)"
              @mouseleave="onCellLeave"
            >
              <template v-if="getBestCell(attrId, secId, skillId)">
                <div class="cell-content">
                  <v-icon
                    v-if="getBestCell(attrId, secId, skillId)?.is_max_level"
                    class="cell-star"
                    color="amber"
                    size="x-small"
                  >
                    mdi-star
                  </v-icon>
                  <span class="cell-code">
                    {{ getBestCell(attrId, secId, skillId)?.code }}
                  </span>
                  <span class="cell-level">
                    {{ formatLevel(getBestCell(attrId, secId, skillId)) }}
                  </span>
                </div>
              </template>
              <template v-else>
                <div class="cell-empty">
                  <span class="cell-code-empty">
                    {{ getCellCode(attrId, secId, skillId) }}
                  </span>
                </div>
              </template>
            </div>
          </div>
        </div>
      </div>

      <!-- 表格视图 -->
      <div v-else class="matrix-table-container">
        <v-table density="compact" hover>
          <thead>
            <tr>
              <th class="text-caption">编码</th>
              <th class="text-caption">基础属性</th>
              <th class="text-caption">附加属性</th>
              <th class="text-caption">技能属性</th>
              <th class="text-caption">等级</th>
              <th class="text-caption">武器</th>
              <th class="text-caption">状态</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="cell in filteredCells"
              :key="cell.code"
              :class="{ 'bg-yellow-lighten-4': cell.is_max_level }"
              @click="onTableCellClick(cell)"
            >
              <td class="text-caption font-weight-bold">{{ cell.code }}</td>
              <td class="text-caption">{{ cell.attribute_name }}</td>
              <td class="text-caption">{{ cell.secondary_name }}</td>
              <td class="text-caption">{{ cell.skill_name }}</td>
              <td class="text-caption">{{ formatLevel(cell) }}</td>
              <td class="text-caption">
                <template v-if="cell.owned">
                  <v-chip :color="getRarityColor(cell.weapon_rarity)" size="x-small">
                    {{ cell.weapon_name }}
                  </v-chip>
                </template>
                <template v-else>
                  <span class="text-grey">-</span>
                </template>
              </td>
              <td>
                <v-icon
                  v-if="cell.owned"
                  :color="cell.is_max_level ? 'amber' : 'success'"
                  size="small"
                >
                  {{ cell.is_max_level ? 'mdi-star' : 'mdi-check-circle' }}
                </v-icon>
                <v-icon v-else color="grey" size="small">
                  mdi-circle-outline
                </v-icon>
              </td>
            </tr>
          </tbody>
        </v-table>
      </div>
    </div>

    <!-- 加载状态 -->
    <div v-else class="matrix-loading">
      <v-progress-circular color="primary" indeterminate />
      <span class="ml-2">加载矩阵数据...</span>
    </div>

    <!-- 悬停提示 -->
    <v-menu
      v-model="showTooltip"
      :close-on-content-click="false"
      location="top"
      :target="tooltipTarget"
    >
      <v-card max-width="300" min-width="200">
        <v-card-text class="pa-2">
          <div v-if="hoveredCell" class="tooltip-content">
            <div class="text-subtitle-2 font-weight-bold mb-1">
              {{ hoveredCell.code }}
            </div>
            <div class="text-caption">
              <div>{{ hoveredCell.attribute_name }} Lv.{{ hoveredCell.attribute_level }}</div>
              <div>{{ hoveredCell.secondary_name }} Lv.{{ hoveredCell.secondary_level }}</div>
              <div>{{ hoveredCell.skill_name }} Lv.{{ hoveredCell.skill_level }}</div>
            </div>
            <v-divider class="my-1" />
            <div v-if="hoveredCell.owned" class="text-caption">
              <v-icon class="mr-1" color="success" size="x-small">mdi-check-circle</v-icon>
              已拥有: {{ hoveredCell.weapon_name }}
            </div>
            <div v-else class="text-caption text-grey">
              <v-icon class="mr-1" size="x-small">mdi-circle-outline</v-icon>
              未拥有
            </div>
          </div>
        </v-card-text>
      </v-card>
    </v-menu>

    <!-- 详情对话框 -->
    <v-dialog v-model="showDetail" max-width="400">
      <v-card v-if="selectedCell">
        <v-card-title class="text-h6">
          基质详情
        </v-card-title>
        <v-card-text>
          <div class="detail-code mb-2">
            <span class="text-h4 font-weight-bold">{{ selectedCell.code }}</span>
          </div>
          <v-list density="compact">
            <v-list-item>
              <template #prepend>
                <v-icon color="primary">mdi-chevron-right</v-icon>
              </template>
              <v-list-item-title>
                {{ selectedCell.attribute_name }} Lv.{{ selectedCell.attribute_level }}
              </v-list-item-title>
            </v-list-item>
            <v-list-item>
              <template #prepend>
                <v-icon color="secondary">mdi-chevron-right</v-icon>
              </template>
              <v-list-item-title>
                {{ selectedCell.secondary_name }} Lv.{{ selectedCell.secondary_level }}
              </v-list-item-title>
            </v-list-item>
            <v-list-item>
              <template #prepend>
                <v-icon color="accent">mdi-chevron-right</v-icon>
              </template>
              <v-list-item-title>
                {{ selectedCell.skill_name }} Lv.{{ selectedCell.skill_level }}
              </v-list-item-title>
            </v-list-item>
          </v-list>

          <v-divider class="my-2" />

          <div v-if="selectedCell.owned">
            <v-list density="compact">
              <v-list-item>
                <template #prepend>
                  <v-icon>mdi-sword</v-icon>
                </template>
                <v-list-item-title>{{ selectedCell.weapon_name }}</v-list-item-title>
                <template #append>
                  <v-chip
                    :color="getRarityColor(selectedCell.weapon_rarity)"
                    size="x-small"
                  >
                    {{ selectedCell.weapon_rarity }}★
                  </v-chip>
                </template>
              </v-list-item>
              <v-list-item>
                <template #prepend>
                  <v-icon :color="selectedCell.is_max_level ? 'amber' : 'success'">
                    {{ selectedCell.is_max_level ? 'mdi-star' : 'mdi-check-circle' }}
                  </v-icon>
                </template>
                <v-list-item-title>
                  {{ selectedCell.is_max_level ? '已满级' : '已拥有' }}
                </v-list-item-title>
              </v-list-item>
            </v-list>
          </div>
          <div v-else class="text-center py-2">
            <v-icon color="grey" size="large">mdi-circle-outline</v-icon>
            <div class="text-caption text-grey mt-1">未拥有此基质组合</div>
          </div>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showDetail = false">关闭</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import MatrixFilters from './MatrixFilters.vue'

// ============================================================================
// 类型定义
// ============================================================================

interface MatrixCellData {
  code: string
  weapon_id: string | null
  weapon_name: string | null
  weapon_rarity: number | null
  weapon_type: string | null
  attribute_id: string
  attribute_name: string
  attribute_level: number
  secondary_id: string
  secondary_name: string
  secondary_level: number
  skill_id: string
  skill_name: string
  skill_level: number
  owned: boolean
  is_max_level: boolean
}

interface MatrixViewResponse {
  matrix: Record<string, MatrixCellData>
  stats: {
    total: number
    owned: number
    max_level: number
    completion_rate: number
  }
  attribute_ids: string[]
  secondary_ids: string[]
  skill_ids: string[]
  attribute_names: Record<string, string>
  secondary_names: Record<string, string>
  skill_names: Record<string, string>
}

interface Filters {
  showOwnedOnly: boolean
  attributeId: string | null
  secondaryId: string | null
  skillId: string | null
  searchCode: string
}

// ============================================================================
// 状态
// ============================================================================

const containerRef = ref<HTMLElement>()
const gridRef = ref<HTMLElement>()
const loading = ref(false)
const viewMode = ref<'grid' | 'table'>('grid')

// 数据
const matrixData = ref<Record<string, MatrixCellData>>({})
const stats = ref<{
  total: number
  owned: number
  max_level: number
  completion_rate: number
} | null>(null)
const attributeIds = ref<string[]>([])
const secondaryIds = ref<string[]>([])
const skillIds = ref<string[]>([])
const attributeNames = ref<Record<string, string>>({})
const secondaryNames = ref<Record<string, string>>({})
const skillNames = ref<Record<string, string>>({})

// 筛选器
const filters = ref<Filters>({
  showOwnedOnly: false,
  attributeId: null,
  secondaryId: null,
  skillId: null,
  searchCode: '',
})

// 悬停提示
const showTooltip = ref(false)
const tooltipTarget = ref<HTMLElement>()
const hoveredCell = ref<MatrixCellData | null>(null)

// 详情对话框
const showDetail = ref(false)
const selectedCell = ref<MatrixCellData | null>(null)

// ============================================================================
// 计算属性
// ============================================================================

const filteredAttributeIds = computed(() => {
  if (filters.value.attributeId) {
    return [filters.value.attributeId]
  }
  return attributeIds.value
})

const filteredSecondaryIds = computed(() => {
  if (filters.value.secondaryId) {
    return [filters.value.secondaryId]
  }
  return secondaryIds.value
})

const filteredSkillIds = computed(() => {
  if (filters.value.skillId) {
    return [filters.value.skillId]
  }
  return skillIds.value
})

const filteredCells = computed(() => {
  let cells = Object.values(matrixData.value)

  if (filters.value.showOwnedOnly) {
    cells = cells.filter(cell => cell.owned)
  }

  if (filters.value.attributeId) {
    cells = cells.filter(cell => cell.attribute_id === filters.value.attributeId)
  }

  if (filters.value.secondaryId) {
    cells = cells.filter(cell => cell.secondary_id === filters.value.secondaryId)
  }

  if (filters.value.skillId) {
    cells = cells.filter(cell => cell.skill_id === filters.value.skillId)
  }

  if (filters.value.searchCode) {
    const search = filters.value.searchCode.toUpperCase()
    cells = cells.filter(cell => cell.code.includes(search))
  }

  return cells
})

// ============================================================================
// 方法
// ============================================================================

async function fetchMatrixData() {
  loading.value = true
  try {
    const response = await fetch('/api/profiles/matrix_view')
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    const data: MatrixViewResponse = await response.json()
    matrixData.value = data.matrix
    stats.value = data.stats
    attributeIds.value = data.attribute_ids
    secondaryIds.value = data.secondary_ids
    skillIds.value = data.skill_ids
    attributeNames.value = data.attribute_names
    secondaryNames.value = data.secondary_names
    skillNames.value = data.skill_names
  } catch (error) {
    console.error('Failed to fetch matrix data:', error)
  } finally {
    loading.value = false
  }
}

async function refreshData() {
  await fetchMatrixData()
}

function getCellCode(attrId: string, secId: string, skillId: string): string {
  // 生成一个占位编码（等级1-1-1）
  const attrCode = attributeIds.value.indexOf(attrId).toString(16).toUpperCase()
  const secCode = secondaryIds.value.indexOf(secId).toString(16).toUpperCase()
  const skillCode = skillIds.value.indexOf(skillId).toString(16).toUpperCase()
  return `${attrCode}${secCode}${skillCode}111`
}

function getBestCell(attrId: string, secId: string, skillId: string): MatrixCellData | null {
  // 查找该属性组合中已拥有的最高等级单元格
  let bestCell: MatrixCellData | null = null
  let bestLevel = -1

  for (let attrLevel = 6; attrLevel >= 1; attrLevel--) {
    for (let secLevel = 6; secLevel >= 1; secLevel--) {
      for (let skillLevel = 3; skillLevel >= 1; skillLevel--) {
        const attrIdx = attributeIds.value.indexOf(attrId)
        const secIdx = secondaryIds.value.indexOf(secId)
        const skillIdx = skillIds.value.indexOf(skillId)

        const attrCode = attrIdx.toString(16).toUpperCase()
        const secCode = secIdx.toString(16).toUpperCase()
        const skillCode = skillIdx.toString(16).toUpperCase()

        const code = `${attrCode}${secCode}${skillCode}${attrLevel}${secLevel}${skillLevel}`
        const cell = matrixData.value[code]

        if (cell && cell.owned) {
          const level = attrLevel * 100 + secLevel * 10 + skillLevel
          if (level > bestLevel) {
            bestLevel = level
            bestCell = cell
          }
        }
      }
    }
  }

  return bestCell
}

function getCellClass(attrId: string, secId: string, skillId: string): string[] {
  const classes: string[] = []
  const cell = getBestCell(attrId, secId, skillId)

  if (cell) {
    classes.push('cell-owned')
    if (cell.is_max_level) {
      classes.push('cell-max-level')
    } else {
      classes.push(`cell-level-${cell.attribute_level}`)
    }
  } else {
    classes.push('cell-empty')
  }

  return classes
}

function getCellStyle(): Record<string, string> {
  return {
    width: '60px',
    height: '60px',
  }
}

function getSecondaryOwnedCount(secId: string): number {
  let count = 0
  for (const cell of Object.values(matrixData.value)) {
    if (cell.secondary_id === secId && cell.owned) {
      count++
    }
  }
  return count
}

function getSecondaryTotalCount(secId: string): number {
  let count = 0
  for (const cell of Object.values(matrixData.value)) {
    if (cell.secondary_id === secId) {
      count++
    }
  }
  return count
}

function formatLevel(cell: MatrixCellData | null): string {
  if (!cell) return ''
  return `${cell.attribute_level}-${cell.secondary_level}-${cell.skill_level}`
}

function getRarityColor(rarity: number | null): string {
  if (!rarity) return 'grey'
  switch (rarity) {
    case 3: { return 'blue'
    }
    case 4: { return 'purple'
    }
    case 5: { return 'orange'
    }
    case 6: { return 'red'
    }
    default: { return 'grey'
    }
  }
}

function onFiltersChange(newFilters: Filters) {
  filters.value = newFilters
}

function onCellClick(attrId: string, secId: string, skillId: string) {
  const cell = getBestCell(attrId, secId, skillId)
  if (cell) {
    selectedCell.value = cell
    showDetail.value = true
  }
}

function onCellHover(attrId: string, secId: string, skillId: string, event?: MouseEvent) {
  const cell = getBestCell(attrId, secId, skillId)
  if (cell) {
    hoveredCell.value = cell
    tooltipTarget.value = event?.target as HTMLElement
    showTooltip.value = true
  }
}

function onCellLeave() {
  showTooltip.value = false
  hoveredCell.value = null
}

function onTableCellClick(cell: MatrixCellData) {
  selectedCell.value = cell
  showDetail.value = true
}

function onGridScroll() {
  // 可以在这里处理滚动事件，例如实现虚拟滚动
}

// ============================================================================
// 生命周期
// ============================================================================

onMounted(() => {
  fetchMatrixData()
})

watch(viewMode, () => {
  // 切换视图时可能需要重新布局
  nextTick(() => {
    if (gridRef.value) {
      gridRef.value.scrollTop = 0
      gridRef.value.scrollLeft = 0
    }
  })
})

// 暴露方法给父组件
defineExpose({
  refreshData,
})
</script>

<style scoped>
.matrix-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  gap: 12px;
}

.matrix-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px;
  background: rgb(var(--v-theme-surface));
  border-radius: 8px;
}

.matrix-content {
  flex: 1;
  overflow: auto;
  border: 1px solid rgba(var(--v-border-color), 0.12);
  border-radius: 8px;
}

.matrix-grid {
  display: flex;
  flex-direction: column;
  min-width: max-content;
}

.matrix-header {
  display: flex;
  position: sticky;
  top: 0;
  z-index: 10;
  background: rgb(var(--v-theme-surface));
}

.matrix-corner {
  width: 80px;
  min-width: 80px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-right: 1px solid rgba(var(--v-border-color), 0.12);
  border-bottom: 1px solid rgba(var(--v-border-color), 0.12);
  background: rgb(var(--v-theme-surface-variant));
}

.matrix-header-cell {
  width: 60px;
  min-width: 60px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-right: 1px solid rgba(var(--v-border-color), 0.12);
  border-bottom: 1px solid rgba(var(--v-border-color), 0.12);
  background: rgb(var(--v-theme-surface-variant));
  writing-mode: vertical-lr;
  text-orientation: mixed;
  padding: 4px;
}

.matrix-row-group {
  display: flex;
  flex-direction: column;
}

.matrix-secondary-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 8px;
  background: rgb(var(--v-theme-surface-variant));
  border-bottom: 1px solid rgba(var(--v-border-color), 0.12);
  position: sticky;
  left: 0;
  z-index: 5;
}

.matrix-row {
  display: flex;
}

.matrix-row-header {
  width: 80px;
  min-width: 80px;
  height: 60px;
  display: flex;
  align-items: center;
  padding: 0 8px;
  border-right: 1px solid rgba(var(--v-border-color), 0.12);
  border-bottom: 1px solid rgba(var(--v-border-color), 0.12);
  background: rgb(var(--v-theme-surface));
  position: sticky;
  left: 0;
  z-index: 5;
}

.matrix-cell {
  width: 60px;
  min-width: 60px;
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-right: 1px solid rgba(var(--v-border-color), 0.12);
  border-bottom: 1px solid rgba(var(--v-border-color), 0.12);
  cursor: pointer;
  transition: all 0.2s ease;
}

.matrix-cell:hover {
  background: rgba(var(--v-theme-primary), 0.1);
  transform: scale(1.05);
  z-index: 1;
}

.cell-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.cell-star {
  position: absolute;
  top: 2px;
  right: 2px;
}

.cell-code {
  font-size: 10px;
  font-weight: bold;
  line-height: 1;
}

.cell-level {
  font-size: 9px;
  opacity: 0.7;
  line-height: 1;
}

.cell-empty {
  display: flex;
  align-items: center;
  justify-content: center;
}

.cell-code-empty {
  font-size: 9px;
  opacity: 0.3;
}

/* 单元格状态样式 */
.cell-owned {
  background: rgba(var(--v-theme-success), 0.1);
}

.cell-max-level {
  background: rgba(var(--v-theme-warning), 0.2);
  box-shadow: inset 0 0 0 2px rgba(var(--v-theme-warning), 0.5);
}

.cell-level-1 { background: rgba(var(--v-theme-info), 0.1); }
.cell-level-2 { background: rgba(var(--v-theme-info), 0.2); }
.cell-level-3 { background: rgba(var(--v-theme-info), 0.3); }
.cell-level-4 { background: rgba(var(--v-theme-info), 0.4); }
.cell-level-5 { background: rgba(var(--v-theme-info), 0.5); }
.cell-level-6 { background: rgba(var(--v-theme-info), 0.6); }

.matrix-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
}

.matrix-table-container {
  max-height: 600px;
  overflow: auto;
}

.tooltip-content {
  font-size: 12px;
}

.detail-code {
  text-align: center;
  padding: 8px;
  background: rgba(var(--v-theme-primary), 0.1);
  border-radius: 8px;
}
</style>
