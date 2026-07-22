<template>
  <v-expansion-panel value="武器总览">
    <v-expansion-panel-title>
      <v-icon class="mr-2">mdi-sword-cross</v-icon>
      武器总览
      <v-chip class="ml-2" color="success" size="small" variant="flat">
        {{ ownedCount }} / {{ totalCount }}
      </v-chip>
    </v-expansion-panel-title>
    <v-expansion-panel-text>
      <v-alert border="start" class="mb-4" type="info" variant="tonal">
        左键点击武器图标查看基质属性，右键点击切换是否拥有该武器的基质。已满级（6/6/3）的武器会显示彩虹边框。鼠标悬停在有相同属性的武器上会显示粒子连线。
      </v-alert>

      <!-- 星级过滤开关 -->
      <div class="d-flex align-center gap-2 mb-4">
        <span class="text-body-2 text-medium-emphasis">显示星级：</span>
        <v-chip-group v-model="selectedRarities" column multiple>
          <v-chip
            color="primary"
            filter
            size="small"
            value="3"
            variant="outlined"
          >
            3★
          </v-chip>
          <v-chip
            color="primary"
            filter
            size="small"
            value="4"
            variant="outlined"
          >
            4★
          </v-chip>
          <v-chip
            color="primary"
            filter
            size="small"
            value="5"
            variant="outlined"
          >
            5★
          </v-chip>
          <v-chip
            color="primary"
            filter
            size="small"
            value="6"
            variant="outlined"
          >
            6★
          </v-chip>
          <v-chip
            color="primary"
            filter
            size="small"
            value="custom"
            variant="outlined"
          >
            自定义
          </v-chip>
        </v-chip-group>
      </div>

      <!-- 自定义基质重合检测按钮 -->
      <v-btn
        class="mb-4"
        color="warning"
        prepend-icon="mdi-swap-horizontal"
        size="small"
        variant="tonal"
        @click="checkCustomOverlap"
      >
        检查自定义基质重合
      </v-btn>

      <!-- 武器总览容器（包含连线层） -->
      <div ref="containerRef" class="weapon-overview-container">
        <!-- 连线层 -->
        <div class="connection-lines-layer">
          <div
            v-for="(line, index) in connectionLines"
            :key="index"
            class="connection-line"
            :style="line.style"
          />
        </div>

        <!-- 自定义基质区段 -->
        <template v-if="showCustomSection && customMatrixEntries.length > 0">
          <div class="d-flex align-center mb-1 mt-3">
            <v-icon class="me-2" color="#ff5a36">mdi-diamond-stone</v-icon>
            <h4>自定义基质</h4>
          </div>
          <div class="weapon-overview-grid">
            <div
              v-for="entry in customMatrixEntries"
              :key="entry.syntheticId"
              class="weapon-overview-item"
              :data-weapon-id="entry.syntheticId"
              @click="showWeaponDetail(entry.syntheticId)"
              @contextmenu.prevent="toggleWeaponOwnership(entry.syntheticId)"
              @mouseenter="handleWeaponMouseEnter(entry.syntheticId)"
              @mouseleave="handleWeaponMouseLeave"
            >
              <!-- 武器悬浮面板：显示自定义基质的三条属性 -->
              <v-tooltip location="top" open-delay="0">
                <template #activator="{ props }">
                  <div v-bind="props" class="h-100">
                    <div
                      class="weapon-icon-wrapper"
                      :class="{
                        'weapon-not-owned': !isWeaponOwned(entry.syntheticId),
                        'weapon-maxed': isWeaponMaxed(entry.syntheticId),
                      }"
                    >
                      <custom-stat-icon :name="entry.displayName" />

                      <!-- 满级的彩虹边框 -->
                      <div v-if="isWeaponMaxed(entry.syntheticId)" class="rainbow-border" />
                    </div>
                  </div>
                </template>
                <span>{{ getWeaponStatsText(entry.syntheticId) }}</span>
              </v-tooltip>
            </div>
          </div>
        </template>

        <template v-for="wType in filteredWeaponTypes" :key="wType.id">
          <div class="d-flex align-center mb-1 mt-3">
            <img
              :alt="wType.name"
              class="group-icon me-2"
              :src="wType.iconUrl"
            />
            <h4>{{ wType.name }}</h4>
          </div>
          <div class="weapon-overview-grid">
            <div
              v-for="weaponId in wType.weaponIds"
              :key="weaponId"
              class="weapon-overview-item"
              :data-weapon-id="weaponId"
              @click="showWeaponDetail(weaponId)"
              @contextmenu.prevent="toggleWeaponOwnership(weaponId)"
              @mouseenter="handleWeaponMouseEnter(weaponId)"
              @mouseleave="handleWeaponMouseLeave"
            >
              <!-- 武器悬浮面板：显示武器的三条基质属性 -->
              <v-tooltip location="top" open-delay="0">
                <template #activator="{ props }">
                  <div v-bind="props" class="h-100">
                    <div
                      class="weapon-icon-wrapper"
                      :class="{
                        'weapon-not-owned': !isWeaponOwned(weaponId),
                        'weapon-maxed': isWeaponMaxed(weaponId),
                        'switch-target-maxed': isSwitchable(weaponId) && isSwitchTargetMaxed(weaponId) && !isWeaponMaxed(weaponId),
                      }"
                    >
                      <item-icon :item-id="weaponId" show-item-name />

                      <!-- 满级的彩虹边框 -->
                      <div v-if="isWeaponMaxed(weaponId)" class="rainbow-border" />
                    </div>
                  </div>
                </template>
                <span>{{ getWeaponStatsText(weaponId) }}</span>
              </v-tooltip>

              <!-- 可切换标记放在灰色滤镜容器外，避免被 opacity/filter 叠加 -->
              <v-chip
                v-if="isSwitchable(weaponId) && !isWeaponMaxed(weaponId)"
                class="switchable-badge"
                color="warning"
                size="x-small"
                variant="flat"
              >
                可切换
              </v-chip>
            </div>
          </div>
        </template>
      </div>
    </v-expansion-panel-text>
  </v-expansion-panel>

  <!-- 武器详情弹窗 -->
  <v-dialog v-model="detailDialog" max-width="600">
    <v-card v-if="detailWeaponId">
      <v-card-item>
        <template #prepend>
          <custom-stat-icon v-if="isCustomEntry(detailWeaponId)" hide-name :name="customEntryName || detailWeaponId" />
          <item-icon v-else class="weapon-icon-detail" :item-id="detailWeaponId" />
        </template>
        <v-card-title>
          <v-text-field
            v-if="isCustomEntry(detailWeaponId)"
            v-model="customEntryName"
            density="compact"
            hide-details
            placeholder="自定义基质名称"
            variant="underlined"
            @blur="saveCustomEntryName"
            @keydown.enter="saveCustomEntryName"
          />
          <template v-else>
            {{ weaponsMap.get(detailWeaponId)?.name || detailWeaponId }}
          </template>
        </v-card-title>
        <v-card-subtitle>{{ getWeaponStatsText(detailWeaponId) }}</v-card-subtitle>
        <template #append>
          <v-btn icon="mdi-close" variant="text" @click="detailDialog = false" />
        </template>
      </v-card-item>
      <v-divider />
      <v-card-text>
        <!-- 当前状态 -->
        <div class="mb-4">
          <div class="text-subtitle-2 mb-1">当前基质等级</div>
          <v-chip :color="isWeaponOwned(detailWeaponId) ? 'primary' : 'grey'" variant="flat">
            {{ getMatrixLevelText(detailWeaponId) }}
          </v-chip>
          <v-chip
            v-if="isWeaponMaxed(detailWeaponId)"
            class="ml-2"
            color="success"
            size="small"
            variant="flat"
          >
            已满级
          </v-chip>
        </div>

        <!-- 优先级设置 -->
        <div class="mb-4">
          <div class="text-subtitle-2 mb-1">基质匹配优先级</div>
          <div class="d-flex flex-wrap align-center ga-2 mb-2">
            <v-chip
              v-for="p in [1, 2, 3, 4, 5, 6, 7, 8, 9]"
              :key="p"
              :color="getWeaponPriority(detailWeaponId!) === p ? 'primary' : undefined"
              size="small"
              :variant="getWeaponPriority(detailWeaponId!) === p ? 'flat' : 'outlined'"
              @click="setWeaponPriority(detailWeaponId!, p)"
            >
              {{ p }}
            </v-chip>
          </div>
          <div class="text-caption text-medium-emphasis" style="line-height: 1.6">
            当扫描到一个无暇基质同时匹配多把武器时，系统会按优先级将该基质分配给优先级最高的武器。<br />
            默认使用武器稀有度作为优先级（6★=6, 5★=5, 4★=4, 3★=3）。<br />
            手动设置 1-9 可覆盖默认值，数值越大越优先。<br />
            已满级（6/6/3）的武器会被自动跳过。
          </div>
        </div>

        <!-- 同类武器（自定义条目不显示） -->
        <div v-if="!isCustomEntry(detailWeaponId) && getSameStatWeapons(detailWeaponId).length > 0">
          <div class="text-subtitle-2 mb-2">同类属性武器</div>
          <div class="d-flex flex-column ga-2">
            <v-card
              v-for="sameId in getSameStatWeapons(detailWeaponId)"
              :key="sameId"
              class="pa-2"
              variant="outlined"
            >
              <div class="d-flex align-center justify-space-between">
                <div class="d-flex align-center ga-2">
                  <item-icon class="weapon-icon-same" :item-id="sameId" />
                  <div>
                    <div class="font-weight-bold text-body-2">
                      {{ weaponsMap.get(sameId)?.name || sameId }}
                    </div>
                    <div class="text-caption text-medium-emphasis">
                      {{ getMatrixLevelText(sameId) }}
                      <span class="ml-1">优先级: {{ getWeaponPriority(sameId) }}</span>
                    </div>
                  </div>
                </div>
                <v-btn
                  color="primary"
                  size="small"
                  variant="tonal"
                  @click="swapMatrix(detailWeaponId!, sameId)"
                >
                  交换
                </v-btn>
              </div>
            </v-card>
          </div>
        </div>
        <div v-else-if="!isCustomEntry(detailWeaponId)" class="text-medium-emphasis text-caption">
          没有其他武器与此武器共享相同属性组合。
        </div>
      </v-card-text>
    </v-card>
  </v-dialog>

  <!-- 自定义基质重合检测弹窗 -->
  <v-dialog v-model="overlapDialog" max-width="700" persistent>
    <v-card>
      <v-card-title class="d-flex align-center">
        <v-icon class="mr-2" color="warning">mdi-alert-circle-outline</v-icon>
        自定义基质重合检测
      </v-card-title>
      <v-card-text>
        <v-alert class="mb-4" type="info" variant="tonal">
          以下自定义基质与内置武器的三个词条完全相同，可选择切换为内置武器。
        </v-alert>
        <div
          v-for="(item, idx) in overlapItems"
          :key="idx"
          class="d-flex align-center mb-3 pa-3 border rounded flex-wrap"
          style="gap: 8px"
        >
          <div class="overlap-icon-wrapper">
            <custom-stat-icon hide-name :name="item.customName" small/>
          </div>
          <span class="font-weight-bold">{{ item.customName }}</span>
          <v-icon size="small">mdi-arrow-left-right</v-icon>
          <div class="overlap-icon-wrapper">
            <item-icon class="weapon-icon-overlap" :item-id="item.matchedWeaponId" />
          </div>
          <span class="font-weight-bold">{{ item.matchedWeaponName }}</span>
          <v-spacer />
          <v-chip-group v-model="item.action" mandatory>
            <v-chip filter size="small" value="ignore" variant="outlined">本次忽略</v-chip>
            <v-chip filter size="small" value="suppress" variant="outlined">不再提示</v-chip>
            <v-chip color="primary" filter size="small" value="switch" variant="outlined">切换</v-chip>
          </v-chip-group>
        </div>
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn @click="overlapDialog = false">取消</v-btn>
        <v-btn color="primary" @click="confirmOverlapActions">确认</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script lang="ts" setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import CustomStatIcon from '@/components/CustomStatIcon.vue'
import ItemIcon from '@/components/ItemIcon.vue'
import { type TreasureMatrixEntry, useProfiles } from '@/composables/useProfiles'
import { useRarityFilters } from '@/composables/useRarityFilters'
import { useStaticData } from '@/utils/gameData/staticData'
import { getGemTagName } from '@/utils/gameData/weapon'

const { weaponTypes, weaponsMap } = useStaticData()
const {
  activeProfile,
  treasureMatrix,
  addTreasureMatrixEntry,
  removeTreasureMatrixEntry,
  updateTreasureMatrix,
  updateWeaponPriority,
} = useProfiles()
const { selectedRarities } = useRarityFilters()

// 武器详情弹窗
const detailDialog = ref(false)
const detailWeaponId = ref<string | null>(null)

// --- 武器连线系统 ---

/** 容器引用 */
const containerRef = ref<HTMLElement | null>(null)

/** 当前悬停的武器 ID */
const hoveredWeaponId = ref<string | null>(null)

/** 连线数据 */
interface ConnectionLine {
  style: {
    left: string
    top: string
    width: string
    transform: string
    opacity: number
  }
}

const connectionLines = ref<ConnectionLine[]>([])

/** 获取武器图标元素位置 */
function getWeaponElementPosition(weaponId: string): { x: number; y: number } | null {
  const container = containerRef.value
  if (!container) return null

  const element = container.querySelector(`[data-weapon-id="${weaponId}"]`)
  if (!element) return null

  const containerRect = container.getBoundingClientRect()
  const elementRect = element.getBoundingClientRect()

  return {
    x: elementRect.left - containerRect.left + elementRect.width / 2,
    y: elementRect.top - containerRect.top + elementRect.height / 2,
  }
}

/** 计算两点之间的距离和角度 */
function calculateLine(
  startX: number,
  startY: number,
  endX: number,
  endY: number,
): { length: number; angle: number } {
  const dx = endX - startX
  const dy = endY - startY
  const length = Math.hypot(dx, dy)
  const angle = Math.atan2(dy, dx) * (180 / Math.PI)
  return { length, angle }
}

/** 更新连线 */
function updateConnectionLines() {
  if (!hoveredWeaponId.value) {
    connectionLines.value = []
    return
  }

  const startPos = getWeaponElementPosition(hoveredWeaponId.value)
  if (!startPos) {
    connectionLines.value = []
    return
  }

  const sameWeapons = getSameStatWeapons(hoveredWeaponId.value)
  const newLines: ConnectionLine[] = []

  for (const targetId of sameWeapons) {
    const endPos = getWeaponElementPosition(targetId)
    if (!endPos) continue

    const { length, angle } = calculateLine(
      startPos.x,
      startPos.y,
      endPos.x,
      endPos.y,
    )

    newLines.push({
      style: {
        left: `${startPos.x}px`,
        top: `${startPos.y}px`,
        width: `${length}px`,
        transform: `rotate(${angle}deg)`,
        opacity: 1,
      },
    })
  }

  connectionLines.value = newLines
}

/** 鼠标进入武器 */
function handleWeaponMouseEnter(weaponId: string) {
  hoveredWeaponId.value = weaponId
  updateConnectionLines()
}

/** 鼠标离开武器 */
function handleWeaponMouseLeave() {
  hoveredWeaponId.value = null
  connectionLines.value = []
}

// 监听窗口大小变化，更新连线位置
onMounted(() => {
  window.addEventListener('resize', updateConnectionLines)
})

onUnmounted(() => {
  window.removeEventListener('resize', updateConnectionLines)
  connectionLines.value = []
})

// --- 自定义基质相关 ---

/** 自定义宝藏基质属性配置列表 */
const customStats = ref<Array<{ name: string; attribute: string | null; secondary: string | null; skill: string | null; no_prompt_switch?: boolean }>>([])

// --- 自定义基质与内置武器重合检测 ---

interface OverlapItem {
  customIndex: number
  customName: string
  customWeaponId: string
  matchedWeaponId: string
  matchedWeaponName: string
  action: 'ignore' | 'suppress' | 'switch'
}

const overlapItems = ref<OverlapItem[]>([])
const overlapDialog = ref(false)

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

/** 判断是否为自定义基质条目（weapon_id 以 custom_stat_ 开头） */
function isCustomEntry(weaponId: string | null): boolean {
  return weaponId?.startsWith('custom_stat_') ?? false
}

/** 自定义基质条目列表，用于武器总览展示 */
const customMatrixEntries = computed(() => {
  return customStats.value
    .map((stat, index) => ({
      syntheticId: `custom_stat_${index}`,
      displayName: stat.name || `自定义基质 ${index + 1}`,
      index,
    }))
})

/** 是否显示自定义基质区段（当 6★ 筛选激活时显示） */
const showCustomSection = computed(() => selectedRarities.value.includes('custom'))

/** 自定义条目编辑中的名称 */
const customEntryName = ref('')

// 弹窗打开时，如果是自定义条目，加载其名称
watch([detailDialog, detailWeaponId], () => {
  if (detailDialog.value && isCustomEntry(detailWeaponId.value)) {
    const index = Number.parseInt(detailWeaponId.value!.replace('custom_stat_', ''), 10)
    customEntryName.value = customStats.value[index]?.name || ''
  }
})

/** 保存自定义条目名称到配置和 profile */
async function saveCustomEntryName() {
  if (!isCustomEntry(detailWeaponId.value)) return
  const index = Number.parseInt(detailWeaponId.value!.replace('custom_stat_', ''), 10)
  if (customStats.value[index]) {
    customStats.value[index].name = customEntryName.value
    await postCustomStatsUpdate()
    // 同步更新 profile 中的 weapon_name
    const entry = matrixEntryByWeaponId.value.get(detailWeaponId.value!)
    if (entry) {
      entry.weapon_name = customEntryName.value
      await updateTreasureMatrix([...treasureMatrix.value])
    }
  }
}

/** 将自定义宝藏基质配置保存到后端 */
async function postCustomStatsUpdate() {
  try {
    const res = await fetch('/api/config')
    const currentConfig = await res.json()
    currentConfig.treasure_essence_stats = customStats.value
    await fetch('/api/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(currentConfig),
    })
  } catch (error) {
    console.error('保存自定义宝藏基质配置失败:', error)
  }
}

/**
 * 检查自定义基质与内置武器的词条重合
 * 匹配规则：三个槽位完全相等（含 null 对 null）
 * 检查范围：所有 config 中配置的自定义基质，无论是否在 profiles 中拥有
 */
function checkCustomOverlap() {
  const items: OverlapItem[] = []
  for (let i = 0; i < customStats.value.length; i++) {
    const stat = customStats.value[i]
    if (!stat) continue
    // 跳过已勾选"不再提示"的
    if (stat.no_prompt_switch) continue
    // 跳过属性全为空的条目（已被切换清空）
    if (!stat.attribute && !stat.secondary && !stat.skill) continue

    const syntheticId = `custom_stat_${i}`

    // 遍历所有内置武器，查找三词条完全匹配
    for (const [weaponId, weapon] of weaponsMap.value.entries()) {
      if (
        weapon.attributeStatId === stat.attribute &&
        weapon.secondaryStatId === stat.secondary &&
        weapon.skillStatId === stat.skill
      ) {
        items.push({
          customIndex: i,
          customName: stat.name || `自定义基质 ${i + 1}`,
          customWeaponId: syntheticId,
          matchedWeaponId: weaponId,
          matchedWeaponName: weapon.name,
          action: 'ignore',
        })
      }
    }
  }
  if (items.length === 0) return
  overlapItems.value = items
  overlapDialog.value = true
}

/** 确认重合操作 */
async function confirmOverlapActions() {
  // 记录需要删除的自定义基质索引
  const indicesToDelete: number[] = []

  for (const item of overlapItems.value) {
    if (item.action === 'ignore') continue

    const stat = customStats.value[item.customIndex]
    if (!stat) continue

    if (item.action === 'suppress') {
      stat.no_prompt_switch = true
      await postCustomStatsUpdate()
    }

    if (item.action === 'switch') {
      // 切换 weapon_id，保留 affix 等级，优先级用武器稀有度默认值（不手动设置）
      const entry = matrixEntryByWeaponId.value.get(item.customWeaponId)
      if (entry) {
        const weapon = weaponsMap.value.get(item.matchedWeaponId)
        const newEntries = treasureMatrix.value
          .filter((e) => e.weapon_id !== item.customWeaponId)
          .concat({
            weapon_id: item.matchedWeaponId,
            weapon_name: weapon?.name || item.matchedWeaponName,
            affix1_level: entry.affix1_level,
            affix2_level: entry.affix2_level,
            affix3_level: entry.affix3_level,
            include_in_calculation: entry.include_in_calculation,
            // priority 不设置，使用武器稀有度默认值
          })
        await updateTreasureMatrix(newEntries)
      }
      indicesToDelete.push(item.customIndex)
    }
  }

  // 从大到小排序删除，避免索引偏移问题
  indicesToDelete.sort((a, b) => b - a)
  for (const index of indicesToDelete) {
    customStats.value.splice(index, 1)
  }

  // 更新 treasure_matrix 中所有引用后续自定义基质的索引
  if (indicesToDelete.length > 0) {
    const updatedTreasureMatrix = treasureMatrix.value.map((e) => {
      if (e.weapon_id.startsWith('custom_stat_')) {
        const currentIndex = Number.parseInt(e.weapon_id.replace('custom_stat_', ''), 10)
        // 计算删除后的新索引
        let newIndex = currentIndex
        for (const deletedIndex of indicesToDelete) {
          if (currentIndex > deletedIndex) {
            newIndex--
          }
        }
        if (newIndex !== currentIndex) {
          return { ...e, weapon_id: `custom_stat_${newIndex}` }
        }
      }
      return e
    })
    await updateTreasureMatrix(updatedTreasureMatrix)
    await postCustomStatsUpdate()
  }

  overlapDialog.value = false
  await fetchCustomStats()
}

onMounted(async () => {
  await fetchCustomStats()
  checkCustomOverlap()
})

const matrixEntryByWeaponId = computed(
  () => new Map(treasureMatrix.value.map((entry) => [entry.weapon_id, entry])),
)

// 武器总览会为每个图标多次判断拥有/满级状态，用 Set/Map 避免重复扫描 treasureMatrix。
const ownedWeaponIds = computed(() => new Set(matrixEntryByWeaponId.value.keys()))

const totalCount = computed(() =>
  weaponTypes.value.reduce((sum, wType) => sum + wType.weaponIds.length, 0),
)

const ownedCount = computed(() => ownedWeaponIds.value.size)

// 过滤后的武器类型列表
const filteredWeaponTypes = computed(() => {
  return weaponTypes.value
    .map((wType) => ({
      ...wType,
      weaponIds: wType.weaponIds
        .filter((weaponId) => {
          const weapon = weaponsMap.value.get(weaponId)
          if (!weapon) return false
          return selectedRarities.value.includes(String(weapon.rarity))
        })
        .toSorted((a, b) => {
          // 按稀有度降序排序（6★ -> 3★）
          const wa = weaponsMap.value.get(a)
          const wb = weaponsMap.value.get(b)
          if (wa && wb) return wb.rarity - wa.rarity
          return 0
        }),
    }))
    .filter((wType) => wType.weaponIds.length > 0)
})

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

async function toggleWeaponOwnership(weaponId: string) {
  if (isWeaponOwned(weaponId)) {
    await removeTreasureMatrixEntry(weaponId)
  } else {
    // 自定义条目使用配置中的名称，普通武器使用 weaponsMap 中的名称
    let weaponName: string
    if (isCustomEntry(weaponId)) {
      const index = Number.parseInt(weaponId.replace('custom_stat_', ''), 10)
      weaponName = customStats.value[index]?.name || `自定义基质 ${index + 1}`
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

/**
 * 显示武器详情弹窗（左键点击）
 */
function showWeaponDetail(weaponId: string) {
  detailWeaponId.value = weaponId
  detailDialog.value = true
}

/**
 * 获取武器属性文本
 * 自定义条目从 customStats 配置中读取属性名
 */
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
  if (weapon.attributeStatId) {
    parts.push(getGemTagName(weapon.attributeStatId))
  }
  if (weapon.secondaryStatId) {
    parts.push(getGemTagName(weapon.secondaryStatId))
  }
  if (weapon.skillStatId) {
    parts.push(getGemTagName(weapon.skillStatId))
  }

  return parts.join('、') || '无属性'
}

/**
 * 获取同类武器（相同属性组合）
 * 自定义条目没有真实武器数据，返回空数组
 */
function getSameStatWeapons(weaponId: string): string[] {
  if (isCustomEntry(weaponId)) return []
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

/**
 * 判断武器是否"可切换"：存在同属性、更高优先级、且已拥有的武器
 */
function isSwitchable(weaponId: string): boolean {
  const myPriority = getWeaponPriority(weaponId)
  const sameWeapons = getSameStatWeapons(weaponId)
  return sameWeapons.some(
    (id) => isWeaponOwned(id) && getWeaponPriority(id) >= myPriority,
  )
}

/**
 * 获取可切换的目标武器是否满级（用于灰色呼吸动画）
 */
function isSwitchTargetMaxed(weaponId: string): boolean {
  const myPriority = getWeaponPriority(weaponId)
  const sameWeapons = getSameStatWeapons(weaponId)
  return sameWeapons.some(
    (id) =>
      isWeaponOwned(id)
      && getWeaponPriority(id) >= myPriority
      && isWeaponMaxed(id),
  )
}

/**
 * 获取武器的基质等级文本
 */
function getMatrixLevelText(weaponId: string): string {
  const entry = matrixEntryByWeaponId.value.get(weaponId)
  if (!entry) return '未配置'
  return `+${entry.affix1_level} / +${entry.affix2_level} / +${entry.affix3_level}`
}

/**
 * 获取用户手动设置的优先级（0 表示未设置）
 */
function getUserPriority(weaponId: string): number {
  const profilePriority = activeProfile.value.weapon_priorities?.[weaponId]
  if (profilePriority && profilePriority > 0) return profilePriority
  const entry = matrixEntryByWeaponId.value.get(weaponId)
  return entry?.priority || 0
}

/**
 * 获取武器的有效优先级（未设置时使用稀有度）
 * 自定义条目默认优先级为 6（等同于 6★）
 */
function getWeaponPriority(weaponId: string): number {
  const userP = getUserPriority(weaponId)
  if (userP > 0) return userP
  // 自定义条目默认优先级为 6
  if (isCustomEntry(weaponId)) return 6
  const weapon = weaponsMap.value.get(weaponId)
  return weapon ? weapon.rarity : 0
}

function getEffectivePriorityForSwap(weaponId: string, entry?: TreasureMatrixEntry): number {
  const userPriority = getUserPriority(weaponId) || entry?.priority || 0
  if (userPriority > 0) return userPriority
  const weapon = weaponsMap.value.get(weaponId)
  return weapon ? weapon.rarity : 0
}

/**
 * 设置武器优先级
 */
async function setWeaponPriority(weaponId: string, priority: number) {
  const entry = matrixEntryByWeaponId.value.get(weaponId)
  if (entry) {
    entry.priority = priority
  }
  await updateWeaponPriority(weaponId, priority)
}

/**
 * 交换两把武器的基质数据
 */
async function swapMatrix(weaponAId: string, weaponBId: string) {
  const entries = treasureMatrix.value.map((entry) => ({ ...entry }))
  const entryA = entries.find((e) => e.weapon_id === weaponAId)
  const entryB = entries.find((e) => e.weapon_id === weaponBId)

  const weaponA = weaponsMap.value.get(weaponAId)
  const weaponB = weaponsMap.value.get(weaponBId)

  const hasA = !!entryA
  const hasB = !!entryB

  if (!hasA && !hasB) return

  const priorityA = getEffectivePriorityForSwap(weaponAId, entryA)
  const priorityB = getEffectivePriorityForSwap(weaponBId, entryB)

  if (hasA && !hasB) {
    // A有基质、B无基质 → A移除、B添加A的数据
    const nextEntries = entries
      .filter((entry) => entry.weapon_id !== weaponAId)
      .concat({
        ...entryA!,
        weapon_id: weaponBId,
        weapon_name: weaponB?.name || weaponBId,
        priority: priorityA,
      })
    await updateTreasureMatrix(nextEntries)
    await updateWeaponPriority(weaponAId, priorityB)
    await updateWeaponPriority(weaponBId, priorityA)
  } else if (!hasA && hasB) {
    // A无基质、B有基质 → A添加B的数据、B移除
    const nextEntries = entries
      .filter((entry) => entry.weapon_id !== weaponBId)
      .concat({
        ...entryB!,
        weapon_id: weaponAId,
        weapon_name: weaponA?.name || weaponAId,
        priority: priorityB,
      })
    await updateTreasureMatrix(nextEntries)
    await updateWeaponPriority(weaponAId, priorityB)
    await updateWeaponPriority(weaponBId, priorityA)
  } else {
    // 两者都有基质，交换等级、计算开关和有效优先级
    const matrixA = {
      affix1: entryA!.affix1_level,
      affix2: entryA!.affix2_level,
      affix3: entryA!.affix3_level,
      includeInCalculation: entryA!.include_in_calculation,
    }
    entryA!.affix1_level = entryB!.affix1_level
    entryA!.affix2_level = entryB!.affix2_level
    entryA!.affix3_level = entryB!.affix3_level
    entryA!.include_in_calculation = entryB!.include_in_calculation
    entryA!.priority = priorityB

    entryB!.affix1_level = matrixA.affix1
    entryB!.affix2_level = matrixA.affix2
    entryB!.affix3_level = matrixA.affix3
    entryB!.include_in_calculation = matrixA.includeInCalculation
    entryB!.priority = priorityA

    await updateTreasureMatrix(entries)
    await updateWeaponPriority(weaponAId, priorityB)
    await updateWeaponPriority(weaponBId, priorityA)
  }

  // 关闭弹窗
  detailDialog.value = false
}
</script>

<style scoped lang="scss">
.group-icon {
  width: 1.5rem;
  height: 1.5rem;
  vertical-align: middle;
}

.weapon-overview-container {
  position: relative;
}

.connection-lines-layer {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 10;
  overflow: visible;
}

.connection-line {
  position: absolute;
  height: 2px;
  background-color: rgb(24, 103, 192);
  transform-origin: 0 50%;
  opacity: 0;
  transition: opacity 0.2s ease;

  &::before {
    content: '';
    position: absolute;
    right: -4px;
    top: -3px;
    width: 8px;
    height: 8px;
    background-color: rgb(24, 103, 192);
    border-radius: 50%;
    box-shadow: 0 0 8px rgb(24, 103, 192);
  }

  &[style*="opacity: 1"] {
    opacity: 1;
  }
}

.weapon-overview-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(3.5rem, 1fr));
  gap: 0.5rem;
}

.weapon-overview-item {
  width: 3.5rem;
  height: 3.5rem;
  cursor: pointer;
  position: relative;

  &:hover .weapon-icon-wrapper {
    transform: scale(1.05);
  }
}

.weapon-icon-wrapper {
  width: 100%;
  height: 100%;
  position: relative;
  transition:
    transform 0.15s,
    opacity 0.15s,
    filter 0.15s;
  border-radius: 6px;

  // 未拥有：灰色滤镜必须作用于上级容器，标记作为兄弟节点避免被叠加影响
  &.weapon-not-owned {
    opacity: 0.4;
    filter: grayscale(0.8);
  }

  // 可切换目标满级：灰色呼吸背景
  &.switch-target-maxed {
    animation: switch-target-breathe 2s ease-in-out infinite;
  }

  // 已满级：彩虹边框动画（优先级最高，必须在 switch-target-maxed 之后定义以覆盖）
  &.weapon-maxed {
    animation: rainbow-glow 3s linear infinite;
  }
}

.weapon-icon-detail {
  width: 3rem !important;
  height: 3rem !important;
}

.weapon-icon-same {
  width: 2rem !important;
  height: 2rem !important;
  flex-shrink: 0;
}

.weapon-icon-overlap {
  width: 2rem !important;
  height: 2rem !important;
  flex-shrink: 0;
}

.overlap-icon-wrapper {
  width: 2rem;
  height: 2rem;
  flex-shrink: 0;
}

.rainbow-border {
  position: absolute;
  inset: -3px;
  border-radius: 8px;
  background: linear-gradient(45deg, #FFF, #ff4ada, #ff4e4e, #ff9832, #ff0, #0f0, #00ffff, #79a0fd, #d46eff, #ff8df0, #FFF);
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
    box-shadow: 0 0 10px rgba(0, 0, 255, 0.8);
  }
  71% {
    box-shadow: 0 0 10px rgba(75, 0, 130, 0.8);
  }
  85% {
    box-shadow: 0 0 10px rgba(148, 0, 211, 0.8);
  }
}

.switchable-badge {
  position: absolute;
  top: -6px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 3;
  pointer-events: none;
  font-size: 0.55rem !important;
  height: 14px !important;
  box-shadow: 0 1px 6px rgba(0, 0, 0, 0.35);
}

@keyframes switch-target-breathe {
  0%,
  100% {
    box-shadow: 0 0 8px 2px rgba(128, 128, 128, 0.3);
  }
  50% {
    box-shadow: 0 0 14px 5px rgba(158, 158, 158, 0.85);
  }
}
</style>
