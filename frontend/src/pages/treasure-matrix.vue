<template>
  <v-container>
    <v-expansion-panels :model-value="[0, 1]" multiple>
      <!-- Treasure Matrix Config -->
      <v-expansion-panel :value="0">
        <v-expansion-panel-title>
          <v-icon class="mr-2">mdi-diamond-stone</v-icon>
          宝藏基质配置
          <v-chip class="ml-2" color="primary" size="small">
            {{ activeProfileName }}
          </v-chip>
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          <v-alert border="start" class="mb-4" type="info" variant="tonal">
            保存你当前账号下每把武器的宝藏基质词条等级，用于计算建议刷取次数。
          </v-alert>

          <!-- Existing entries -->
          <v-card
            v-for="(entry, index) in matrixEntries"
            :key="entry.weapon_id"
            class="mb-3"
            variant="outlined"
          >
            <v-card-text>
              <v-row align="center">
                <v-col cols="12" md="3">
                  <div class="d-flex align-center">
                    <item-icon class="me-2" :item-id="entry.weapon_id" />
                    <div>
                      <div class="font-weight-bold">{{ entry.weapon_name || entry.weapon_id }}</div>
                      <div class="text-caption text-medium-emphasis">
                        {{ getWeaponStats(entry.weapon_id) }}
                      </div>
                    </div>
                  </div>
                </v-col>
                <v-col cols="12" md="2">
                  <v-select
                    v-model="entry.affix1_level"
                    density="compact"
                    hide-details
                    :items="[1, 2, 3, 4, 5, 6]"
                    label="基础属性"
                    variant="outlined"
                    @update:model-value="onEntryChange"
                  >
                    <template #selection="{ item }">+{{ item }}</template>
                    <template #item="{ item, props }">
                      <v-list-item v-bind="props">
                        <template #title>+{{ item }}</template>
                      </v-list-item>
                    </template>
                  </v-select>
                </v-col>
                <v-col cols="12" md="2">
                  <v-select
                    v-model="entry.affix2_level"
                    density="compact"
                    hide-details
                    :items="[1, 2, 3, 4, 5, 6]"
                    label="附加属性"
                    variant="outlined"
                    @update:model-value="onEntryChange"
                  >
                    <template #selection="{ item }">+{{ item }}</template>
                    <template #item="{ item, props }">
                      <v-list-item v-bind="props">
                        <template #title>+{{ item }}</template>
                      </v-list-item>
                    </template>
                  </v-select>
                </v-col>
                <v-col cols="12" md="2">
                  <v-select
                    v-model="entry.affix3_level"
                    density="compact"
                    hide-details
                    :items="[1, 2, 3]"
                    label="技能属性"
                    variant="outlined"
                    @update:model-value="onEntryChange"
                  >
                    <template #selection="{ item }">+{{ item }}</template>
                    <template #item="{ item, props }">
                      <v-list-item v-bind="props">
                        <template #title>+{{ item }}</template>
                      </v-list-item>
                    </template>
                  </v-select>
                </v-col>
                <v-col cols="12" md="3">
                  <v-btn
                    color="primary"
                    icon="mdi-calculator"
                    size="small"
                    variant="text"
                    @click="computeSingle(entry)"
                  />
                  <v-btn
                    color="error"
                    icon="mdi-delete"
                    size="small"
                    variant="text"
                    @click="removeEntry(index)"
                  />
                </v-col>
              </v-row>
            </v-card-text>
          </v-card>

          <v-btn
            class="mt-2"
            color="primary"
            prepend-icon="mdi-plus"
            @click="showAddWeaponDialog = true"
          >
            添加武器
          </v-btn>
        </v-expansion-panel-text>
      </v-expansion-panel>

      <!-- Farming Recommendations -->
      <v-expansion-panel :value="1">
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
                <template #selection="{ item }">+{{ item }}</template>
                <template #item="{ item, props }">
                  <v-list-item v-bind="props">
                    <template #title>+{{ item }}</template>
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
                <template #selection="{ item }">+{{ item }}</template>
                <template #item="{ item, props }">
                  <v-list-item v-bind="props">
                    <template #title>+{{ item }}</template>
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
                <template #selection="{ item }">+{{ item }}</template>
                <template #item="{ item, props }">
                  <v-list-item v-bind="props">
                    <template #title>+{{ item }}</template>
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
            @click="computeAll"
          >
            计算所有武器的刷取建议
          </v-btn>

          <v-alert v-if="recommendations.length === 0" border="start" type="info" variant="tonal">
            请先添加武器到宝藏基质配置，然后点击「计算所有武器的刷取建议」。
          </v-alert>

          <v-card
            v-for="rec in recommendations"
            :key="rec.weapon_id"
            class="mb-4"
            variant="outlined"
          >
            <v-card-item>
              <template #prepend>
                <item-icon :item-id="rec.weapon_id" />
              </template>
              <v-card-title>{{ rec.weapon_name }}</v-card-title>
              <v-card-subtitle>
                当前: +{{ rec.current_levels[0] }} / +{{ rec.current_levels[1] }} / +{{ rec.current_levels[2] }}
                → 目标: +{{ rec.target_levels[0] }} / +{{ rec.target_levels[1] }} / +{{ rec.target_levels[2] }}
              </v-card-subtitle>
              <template #append>
                <v-chip color="warning" size="large" variant="flat">
                  <v-icon start>mdi-sword</v-icon>
                  约 {{ Math.ceil(rec.total_expected_runs) }} 次刷取
                </v-chip>
              </template>
            </v-card-item>
            <v-divider />
            <v-card-text>
              <v-row>
                <v-col cols="12" md="4">
                  <v-list density="compact">
                    <v-list-subheader>基础属性 +{{ rec.current_levels[0] }} → +{{ rec.target_levels[0] }}</v-list-subheader>
                    <v-list-item
                      v-for="step in rec.affix_results[0]?.steps"
                      :key="'a1-' + step.from_level"
                      density="compact"
                    >
                      <v-list-item-title>
                        +{{ step.from_level }} → +{{ step.to_level }}
                      </v-list-item-title>
                      <template #append>
                        <v-chip size="small" variant="tonal">
                          {{ (step.success_prob * 100).toFixed(1) }}%
                        </v-chip>
                        <span class="text-caption ml-2">
                          期望 {{ step.expected_attempts.toFixed(1) }} 次
                        </span>
                      </template>
                    </v-list-item>
                    <v-list-item v-if="rec.affix_results[0]?.steps.length === 0" density="compact">
                      <v-list-item-title class="text-medium-emphasis">已达标</v-list-item-title>
                    </v-list-item>
                  </v-list>
                </v-col>
                <v-col cols="12" md="4">
                  <v-list density="compact">
                    <v-list-subheader>附加属性 +{{ rec.current_levels[1] }} → +{{ rec.target_levels[1] }}</v-list-subheader>
                    <v-list-item
                      v-for="step in rec.affix_results[1]?.steps"
                      :key="'a2-' + step.from_level"
                      density="compact"
                    >
                      <v-list-item-title>
                        +{{ step.from_level }} → +{{ step.to_level }}
                      </v-list-item-title>
                      <template #append>
                        <v-chip size="small" variant="tonal">
                          {{ (step.success_prob * 100).toFixed(1) }}%
                        </v-chip>
                        <span class="text-caption ml-2">
                          期望 {{ step.expected_attempts.toFixed(1) }} 次
                        </span>
                      </template>
                    </v-list-item>
                    <v-list-item v-if="rec.affix_results[1]?.steps.length === 0" density="compact">
                      <v-list-item-title class="text-medium-emphasis">已达标</v-list-item-title>
                    </v-list-item>
                  </v-list>
                </v-col>
                <v-col cols="12" md="4">
                  <v-list density="compact">
                    <v-list-subheader>技能属性 +{{ rec.current_levels[2] }} → +{{ rec.target_levels[2] }}</v-list-subheader>
                    <v-list-item
                      v-for="step in rec.affix_results[2]?.steps"
                      :key="'a3-' + step.from_level"
                      density="compact"
                    >
                      <v-list-item-title>
                        +{{ step.from_level }} → +{{ step.to_level }}
                      </v-list-item-title>
                      <template #append>
                        <v-chip size="small" variant="tonal">
                          {{ (step.success_prob * 100).toFixed(1) }}%
                        </v-chip>
                        <span class="text-caption ml-2">
                          期望 {{ step.expected_attempts.toFixed(1) }} 次
                        </span>
                      </template>
                    </v-list-item>
                    <v-list-item v-if="rec.affix_results[2]?.steps.length === 0" density="compact">
                      <v-list-item-title class="text-medium-emphasis">已达标</v-list-item-title>
                    </v-list-item>
                  </v-list>
                </v-col>
              </v-row>
              <v-divider class="my-2" />
              <div class="d-flex flex-wrap ga-4 text-caption">
                <div>
                  <strong>期望消耗无暇基质:</strong> {{ rec.total_expected_essences.toFixed(1) }} 个
                </div>
                <div>
                  <strong>期望获得冷却脂:</strong>
                  {{ rec.affix_results.reduce((sum, r) => sum + r.expected_grease_gained, 0).toFixed(0) }} 点
                </div>
                <div>
                  <strong>期望消耗冷却脂:</strong>
                  {{ rec.affix_results.reduce((sum, r) => sum + r.expected_grease_used, 0).toFixed(0) }} 点
                </div>
              </div>
            </v-card-text>
          </v-card>
        </v-expansion-panel-text>
      </v-expansion-panel>
    </v-expansion-panels>

    <!-- Add Weapon Dialog -->
    <v-dialog v-model="showAddWeaponDialog" max-width="800">
      <v-card>
        <v-card-title>选择武器</v-card-title>
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
            <h4 class="mt-4 mb-2">
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
  </v-container>
</template>

<script lang="ts" setup>
import { computed, onMounted, ref } from 'vue'
import ItemIcon from '@/components/ItemIcon.vue'
import { type TreasureMatrixEntry, useProfiles } from '@/composables/useProfiles'
import { useStaticData } from '@/utils/gameData/staticData'
import { getGemTagName, getStatsForWeapon } from '@/utils/gameData/weapon'

const {
  activeProfileName,
  treasureMatrix,
  fetchProfiles,
  updateTreasureMatrix,
  addTreasureMatrixEntry,
  removeTreasureMatrixEntry,
  getBatchFarmingRecommendations,
} = useProfiles()

const { weaponsMap, weaponTypes } = useStaticData()

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

const recommendations = ref<Recommendation[]>([])

const matrixEntries = computed({
  get: () => treasureMatrix.value,
  set: (val) => {
    updateTreasureMatrix(val)
  },
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
  })
  showAddWeaponDialog.value = false
}

async function removeEntry(index: number) {
  const entry = matrixEntries.value[index]
  if (entry) {
    await removeTreasureMatrixEntry(entry.weapon_id)
  }
}

let debounceTimer: ReturnType<typeof setTimeout> | null = null

function onEntryChange() {
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
      recommendations.value = results
    }
  } finally {
    computing.value = false
  }
}

async function computeAll() {
  if (matrixEntries.value.length === 0) return
  computing.value = true
  try {
    const items = matrixEntries.value.map((entry) => ({
      weapon_id: entry.weapon_id,
      current_levels: [entry.affix1_level, entry.affix2_level, entry.affix3_level] as [number, number, number],
      target_levels: [targetAffix1.value, targetAffix2.value, targetAffix3.value] as [number, number, number],
    }))
    const results = await getBatchFarmingRecommendations(items)
    // Sort by expected runs (ascending - least runs first)
    results.sort((a: Recommendation, b: Recommendation) => a.total_expected_runs - b.total_expected_runs)
    recommendations.value = results
  } finally {
    computing.value = false
  }
}

onMounted(() => {
  fetchProfiles()
})
</script>

<style scoped lang="scss">
$weapon-icon-size: clamp(2.5rem, 14vw, 5rem);

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
  &:hover {
    transform: scale(1.1);
  }
}
</style>
