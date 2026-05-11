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
        左键点击武器图标查看基质属性，右键点击切换是否拥有该武器的基质。已满级（6/6/3）的武器会显示彩虹边框。
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
        </v-chip-group>
      </div>

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
            @click="showWeaponDetail(weaponId)"
            @contextmenu.prevent="toggleWeaponOwnership(weaponId)"
          >
            <div
              class="weapon-icon-wrapper"
              :class="{
                'weapon-not-owned': !isWeaponOwned(weaponId),
                'weapon-maxed': isWeaponMaxed(weaponId),
                'switch-target-maxed': isSwitchable(weaponId) && isSwitchTargetMaxed(weaponId),
              }"
            >
              <item-icon :item-id="weaponId" show-item-name />

              <!-- 满级的彩虹边框 -->
              <div v-if="isWeaponMaxed(weaponId)" class="rainbow-border" />
            </div>

            <!-- 可切换标记放在灰色滤镜容器外，避免被 opacity/filter 叠加 -->
            <v-chip
              v-if="isSwitchable(weaponId)"
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
    </v-expansion-panel-text>
  </v-expansion-panel>

  <!-- 武器详情弹窗 -->
  <v-dialog v-model="detailDialog" max-width="600">
    <v-card v-if="detailWeaponId">
      <v-card-item>
        <template #prepend>
          <item-icon class="weapon-icon-detail" :item-id="detailWeaponId" />
        </template>
        <v-card-title>{{ weaponsMap.get(detailWeaponId)?.name || detailWeaponId }}</v-card-title>
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

        <!-- 同类武器 -->
        <div v-if="getSameStatWeapons(detailWeaponId).length > 0">
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
        <div v-else class="text-medium-emphasis text-caption">
          没有其他武器与此武器共享相同属性组合。
        </div>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<script lang="ts" setup>
import { computed, ref } from 'vue'
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
    const weapon = weaponsMap.value.get(weaponId)
    await addTreasureMatrixEntry({
      weapon_id: weaponId,
      weapon_name: weapon?.name || weaponId,
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
 */
function getWeaponStatsText(weaponId: string): string {
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
 */
function getSameStatWeapons(weaponId: string): string[] {
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
 */
function getWeaponPriority(weaponId: string): number {
  const userP = getUserPriority(weaponId)
  if (userP > 0) return userP
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

  // 已满级：彩虹边框动画
  &.weapon-maxed {
    animation: rainbow-glow 3s linear infinite;
  }

  // 可切换目标满级：灰色呼吸背景
  &.switch-target-maxed {
    animation: switch-target-breathe 2s ease-in-out infinite;
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

.rainbow-border {
  position: absolute;
  inset: -3px;
  border-radius: 8px;
  background: linear-gradient(
    45deg,
    #ff0000,
    #ff7f00,
    #ffff00,
    #00ff00,
    #0000ff,
    #4b0082,
    #9400d3
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
