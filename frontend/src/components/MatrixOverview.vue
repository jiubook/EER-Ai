<template>
  <v-expansion-panel value="基质总览">
    <v-expansion-panel-title>
      <v-icon class="mr-2">mdi-table</v-icon>
      基质总览
      <v-chip class="ml-2" color="success" size="small" variant="flat">
        {{ ownedCount }} / {{ totalCount }}
      </v-chip>
    </v-expansion-panel-title>
    <v-expansion-panel-text>
      <v-alert border="start" class="mb-4" type="info" variant="tonal">
        按技能属性分组查看所有基质组合。横轴为基础属性，纵轴为附加属性。左键点击武器图标查看基质属性，右键点击切换是否拥有该武器的基质。已满级（6/6/3）的武器会显示彩虹边框。
      </v-alert>

      <!-- 星级过滤开关 -->
      <div class="d-flex align-center gap-2 mb-4">
        <span class="text-body-2 text-medium-emphasis">显示星级：</span>
        <v-chip-group v-model="selectedRarities" column multiple>
          <v-chip color="primary" filter size="small" value="3" variant="outlined">3★</v-chip>
          <v-chip color="primary" filter size="small" value="4" variant="outlined">4★</v-chip>
          <v-chip color="primary" filter size="small" value="5" variant="outlined">5★</v-chip>
          <v-chip color="primary" filter size="small" value="6" variant="outlined">6★</v-chip>
          <v-chip color="primary" filter size="small" value="custom" variant="outlined">自定义</v-chip>
        </v-chip-group>
      </div>

      <!-- 每个技能属性一个section -->
      <template v-for="group in matrixGroups" :key="group.skillStatId">
        <div class="d-flex align-center mb-2 mt-4">
          <div class="skill-icon-header me-2">
            <img alt="基质底板" class="skill-icon-bg" :src="essenceBgSrc" />
            <img v-if="group.skillIconUrl" alt="技能" class="skill-icon-img" :src="group.skillIconUrl" />
          </div>
          <h4>{{ group.skillName }}</h4>
          <v-chip class="ml-2" color="primary" size="x-small" variant="tonal">
            {{ group.weaponCount }} 把武器
          </v-chip>
        </div>

        <div class="matrix-table-wrapper">
          <table class="matrix-table">
            <thead>
              <tr>
                <th class="matrix-corner">
                  <span class="corner-label">基础属性 →<br />附加属性 ↓</span>
                </th>
                <th v-for="col in group.columns" :key="col.statId" class="matrix-col-header">
                  <span class="col-header-text">{{ col.name }}</span>
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in group.rows" :key="row.statId">
                <td class="matrix-row-header">
                  <span class="row-header-text">{{ row.name }}</span>
                </td>
                <td
                  v-for="(cell, colIdx) in row.cells"
                  :key="colIdx"
                  class="matrix-cell"
                  :class="{ 'matrix-cell--empty': cell.weaponIds.length === 0 }"
                >
                  <div class="matrix-cell-content">
                    <div
                      v-for="weaponId in cell.weaponIds"
                      :key="weaponId"
                      class="matrix-weapon-item"
                      :data-weapon-id="weaponId"
                      @click="showWeaponDetail(weaponId)"
                      @contextmenu.prevent="toggleWeaponOwnership(weaponId)"
                    >
                      <v-tooltip location="top" open-delay="0">
                        <template #activator="{ props }">
                          <div v-bind="props" class="matrix-weapon-icon-wrapper" :class="{
                            'weapon-not-owned': !isWeaponOwned(weaponId),
                            'weapon-maxed': isWeaponMaxed(weaponId),
                          }">
                            <custom-stat-icon v-if="isCustomEntry(weaponId)" hide-name :name="getCustomStatName(weaponId)" :skill-stat-id="getCustomStatSkillId(weaponId)" small />
                            <item-icon v-else :item-id="weaponId" />
                            <div v-if="isWeaponMaxed(weaponId)" class="rainbow-border" />
                          </div>
                        </template>
                        <span>{{ getWeaponStatsText(weaponId) }}</span>
                      </v-tooltip>
                    </div>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>

      <!-- 空状态 -->
      <div v-if="matrixGroups.length === 0" class="text-center py-6">
        <v-icon class="mb-2" color="medium-emphasis" size="48">mdi-table-off</v-icon>
        <div class="text-medium-emphasis">当前筛选条件下没有匹配的基质数据</div>
      </div>
    </v-expansion-panel-text>
  </v-expansion-panel>

  <!-- 武器详情弹窗（共享组件） -->
  <weapon-detail-dialog
    v-model="detailDialog"
    :weapon-id="detailWeaponId"
    :is-owned="isDetailOwned"
    :affix1="detailAffix1"
    :affix2="detailAffix2"
    :affix3="detailAffix3"
    :same-stat-weapons="sameStatWeaponsForDialog"
    :custom-stats="customStats"
    @update:affix1="detailAffix1 = $event"
    @update:affix2="detailAffix2 = $event"
    @update:affix3="detailAffix3 = $event"
    @toggle-ownership="toggleDetailOwnership"
    @remove-entry="removeEntry"
  />
</template>

<script lang="ts" setup>
import { computed, onMounted, ref, watch } from 'vue'
import CustomStatIcon from '@/components/CustomStatIcon.vue'
import ItemIcon from '@/components/ItemIcon.vue'
import WeaponDetailDialog, { type SameStatWeapon } from '@/components/WeaponDetailDialog.vue'
import { type TreasureMatrixEntry, useProfiles } from '@/composables/useProfiles'
import { useRarityFilters } from '@/composables/useRarityFilters'
import { useStaticData } from '@/utils/gameData/staticData'
import { getGemTagName } from '@/utils/gameData/weapon'

const { weaponsMap, essencesMap, matrixIcons } = useStaticData()
const {
  treasureMatrix,
  addTreasureMatrixEntry,
  removeTreasureMatrixEntry,
  updateTreasureMatrix,
  updateWeaponPriority,
} = useProfiles()
const { selectedRarities } = useRarityFilters()

// 底板图片路径
const essenceBgSrc = computed(() => matrixIcons.value.essenceBg)

// --- 自定义基质相关 ---

/** 自定义宝藏基质属性配置列表 */
const customStats = ref<Array<{ name: string; attribute: string | null; secondary: string | null; skill: string | null }>>([])

/** 从后端获取配置中的自定义宝藏基质属性列表 */
async function fetchCustomStats() {
  try {
    const res = await fetch('/api/config')
    const config = await res.json()
    customStats.value = config.treasure_essence_stats || []
  } catch (error) {
    console.error('获取自定义宝藏基质配置失败:', error)
  }
}

/** 判断是否为自定义基质条目 */
function isCustomEntry(weaponId: string): boolean {
  return weaponId.startsWith('custom_stat_')
}

/** 获取自定义基质的显示名称 */
function getCustomStatName(weaponId: string): string {
  const index = Number.parseInt(weaponId.replace('custom_stat_', ''), 10)
  return customStats.value[index]?.name || `自定义基质 ${index + 1}`
}

/** 获取自定义基质的技能属性ID */
function getCustomStatSkillId(weaponId: string): string | null {
  const index = Number.parseInt(weaponId.replace('custom_stat_', ''), 10)
  return customStats.value[index]?.skill || null
}

onMounted(() => {
  fetchCustomStats()
})

// --- 弹窗状态 ---
const detailDialog = ref(false)
const detailWeaponId = ref<string | null>(null)
const detailAffix1 = ref(1)
const detailAffix2 = ref(1)
const detailAffix3 = ref(1)

// --- Profile 数据 ---
const matrixEntryByWeaponId = computed(
  () => new Map(treasureMatrix.value.map((entry) => [entry.weapon_id, entry])),
)
const ownedWeaponIds = computed(() => new Set(matrixEntryByWeaponId.value.keys()))

// --- 同类武器列表（供弹窗使用） ---
const sameStatWeaponsForDialog = computed<SameStatWeapon[]>(() => {
  if (!detailWeaponId.value) return []
  return getSameStatWeapons(detailWeaponId.value).map((id) => ({
    id,
    name: weaponsMap.value.get(id)?.name || id,
    levelText: getMatrixLevelText(id),
  }))
})

// --- 矩阵分组核心逻辑 ---

interface MatrixCell {
  weaponIds: string[]
}

interface MatrixRow {
  statId: string
  name: string
  cells: MatrixCell[]
}

interface MatrixColumn {
  statId: string
  name: string
}

interface MatrixGroup {
  skillStatId: string
  skillName: string
  skillIconUrl: string | null
  weaponCount: number
  columns: MatrixColumn[]
  rows: MatrixRow[]
}

/** 获取所有武器（含自定义）的属性信息 */
interface WeaponWithStats {
  id: string
  attributeStatId: string | null
  secondaryStatId: string | null
  skillStatId: string | null
  rarity: number
  isCustom: boolean
}

const allWeaponsWithStats = computed<WeaponWithStats[]>(() => {
  const result: WeaponWithStats[] = []

  // 内置武器
  for (const [id, weapon] of weaponsMap.value.entries()) {
    result.push({
      id,
      attributeStatId: weapon.attributeStatId,
      secondaryStatId: weapon.secondaryStatId,
      skillStatId: weapon.skillStatId,
      rarity: weapon.rarity,
      isCustom: false,
    })
  }

  // 自定义基质
  for (let i = 0; i < customStats.value.length; i++) {
    const stat = customStats.value[i]
    if (!stat) continue
    const syntheticId = `custom_stat_${i}`
    result.push({
      id: syntheticId,
      attributeStatId: stat.attribute,
      secondaryStatId: stat.secondary,
      skillStatId: stat.skill,
      rarity: 6, // 自定义基质视为 6★
      isCustom: true,
    })
  }

  return result
})

/** 按技能属性分组，构建矩阵 */
const matrixGroups = computed<MatrixGroup[]>(() => {
  // 按星级过滤
  const filtered = allWeaponsWithStats.value.filter((w) => {
    return selectedRarities.value.includes(String(w.rarity))
  })

  // 按 skillStatId 分组
  const grouped = new Map<string, WeaponWithStats[]>()
  for (const weapon of filtered) {
    const key = weapon.skillStatId || '__none__'
    if (!grouped.has(key)) grouped.set(key, [])
    grouped.get(key)!.push(weapon)
  }

  const groups: MatrixGroup[] = []

  // 按技能名称排序
  const sortedEntries = Array.from(grouped.entries()).toSorted((a, b) => {
    const nameA = a[0] === '__none__' ? '无技能属性' : getGemTagName(a[0])
    const nameB = b[0] === '__none__' ? '无技能属性' : getGemTagName(b[0])
    return nameA.localeCompare(nameB)
  })

  for (const [skillStatId, weapons] of sortedEntries) {
    // 收集该组内所有唯一的 基础属性 和 附加属性（null 用 __none__ 占位）
    const attrStatIds = new Set<string>()
    const secStatIds = new Set<string>()

    for (const w of weapons) {
      attrStatIds.add(w.attributeStatId || '__none__')
      secStatIds.add(w.secondaryStatId || '__none__')
    }

    // 排序列和行（按名称排序，__none__ 排最后）
    const columns: MatrixColumn[] = Array.from(attrStatIds)
      .map((id) => ({ statId: id, name: id === '__none__' ? '无基础属性' : getGemTagName(id) }))
      .toSorted((a, b) => {
        if (a.statId === '__none__') return 1
        if (b.statId === '__none__') return -1
        return a.name.localeCompare(b.name)
      })

    const rowStatIds = Array.from(secStatIds)
      .map((id) => ({ statId: id, name: id === '__none__' ? '无附加属性' : getGemTagName(id) }))
      .toSorted((a, b) => {
        if (a.statId === '__none__') return 1
        if (b.statId === '__none__') return -1
        return a.name.localeCompare(b.name)
      })

    // 构建矩阵行
    const rows: MatrixRow[] = rowStatIds.map((rowStat) => ({
      statId: rowStat.statId,
      name: rowStat.name,
      cells: columns.map((colStat) => {
        const matchingWeapons = weapons
          .filter(
            (w) =>
              (w.attributeStatId || '__none__') === colStat.statId &&
              (w.secondaryStatId || '__none__') === rowStat.statId,
          )
          .toSorted((a, b) => b.rarity - a.rarity)
        return { weaponIds: matchingWeapons.map((w) => w.id) }
      }),
    }))

    const skillName = skillStatId === '__none__' ? '无技能属性' : getGemTagName(skillStatId)
    const skillIconUrl =
      skillStatId !== '__none__' ? matrixIcons.value.skills[skillStatId] || null : null

    groups.push({
      skillStatId,
      skillName,
      skillIconUrl,
      weaponCount: weapons.length,
      columns,
      rows,
    })
  }

  return groups
})

// --- 统计 ---
const totalCount = computed(() => weaponsMap.value.size)
const ownedCount = computed(() => ownedWeaponIds.value.size)

// --- 辅助函数 ---

function isWeaponOwned(weaponId: string): boolean {
  return ownedWeaponIds.value.has(weaponId)
}

function isWeaponMaxed(weaponId: string): boolean {
  const entry = matrixEntryByWeaponId.value.get(weaponId)
  return (
    entry !== undefined &&
    entry.affix1_level === 6 &&
    entry.affix2_level === 6 &&
    entry.affix3_level === 3
  )
}

const isDetailOwned = computed(() => {
  const weaponId = detailWeaponId.value
  if (!weaponId) return false
  return isWeaponOwned(weaponId)
})

async function toggleWeaponOwnership(weaponId: string) {
  if (isWeaponOwned(weaponId)) {
    await removeTreasureMatrixEntry(weaponId)
  } else {
    // 自定义条目使用配置中的名称，普通武器使用 weaponsMap 中的名称
    let weaponName: string
    if (isCustomEntry(weaponId)) {
      weaponName = getCustomStatName(weaponId)
    } else {
      const weapon = weaponsMap.value.get(weaponId)
      weaponName = weapon?.name || weaponId
    }
    await addTreasureMatrixEntry({
      weapon_id: weaponId,
      weapon_name: weaponName,
      affix1_level: 1,
      affix2_level: 1,
      affix3_level: 1,
      include_in_calculation: true,
    })
  }
}

async function toggleDetailOwnership() {
  const weaponId = detailWeaponId.value
  if (!weaponId) return
  await toggleWeaponOwnership(weaponId)
}

function showWeaponDetail(weaponId: string) {
  detailWeaponId.value = weaponId
  detailDialog.value = true
}

async function removeEntry(weaponId: string) {
  await removeTreasureMatrixEntry(weaponId)
  detailDialog.value = false
}

function getWeaponStatsText(weaponId: string): string {
  // 自定义条目：从配置中读取属性
  if (isCustomEntry(weaponId)) {
    const index = Number.parseInt(weaponId.replace('custom_stat_', ''), 10)
    const stat = customStats.value[index]
    if (!stat) return '自定义基质'
    const parts: string[] = []
    if (stat.attribute) parts.push(getGemTagName(stat.attribute))
    if (stat.secondary) parts.push(getGemTagName(stat.secondary))
    if (stat.skill) parts.push(getGemTagName(stat.skill))
    return parts.join('、') || '自定义基质'
  }

  const weapon = weaponsMap.value.get(weaponId)
  if (!weapon) return '未知武器'

  const parts: string[] = []
  if (weapon.attributeStatId) parts.push(getGemTagName(weapon.attributeStatId))
  if (weapon.secondaryStatId) parts.push(getGemTagName(weapon.secondaryStatId))
  if (weapon.skillStatId) parts.push(getGemTagName(weapon.skillStatId))

  return parts.join('、') || '无属性'
}

function getMatrixLevelText(weaponId: string): string {
  const entry = matrixEntryByWeaponId.value.get(weaponId)
  if (!entry) return '未配置'
  return `+${entry.affix1_level} / +${entry.affix2_level} / +${entry.affix3_level}`
}

function getSameStatWeapons(weaponId: string): string[] {
  // 自定义条目：从配置中读取属性
  if (isCustomEntry(weaponId)) {
    const index = Number.parseInt(weaponId.replace('custom_stat_', ''), 10)
    const stat = customStats.value[index]
    if (!stat) return []
    const sameWeapons: string[] = []
    // 与内置武器比较
    for (const [id, w] of weaponsMap.value.entries()) {
      if (
        w.attributeStatId === (stat.attribute || null) &&
        w.secondaryStatId === (stat.secondary || null) &&
        w.skillStatId === (stat.skill || null)
      ) {
        sameWeapons.push(id)
      }
    }
    return sameWeapons
  }

  const weapon = weaponsMap.value.get(weaponId)
  if (!weapon) return []
  const sameWeapons: string[] = []
  for (const [id, w] of weaponsMap.value.entries()) {
    if (
      id !== weaponId &&
      w.attributeStatId === weapon.attributeStatId &&
      w.secondaryStatId === weapon.secondaryStatId &&
      w.skillStatId === weapon.skillStatId
    ) {
      sameWeapons.push(id)
    }
  }
  return sameWeapons
}

// 弹窗打开时加载等级
watch([detailDialog, detailWeaponId], () => {
  if (!detailDialog.value) return
  const weaponId = detailWeaponId.value
  if (!weaponId) return

  const entry = matrixEntryByWeaponId.value.get(weaponId)
  detailAffix1.value = entry?.affix1_level ?? 1
  detailAffix2.value = entry?.affix2_level ?? 1
  detailAffix3.value = entry?.affix3_level ?? 1
})

// 等级变化时自动保存（防抖）
let detailSaveTimer: ReturnType<typeof setTimeout> | null = null
watch([detailAffix1, detailAffix2, detailAffix3], async () => {
  const weaponId = detailWeaponId.value
  if (!weaponId || !isWeaponOwned(weaponId)) return

  if (detailSaveTimer) clearTimeout(detailSaveTimer)
  detailSaveTimer = setTimeout(async () => {
    const entry = matrixEntryByWeaponId.value.get(weaponId)
    if (entry) {
      entry.affix1_level = detailAffix1.value
      entry.affix2_level = detailAffix2.value
      entry.affix3_level = detailAffix3.value
      await updateTreasureMatrix([...treasureMatrix.value])
    }
    detailSaveTimer = null
  }, 400)
})
</script>

<style scoped lang="scss">
.skill-icon-header {
  position: relative;
  width: 1.5rem;
  height: 1.5rem;
  flex-shrink: 0;
}

.skill-icon-bg {
  position: absolute;
  width: 100%;
  height: 100%;
  object-fit: cover;
  z-index: 0;
  border-radius: 4px;
}

.skill-icon-img {
  position: absolute;
  width: 100%;
  height: 100%;
  object-fit: cover;
  z-index: 1;
  transform: translate(5%, -5%);
}

.matrix-table-wrapper {
  overflow-x: auto;
  margin-bottom: 1.5rem;
  border: 1px solid rgba(var(--v-border-color), 0.12);
  border-radius: 12px;
  background: rgba(var(--v-theme-surface), 0.5);
}

.matrix-table {
  width: 100%;
  border-collapse: collapse;
  min-width: 400px;

  th,
  td {
    padding: 8px;
    border: 1px solid rgba(var(--v-border-color), 0.08);
    text-align: center;
    vertical-align: middle;
  }
}

.matrix-corner {
  background: rgba(var(--v-theme-primary), 0.04);
  width: 100px;
  min-width: 100px;
  position: sticky;
  left: 0;
  z-index: 2;
}

.corner-label {
  font-size: 0.7rem;
  color: rgba(var(--v-theme-on-surface), 0.52);
  font-weight: 600;
  line-height: 1.4;
}

.matrix-col-header {
  background: rgba(var(--v-theme-primary), 0.04);
  min-width: 80px;
}

.col-header-text {
  font-size: 0.78rem;
  font-weight: 700;
  color: rgba(var(--v-theme-on-surface), 0.78);
  white-space: nowrap;
}

.matrix-row-header {
  background: rgba(var(--v-theme-primary), 0.04);
  width: 100px;
  min-width: 100px;
  position: sticky;
  left: 0;
  z-index: 1;
}

.row-header-text {
  font-size: 0.78rem;
  font-weight: 700;
  color: rgba(var(--v-theme-on-surface), 0.78);
  white-space: nowrap;
}

.matrix-cell {
  min-width: 60px;
  min-height: 48px;
  transition: background 0.15s;

  &:hover {
    background: rgba(var(--v-theme-primary), 0.04);
  }

  &--empty {
    background: rgba(var(--v-theme-on-surface), 0.01);
  }
}

.matrix-cell-content {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  justify-content: center;
  align-items: center;
  min-height: 40px;
}

.matrix-weapon-item {
  width: 2.5rem;
  height: 2.5rem;
  cursor: pointer;
  position: relative;
  transition: transform 0.15s;

  &:hover {
    transform: scale(1.1);
  }
}

.matrix-weapon-icon-wrapper {
  width: 100%;
  height: 100%;
  position: relative;
  border-radius: 6px;
  overflow: hidden;
  transition: opacity 0.15s, filter 0.15s;

  &.weapon-not-owned {
    opacity: 0.4;
    filter: grayscale(0.8);
  }

  &.weapon-maxed {
    animation: rainbow-glow 3s linear infinite;
  }
}

.rainbow-border {
  position: absolute;
  inset: -3px;
  border-radius: 8px;
  background: linear-gradient(
    45deg,
    #fff,
    #ff4ada,
    #ff4e4e,
    #ff9832,
    #ff0,
    #0f0,
    #00ffff,
    #79a0fd,
    #d46eff,
    #ff8df0,
    #fff
  );
  background-size: 400% 400%;
  animation: rainbow-rotate 3s linear infinite;
  z-index: -1;
  pointer-events: none;
}

@keyframes rainbow-rotate {
  0% {
    background-position: 0% 50%;
  }
  50% {
    background-position: 100% 50%;
  }
  100% {
    background-position: 0% 50%;
  }
}

@keyframes rainbow-glow {
  0%,
  100% {
    box-shadow: 0 0 10px rgba(255, 0, 0, 0.8);
  }
  14% {
    box-shadow: 0 0 10px rgba(255, 127, 0, 0.8);
  }
  28% {
    box-shadow: 0 0 10px rgba(255, 255, 0, 0.8);
  }
  42% {
    box-shadow: 0 0 10px rgba(0, 255, 0, 0.8);
  }
  57% {
    box-shadow: 0 0 10px rgba(0, 127, 255, 0.8);
  }
  71% {
    box-shadow: 0 0 10px rgba(0, 0, 255, 0.8);
  }
  85% {
    box-shadow: 0 0 10px rgba(127, 0, 255, 0.8);
  }
}
</style>
