<template>
  <v-container class="treasure-matrix-page">
    <v-expansion-panels v-model="openedPanels" multiple>
      <!-- 武器总览 -->
      <weapon-overview />

      <!-- Treasure Matrix Config -->
      <v-expansion-panel :value="1">
        <v-expansion-panel-title>
          <v-icon class="mr-2">mdi-diamond-stone</v-icon>
          宝藏基质配置
          <v-chip class="ml-2" color="primary" size="small" variant="flat">
            {{ activeProfileName }}
          </v-chip>
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          <v-alert border="start" class="mb-4" type="info" variant="tonal">
            保存你当前账号下每把武器的宝藏基质词条等级，用于计算建议刷取次数。点击武器卡片可切换是否参与计算。
          </v-alert>

          <!-- 星级过滤开关 -->
          <div class="d-flex align-center gap-2 mb-3">
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

          <!-- 显示满级武器开关 -->
          <div class="d-flex align-center mb-3">
            <v-switch
              v-model="showMaxedWeapons"
              color="primary"
              density="compact"
              hide-details
              label="显示满级武器（6/6/3）"
            />
          </div>

          <!-- Existing entries -->
          <v-card
            v-for="(entry, index) in filteredMatrixEntries"
            :key="entry.weapon_id"
            class="mb-3 entry-card"
            :class="{ 'entry-card--selected': entry.include_in_calculation !== false }"
            variant="outlined"
          >
            <v-card-text class="clickable-card" @click="toggleIncludeInCalculation(entry)">
              <v-row align="center">
                <v-col cols="12" md="3">
                  <div class="d-flex align-center">
                    <item-icon class="me-2 weapon-icon-small" :item-id="entry.weapon_id" />
                    <div>
                      <div class="font-weight-bold">{{ entry.weapon_name || entry.weapon_id }}</div>
                      <div class="text-caption text-medium-emphasis">
                        {{ getWeaponStats(entry.weapon_id) }}
                      </div>
                    </div>
                  </div>
                </v-col>
                <v-col cols="6" md="2">
                  <v-select
                    v-model="entry.affix1_level"
                    density="compact"
                    hide-details
                    :items="[1, 2, 3, 4, 5, 6]"
                    label="基础属性"
                    variant="outlined"
                    @click.stop
                    @update:model-value="onEntryChange"
                  >
                    <template #selection="{ item }">
                      <v-chip color="primary" size="x-small" variant="flat">+{{ item.title }}</v-chip>
                    </template>
                    <template #item="{ item, props }">
                      <v-list-item v-bind="props">
                        <template #title>+{{ item.title }}</template>
                      </v-list-item>
                    </template>
                  </v-select>
                </v-col>
                <v-col cols="6" md="2">
                  <v-select
                    v-model="entry.affix2_level"
                    density="compact"
                    hide-details
                    :items="[1, 2, 3, 4, 5, 6]"
                    label="附加属性"
                    variant="outlined"
                    @click.stop
                    @update:model-value="onEntryChange"
                  >
                    <template #selection="{ item }">
                      <v-chip color="teal" size="x-small" variant="flat">+{{ item.title }}</v-chip>
                    </template>
                    <template #item="{ item, props }">
                      <v-list-item v-bind="props">
                        <template #title>+{{ item.title }}</template>
                      </v-list-item>
                    </template>
                  </v-select>
                </v-col>
                <v-col cols="6" md="2">
                  <v-select
                    v-model="entry.affix3_level"
                    density="compact"
                    hide-details
                    :items="[1, 2, 3]"
                    label="技能属性"
                    variant="outlined"
                    @click.stop
                    @update:model-value="onEntryChange"
                  >
                    <template #selection="{ item }">
                      <v-chip color="blue" size="x-small" variant="flat">+{{ item.title }}</v-chip>
                    </template>
                    <template #item="{ item, props }">
                      <v-list-item v-bind="props">
                        <template #title>+{{ item.title }}</template>
                      </v-list-item>
                    </template>
                  </v-select>
                </v-col>
                <v-col cols="12" md="3">
                  <div class="d-flex ga-2 justify-end">
                    <v-tooltip text="计算此武器的刷取建议">
                      <template #activator="{ props }">
                        <v-btn
                          v-bind="props"
                          color="primary"
                          icon="mdi-calculator"
                          size="default"
                          variant="tonal"
                          @click.stop="computeSingle(entry)"
                        />
                      </template>
                    </v-tooltip>
                    <v-tooltip text="移除此武器">
                      <template #activator="{ props }">
                        <v-btn
                          v-bind="props"
                          color="error"
                          icon="mdi-delete"
                          size="default"
                          variant="tonal"
                          @click.stop="removeEntry(index)"
                        />
                      </template>
                    </v-tooltip>
                  </div>
                </v-col>
              </v-row>
            </v-card-text>
          </v-card>

          <div v-if="filteredMatrixEntries.length === 0" class="text-center py-6">
            <v-icon class="mb-2" color="medium-emphasis" size="48">mdi-diamond-outline</v-icon>
            <div class="text-medium-emphasis">尚未添加任何武器，点击下方按钮开始配置</div>
          </div>

          <v-btn
            class="mt-2"
            color="primary"
            prepend-icon="mdi-plus"
            variant="flat"
            @click="showAddWeaponDialog = true"
          >
            添加武器
          </v-btn>
        </v-expansion-panel-text>
      </v-expansion-panel>

      <!-- Farming Recommendations -->
      <v-expansion-panel :value="2">
        <v-expansion-panel-title>
          <v-icon class="mr-2">mdi-calculator</v-icon>
          刷取建议
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          <v-row align="center" class="mb-4">
            <v-col cols="12" md="4">
              <v-select
                v-model="targetAffix1"
                density="compact"
                hide-details
                :items="[1, 2, 3, 4, 5, 6]"
                label="目标基础属性"
                variant="outlined"
              >
                <template #selection="{ item }">+{{ item.title }}</template>
                <template #item="{ item, props }">
                  <v-list-item v-bind="props">
                    <template #title>+{{ item.title }}</template>
                  </v-list-item>
                </template>
              </v-select>
            </v-col>
            <v-col cols="12" md="4">
              <v-select
                v-model="targetAffix2"
                density="compact"
                hide-details
                :items="[1, 2, 3, 4, 5, 6]"
                label="目标附加属性"
                variant="outlined"
              >
                <template #selection="{ item }">+{{ item.title }}</template>
                <template #item="{ item, props }">
                  <v-list-item v-bind="props">
                    <template #title>+{{ item.title }}</template>
                  </v-list-item>
                </template>
              </v-select>
            </v-col>
            <v-col cols="12" md="4">
              <v-select
                v-model="targetAffix3"
                density="compact"
                hide-details
                :items="[1, 2, 3]"
                label="目标技能属性"
                variant="outlined"
              >
                <template #selection="{ item }">+{{ item.title }}</template>
                <template #item="{ item, props }">
                  <v-list-item v-bind="props">
                    <template #title>+{{ item.title }}</template>
                  </v-list-item>
                </template>
              </v-select>
            </v-col>
          </v-row>

          <v-btn
            class="mb-4"
            color="primary"
            :loading="computing"
            prepend-icon="mdi-calculator"
            variant="flat"
            @click="computeAll"
          >
            计算所有武器的刷取建议
          </v-btn>

          <v-btn
            v-if="recommendations.length > 0"
            class="mb-4 ml-2"
            color="success"
            prepend-icon="mdi-map-search"
            variant="flat"
            @click="navigateToPlanner()"
          >
            查看最优刷取方案
          </v-btn>

          <v-alert v-if="recommendations.length === 0" border="start" type="info" variant="tonal">
            请先添加武器到宝藏基质配置，然后点击「计算所有武器的刷取建议」。
          </v-alert>

          <v-card
            v-for="rec in sortedRecommendations"
            :key="rec.weapon_id"
            class="mb-4 rec-card"
            variant="outlined"
          >
            <v-card-item>
              <template #prepend>
                <item-icon class="weapon-icon-small" :item-id="rec.weapon_id" />
              </template>
              <v-card-title>{{ rec.weapon_name }}</v-card-title>
              <v-card-subtitle>
                当前: +{{ rec.current_levels[0] }} / +{{ rec.current_levels[1] }} / +{{ rec.current_levels[2] }}
                → 目标: +{{ rec.target_levels[0] }} / +{{ rec.target_levels[1] }} / +{{ rec.target_levels[2] }}
              </v-card-subtitle>
              <template #append>
                <v-chip color="warning" size="large" variant="flat">
                  <v-icon start>mdi-sword</v-icon>
                  约 {{ Math.ceil(getAdjustedStats(rec).totalRuns) }} 次刷取
                </v-chip>
              </template>
            </v-card-item>
            <v-divider />
            <v-card-text>
              <v-row>
                <v-col cols="12" md="4">
                  <v-list density="compact">
                    <v-list-subheader>
                      <v-icon class="mr-1" color="primary" size="small">mdi-circle</v-icon>
                      基础属性 +{{ rec.current_levels[0] }} → +{{ rec.target_levels[0] }}
                    </v-list-subheader>
                    <v-list-item
                      v-for="step in rec.affix_results[0]?.steps"
                      :key="'a1-' + step.from_level"
                      :class="{ 'bg-success-lighten-5': isUsingGrease(rec.weapon_id, 0, step.from_level) }"
                      density="compact"
                      style="cursor: pointer"
                      @click="toggleUseGrease(rec.weapon_id, 0, step.from_level)"
                    >
                      <v-list-item-title>
                        +{{ step.from_level }} → +{{ step.to_level }}
                      </v-list-item-title>
                      <template #append>
                        <v-chip
                          :color="isUsingGrease(rec.weapon_id, 0, step.from_level) ? 'success' : undefined"
                          size="x-small"
                          :variant="isUsingGrease(rec.weapon_id, 0, step.from_level) ? 'flat' : 'tonal'"
                        >
                          {{ isUsingGrease(rec.weapon_id, 0, step.from_level) ? '100%' : (step.success_prob * 100).toFixed(1) + '%' }}
                        </v-chip>
                        <span class="text-caption ml-2">
                          {{ isUsingGrease(rec.weapon_id, 0, step.from_level) ? `冷却脂 ${step.grease_threshold}` : `期望 ${step.expected_attempts.toFixed(1)} 次` }}
                        </span>
                      </template>
                    </v-list-item>
                    <v-list-item v-if="rec.affix_results[0]?.steps.length === 0" density="compact">
                      <v-list-item-title class="text-medium-emphasis">
                        <v-icon class="mr-1" color="success" size="small">mdi-check</v-icon>
                        已达标
                      </v-list-item-title>
                    </v-list-item>
                  </v-list>
                </v-col>
                <v-col cols="12" md="4">
                  <v-list density="compact">
                    <v-list-subheader>
                      <v-icon class="mr-1" color="teal" size="small">mdi-circle</v-icon>
                      附加属性 +{{ rec.current_levels[1] }} → +{{ rec.target_levels[1] }}
                    </v-list-subheader>
                    <v-list-item
                      v-for="step in rec.affix_results[1]?.steps"
                      :key="'a2-' + step.from_level"
                      :class="{ 'bg-success-lighten-5': isUsingGrease(rec.weapon_id, 1, step.from_level) }"
                      density="compact"
                      style="cursor: pointer"
                      @click="toggleUseGrease(rec.weapon_id, 1, step.from_level)"
                    >
                      <v-list-item-title>
                        +{{ step.from_level }} → +{{ step.to_level }}
                      </v-list-item-title>
                      <template #append>
                        <v-chip
                          :color="isUsingGrease(rec.weapon_id, 1, step.from_level) ? 'success' : undefined"
                          size="x-small"
                          :variant="isUsingGrease(rec.weapon_id, 1, step.from_level) ? 'flat' : 'tonal'"
                        >
                          {{ isUsingGrease(rec.weapon_id, 1, step.from_level) ? '100%' : (step.success_prob * 100).toFixed(1) + '%' }}
                        </v-chip>
                        <span class="text-caption ml-2">
                          {{ isUsingGrease(rec.weapon_id, 1, step.from_level) ? `冷却脂 ${step.grease_threshold}` : `期望 ${step.expected_attempts.toFixed(1)} 次` }}
                        </span>
                      </template>
                    </v-list-item>
                    <v-list-item v-if="rec.affix_results[1]?.steps.length === 0" density="compact">
                      <v-list-item-title class="text-medium-emphasis">
                        <v-icon class="mr-1" color="success" size="small">mdi-check</v-icon>
                        已达标
                      </v-list-item-title>
                    </v-list-item>
                  </v-list>
                </v-col>
                <v-col cols="12" md="4">
                  <v-list density="compact">
                    <v-list-subheader>
                      <v-icon class="mr-1" color="blue" size="small">mdi-circle</v-icon>
                      技能属性 +{{ rec.current_levels[2] }} → +{{ rec.target_levels[2] }}
                    </v-list-subheader>
                    <v-list-item
                      v-for="step in rec.affix_results[2]?.steps"
                      :key="'a3-' + step.from_level"
                      :class="{ 'bg-success-lighten-5': isUsingGrease(rec.weapon_id, 2, step.from_level) }"
                      density="compact"
                      style="cursor: pointer"
                      @click="toggleUseGrease(rec.weapon_id, 2, step.from_level)"
                    >
                      <v-list-item-title>
                        +{{ step.from_level }} → +{{ step.to_level }}
                      </v-list-item-title>
                      <template #append>
                        <v-chip
                          :color="isUsingGrease(rec.weapon_id, 2, step.from_level) ? 'success' : undefined"
                          size="x-small"
                          :variant="isUsingGrease(rec.weapon_id, 2, step.from_level) ? 'flat' : 'tonal'"
                        >
                          {{ isUsingGrease(rec.weapon_id, 2, step.from_level) ? '100%' : (step.success_prob * 100).toFixed(1) + '%' }}
                        </v-chip>
                        <span class="text-caption ml-2">
                          {{ isUsingGrease(rec.weapon_id, 2, step.from_level) ? `冷却脂 ${step.grease_threshold}` : `期望 ${step.expected_attempts.toFixed(1)} 次` }}
                        </span>
                      </template>
                    </v-list-item>
                    <v-list-item v-if="rec.affix_results[2]?.steps.length === 0" density="compact">
                      <v-list-item-title class="text-medium-emphasis">
                        <v-icon class="mr-1" color="success" size="small">mdi-check</v-icon>
                        已达标
                      </v-list-item-title>
                    </v-list-item>
                  </v-list>
                </v-col>
              </v-row>
              <v-divider class="my-2" />
              <div class="d-flex flex-wrap align-center justify-space-between ga-2">
                <div class="d-flex flex-wrap ga-4 text-caption">
                  <div class="d-flex align-center">
                    <v-icon class="mr-1" color="primary" size="small">mdi-diamond-stone</v-icon>
                    <strong>期望消耗无暇基质:</strong>&nbsp;{{ getAdjustedStats(rec).totalEssences }} 个
                  </div>
                  <div class="d-flex align-center">
                    <v-icon class="mr-1" color="success" size="small">mdi-arrow-up-bold</v-icon>
                    <strong>期望获得冷却脂:</strong>&nbsp;
                    {{ getAdjustedStats(rec).totalGreaseGained }} 点
                  </div>
                  <div class="d-flex align-center">
                    <v-icon class="mr-1" color="warning" size="small">mdi-arrow-down-bold</v-icon>
                    <strong>消耗冷却脂:</strong>&nbsp;
                    {{ getAdjustedStats(rec).totalGreaseUsed }} 点
                  </div>
                </div>
                <v-btn
                  color="primary"
                  prepend-icon="mdi-map-search"
                  size="small"
                  variant="tonal"
                  @click="navigateToPlanner()"
                >
                  查看最优刷取方案
                </v-btn>
              </div>
            </v-card-text>
          </v-card>
        </v-expansion-panel-text>
      </v-expansion-panel>
    </v-expansion-panels>

    <!-- Add Weapon Dialog -->
    <v-dialog v-model="showAddWeaponDialog" max-width="800">
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon class="mr-2">mdi-sword</v-icon>
          选择武器
        </v-card-title>
        <v-card-text>
          <v-text-field
            v-model="weaponSearch"
            class="mb-4"
            clearable
            density="compact"
            hide-details
            label="搜索武器名称..."
            prepend-inner-icon="mdi-magnify"
            variant="outlined"
          />
          <template v-for="wType in weaponTypes" :key="wType.id">
            <h4 class="mt-4 mb-2 d-flex align-center">
              <img
                :alt="wType.name"
                class="group-icon me-2"
                :src="wType.iconUrl"
              />
              {{ wType.name }}
            </h4>
            <div class="weapon-grid">
              <div
                v-for="weaponId in filteredWeaponIds(wType.weaponIds)"
                :key="weaponId"
                class="weapon-item"
                @click="onAddWeapon(weaponId)"
              >
                <item-icon :item-id="weaponId" show-item-name />
              </div>
            </div>
          </template>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="showAddWeaponDialog = false">关闭</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- 回到顶部按钮 -->
    <back-to-top />
  </v-container>
</template>

<script lang="ts" setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import BackToTop from '@/components/BackToTop.vue'
import ItemIcon from '@/components/ItemIcon.vue'
import WeaponOverview from '@/components/WeaponOverview.vue'
import { type TreasureMatrixEntry, useProfiles } from '@/composables/useProfiles'
import { useRarityFilters } from '@/composables/useRarityFilters'
import { useStaticData } from '@/utils/gameData/staticData'
import { getGemTagName, getStatsForWeapon } from '@/utils/gameData/weapon'

const router = useRouter()

const {
  activeProfileName,
  treasureMatrix,
  fetchProfiles,
  updateTreasureMatrix,
  addTreasureMatrixEntry,
  removeTreasureMatrixEntry,
  getBatchFarmingRecommendations,
} = useProfiles()
const { selectedRarities } = useRarityFilters()

const { weaponsMap, weaponTypes } = useStaticData()

// 控制面板展开状态
const openedPanels = ref<number[]>([0, 1, 2])

const showAddWeaponDialog = ref(false)
const weaponSearch = ref('')
const computing = ref(false)

const targetAffix1 = ref(6)
const targetAffix2 = ref(6)
const targetAffix3 = ref(3)

interface Recommendation {
  weapon_id: string
  weapon_name: string
  current_levels: [number, number, number]
  target_levels: [number, number, number]
  total_expected_runs: number
  total_expected_essences: number
  affix_results: Array<{
    affix_name: string
    current_level: number
    target_level: number
    expected_attempts: number
    expected_essences_consumed: number
    expected_grease_gained: number
    expected_grease_used: number
    steps: Array<{
      from_level: number
      to_level: number
      success_prob: number
      grease_threshold: number
      expected_attempts: number
      expected_essences: number
      expected_grease_gained: number
      expected_grease_used: number
    }>
  }>
}

// 从 localStorage 加载保存的推荐结果
const savedRecommendations = localStorage.getItem('treasureMatrixRecommendations')
const recommendations = ref<Recommendation[]>(
  savedRecommendations ? JSON.parse(savedRecommendations) : []
)

// 监听 recommendations 变化，保存到 localStorage
watch(
  recommendations,
  (newValue) => {
    if (newValue.length > 0) {
      localStorage.setItem('treasureMatrixRecommendations', JSON.stringify(newValue))
    }
  },
  { deep: true }
)

// 跟踪每个武器的每个步骤是否使用冷却脂
// 格式: { weaponId: { 'affixIndex-fromLevel': boolean } }
const useGreaseForSteps = ref<Record<string, Record<string, boolean>>>({})

// 排序后的推荐列表：初始排序后保持稳定，用户切换冷却脂时不重新排序
// 从 localStorage 加载保存的排序顺序
const savedFrozenOrder = localStorage.getItem('treasureMatrixFrozenOrder')
const frozenSortOrder = ref<string[] | null>(
  savedFrozenOrder ? JSON.parse(savedFrozenOrder) : null
)

// 保存冻结的排序顺序到 localStorage
watch(
  frozenSortOrder,
  (newValue) => {
    if (newValue) {
      localStorage.setItem('treasureMatrixFrozenOrder', JSON.stringify(newValue))
    }
  },
  { deep: true }
)

// 监听 recommendations 变化，更新冻结顺序
watch(recommendations, (newRecommendations: Recommendation[]) => {
  const sorted = newRecommendations.toSorted((a: Recommendation, b: Recommendation) => {
    const aRuns = Math.ceil(a.total_expected_runs)
    const bRuns = Math.ceil(b.total_expected_runs)

    // 本身不需要刷取的武器置底
    if (aRuns === 0 && bRuns !== 0) return 1
    if (aRuns !== 0 && bRuns === 0) return -1

    // 按原始刷取次数升序排序
    return aRuns - bRuns
  })

  const currentIds = sorted.map((rec: Recommendation) => rec.weapon_id).join(',')

  // 如果还没有冻结顺序，或者是全新的推荐列表，则冻结
  if (frozenSortOrder.value === null || frozenSortOrder.value.join(',') !== currentIds) {
    frozenSortOrder.value = sorted.map((rec: Recommendation) => rec.weapon_id)
  }
}, { deep: true })

const sortedRecommendations = computed(() => {
  if (!frozenSortOrder.value) {
    return recommendations.value
  }

  // 使用冻结的顺序
  const orderMap = new Map(frozenSortOrder.value.map((id, idx) => [id, idx]))
  return [...recommendations.value].toSorted((a, b) => {
    return (orderMap.get(a.weapon_id) ?? 0) - (orderMap.get(b.weapon_id) ?? 0)
  })
})

const showMaxedWeapons = ref(false)

const matrixEntries = computed({
  get: () => treasureMatrix.value,
  set: (val) => {
    updateTreasureMatrix(val)
  },
})

const filteredMatrixEntries = computed(() => {
  let entries = matrixEntries.value

  // 过滤稀有度
  entries = entries.filter((entry) => {
    const weapon = weaponsMap.value.get(entry.weapon_id)
    if (!weapon) return false
    return selectedRarities.value.includes(String(weapon.rarity))
  })

  // 过滤满级武器
  if (!showMaxedWeapons.value) {
    entries = entries.filter(
      (entry) =>
        !(entry.affix1_level === 6 && entry.affix2_level === 6 && entry.affix3_level === 3),
    )
  }

  // 按稀有度降序排序（6★ -> 3★）
  return entries.toSorted((a, b) => {
    const wa = weaponsMap.value.get(a.weapon_id)
    const wb = weaponsMap.value.get(b.weapon_id)
    if (wa && wb) return wb.rarity - wa.rarity
    return 0
  })
})

function getWeaponStats(weaponId: string): string {
  const stats = getStatsForWeapon(weaponId)
  const parts: string[] = []
  if (stats.attribute) parts.push(getGemTagName(stats.attribute))
  if (stats.secondary) parts.push(getGemTagName(stats.secondary))
  if (stats.skill) parts.push(getGemTagName(stats.skill))
  return parts.join('、') || '无属性'
}

function filteredWeaponIds(weaponIds: string[]): string[] {
  if (!weaponSearch.value.trim()) return weaponIds
  const search = weaponSearch.value.trim().toLowerCase()
  return weaponIds.filter((id) => {
    const weapon = weaponsMap.value.get(id)
    return weapon && weapon.name.toLowerCase().includes(search)
  })
}

async function onAddWeapon(weaponId: string) {
  const weapon = weaponsMap.value.get(weaponId)
  if (!weapon) return

  // Check if already exists
  const existing = matrixEntries.value.find((e) => e.weapon_id === weaponId)
  if (existing) {
    showAddWeaponDialog.value = false
    return
  }

  await addTreasureMatrixEntry({
    weapon_id: weaponId,
    weapon_name: weapon.name,
    affix1_level: 1,
    affix2_level: 1,
    affix3_level: 1,
    include_in_calculation: true,
  })
  showAddWeaponDialog.value = false
}

async function removeEntry(index: number) {
  const entry = filteredMatrixEntries.value[index]
  if (entry) {
    await removeTreasureMatrixEntry(entry.weapon_id)
  }
}

function toggleUseGrease(weaponId: string, affixIndex: number, fromLevel: number) {
  const key = `${affixIndex}-${fromLevel}`
  if (!useGreaseForSteps.value[weaponId]) {
    useGreaseForSteps.value[weaponId] = {}
  }
  useGreaseForSteps.value[weaponId][key] = !useGreaseForSteps.value[weaponId][key]
}

function isUsingGrease(weaponId: string, affixIndex: number, fromLevel: number): boolean {
  return useGreaseForSteps.value[weaponId]?.[`${affixIndex}-${fromLevel}`] || false
}

function getAdjustedStats(rec: Recommendation) {
  let totalEssences = 0
  let totalGreaseGained = 0
  let totalGreaseUsed = 0

  for (const [affixIndex, affixResult] of rec.affix_results.entries()) {
    for (const step of affixResult.steps) {
      const usingGrease = isUsingGrease(rec.weapon_id, affixIndex, step.from_level)
      if (usingGrease) {
        // 使用冷却脂：不消耗基质，不获得冷却脂，但要消耗固定冷却脂
        totalGreaseUsed += step.grease_threshold
      } else {
        // 不使用冷却脂：正常计算
        // 每个步骤的基质消耗向上取整
        totalEssences += Math.ceil(step.expected_essences)
        // 冷却脂获得取最接近的10的倍数
        totalGreaseGained += Math.round(step.expected_grease_gained / 10) * 10
        // 冷却脂消耗（正常升级时为0）
        totalGreaseUsed += Math.round(step.expected_grease_used / 10) * 10
      }
    }
  }

  // 计算刷取次数：每次刷取掉落 3 个无暇基质
  const ESSENCES_PER_RUN = 3
  const totalRuns = totalEssences / ESSENCES_PER_RUN

  return {
    totalEssences,
    totalGreaseGained,
    totalGreaseUsed,
    totalRuns,
  }
}

function toggleIncludeInCalculation(entry: TreasureMatrixEntry) {
  entry.include_in_calculation = !entry.include_in_calculation
  updateTreasureMatrix(matrixEntries.value)
}

let debounceTimer: ReturnType<typeof setTimeout> | null = null

function onEntryChange() {
  // 检查是否有武器达到满级（6/6/3），自动取消勾选
  for (const entry of matrixEntries.value) {
    if (
      entry.affix1_level === 6 &&
      entry.affix2_level === 6 &&
      entry.affix3_level === 3 &&
      entry.include_in_calculation !== false
    ) {
      entry.include_in_calculation = false
    }
  }

  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    updateTreasureMatrix([...matrixEntries.value])
  }, 500)
}

async function computeSingle(entry: TreasureMatrixEntry) {
  computing.value = true
  try {
    const results = await getBatchFarmingRecommendations([
      {
        weapon_id: entry.weapon_id,
        current_levels: [entry.affix1_level, entry.affix2_level, entry.affix3_level],
        target_levels: [targetAffix1.value, targetAffix2.value, targetAffix3.value],
      },
    ])
    if (results.length > 0) {
      frozenSortOrder.value = null
      recommendations.value = results

      // 计算完成后，折叠武器总览（value=0）和宝藏基质配置面板（value=1）
      // 只保留刷取建议（value=2）展开
      openedPanels.value = [2]
    }
  } finally {
    computing.value = false
  }
}

async function computeAll() {
  if (matrixEntries.value.length === 0) return
  computing.value = true
  try {
    // 只计算勾选了"参与计算"的武器，并且在选中的稀有度范围内
    const items = matrixEntries.value
      .filter((entry) => {
        // 必须勾选了"参与计算"
        if (entry.include_in_calculation === false) return false

        // 必须在选中的稀有度范围内
        const weapon = weaponsMap.value.get(entry.weapon_id)
        if (!weapon) return false
        return selectedRarities.value.includes(String(weapon.rarity))
      })
      .map((entry) => ({
        weapon_id: entry.weapon_id,
        current_levels: [entry.affix1_level, entry.affix2_level, entry.affix3_level] as [
          number,
          number,
          number,
        ],
        target_levels: [targetAffix1.value, targetAffix2.value, targetAffix3.value] as [
          number,
          number,
          number,
        ],
      }))
    const results = await getBatchFarmingRecommendations(items)
    // Sort by expected runs (ascending - least runs first)
    results.sort(
      (a: Recommendation, b: Recommendation) => a.total_expected_runs - b.total_expected_runs,
    )
    frozenSortOrder.value = null
    recommendations.value = results

    // 计算完成后，折叠武器总览（value=0）和宝藏基质配置面板（value=1）
    // 只保留刷取建议（value=2）展开
    openedPanels.value = [2]
  } finally {
    computing.value = false
  }
}

/**
 * 跳转到基质规划页面，开启不使用预刻券模式。
 * 不传递特定武器，让用户根据未获得数量排序后的方案自行选择。
 */
function navigateToPlanner() {
  router.push({
    name: 'matrix-planner',
    query: { clear: 'true', noPrecraft: 'true' },
  })
  // 滚动到页面顶部
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

onMounted(() => {
  fetchProfiles()

  // 如果有保存的推荐结果，自动折叠武器总览和宝藏基质配置面板
  if (recommendations.value.length > 0) {
    openedPanels.value = [2]
  }
})
</script>

<style scoped lang="scss">
$weapon-icon-size: clamp(2.5rem, 14vw, 5rem);

.treasure-matrix-page {
  .entry-card {
    position: relative;
    transition: transform 0.15s ease, box-shadow 0.15s ease;
    overflow: hidden;

    &:hover {
      transform: translateY(-1px);
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08) !important;
    }

    // 选中状态的左侧淡蓝色渐变
    &.entry-card--selected::before {
      content: '';
      position: absolute;
      left: 0;
      top: 0;
      bottom: 0;
      width: 10px;
      background: linear-gradient(
        to right,
        rgba(33, 150, 243, 0.8),
        rgba(33, 150, 243, 0.4),
        transparent
      );
      z-index: 1;
    }

    .clickable-card {
      cursor: pointer;
      user-select: none;
    }
  }

  .rec-card {
    transition: transform 0.2s ease, box-shadow 0.2s ease;
    &:hover {
      transform: translateY(-2px);
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1) !important;
    }
  }
}

.group-icon {
  width: 1.5rem;
  height: 1.5rem;
  vertical-align: middle;
}

.weapon-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, $weapon-icon-size);
  gap: calc($weapon-icon-size / 10);
}

.weapon-item {
  width: $weapon-icon-size;
  height: $weapon-icon-size;
  cursor: pointer;
  transition: transform 0.15s;
  border-radius: 6px;
  &:hover {
    transform: scale(1.1);
  }
}

.weapon-icon-small {
  width: 2.5rem !important;
  height: 2.5rem !important;
  display: inline-block;
  flex-shrink: 0;
}
</style>
