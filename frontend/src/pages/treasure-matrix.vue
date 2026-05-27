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
            :class="{
              'entry-card--muted': entry.include_in_calculation === false,
            }"
            variant="outlined"
          >
            <v-card-text class="clickable-card pa-0" @click="toggleIncludeInCalculation(entry)">
              <div class="matrix-card-body">
                <section class="weapon-identity">
                  <div class="weapon-icon-wrap" :class="getWeaponTierClass(entry.weapon_id)">
                    <custom-stat-icon v-if="isCustomEntry(entry.weapon_id)" hide-name :name="entry.weapon_name || entry.weapon_id" small />
                    <item-icon v-else class="weapon-icon-small" :item-id="entry.weapon_id" />
                    <span class="weapon-tier">{{ getWeaponRarityText(entry.weapon_id) }}</span>
                  </div>
                  <div class="weapon-info">
                    <div class="weapon-name">{{ entry.weapon_name || entry.weapon_id }}</div>
                    <div class="weapon-traits">
                      <span
                        v-for="trait in getWeaponTraitNames(entry.weapon_id)"
                        :key="trait"
                        class="trait"
                      >
                        {{ trait }}
                      </span>
                    </div>
                    <v-chip
                      class="participation-chip"
                      :color="entry.include_in_calculation === false ? 'grey' : 'primary'"
                      size="x-small"
                      variant="tonal"
                    >
                      {{ entry.include_in_calculation === false ? '已排除' : '参与计算' }}
                    </v-chip>
                  </div>
                </section>

                <section class="attribute-section">
                  <div class="attr-control attr-control--primary" @click.stop>
                    <span class="attr-label">基础属性</span>
                    <div aria-label="基础属性等级" class="attr-pips" role="group">
                      <span
                        v-for="level in affixLevelItems"
                        :key="`a1-${level}`"
                        :aria-label="`设置基础属性为 +${level}`"
                        class="pip"
                        :class="{
                          active: level <= entry.affix1_level,
                          'pip--max': entry.affix1_level === 6,
                        }"
                        role="button"
                        tabindex="0"
                        @click.stop="setEntryAffixLevel(entry, 1, level)"
                        @keydown.enter.stop.prevent="setEntryAffixLevel(entry, 1, level)"
                        @keydown.space.stop.prevent="setEntryAffixLevel(entry, 1, level)"
                      />
                    </div>
                    <span
                      class="attr-value"
                      :class="{ 'attr-value--full': entry.affix1_level === 6 }"
                    >
                      +{{ entry.affix1_level }} / 6
                    </span>
                    <span v-if="entry.affix1_level === 6" class="max-label">MAX</span>
                  </div>

                  <div class="attr-control attr-control--teal" @click.stop>
                    <span class="attr-label">附加属性</span>
                    <div aria-label="附加属性等级" class="attr-pips" role="group">
                      <span
                        v-for="level in affixLevelItems"
                        :key="`a2-${level}`"
                        :aria-label="`设置附加属性为 +${level}`"
                        class="pip"
                        :class="{
                          active: level <= entry.affix2_level,
                          'pip--max': entry.affix2_level === 6,
                        }"
                        role="button"
                        tabindex="0"
                        @click.stop="setEntryAffixLevel(entry, 2, level)"
                        @keydown.enter.stop.prevent="setEntryAffixLevel(entry, 2, level)"
                        @keydown.space.stop.prevent="setEntryAffixLevel(entry, 2, level)"
                      />
                    </div>
                    <span
                      class="attr-value"
                      :class="{ 'attr-value--full': entry.affix2_level === 6 }"
                    >
                      +{{ entry.affix2_level }} / 6
                    </span>
                    <span v-if="entry.affix2_level === 6" class="max-label">MAX</span>
                  </div>

                  <div class="attr-control attr-control--indigo" @click.stop>
                    <span class="attr-label">技能属性</span>
                    <div aria-label="技能属性等级" class="attr-pips attr-pips--skill" role="group">
                      <span
                        v-for="level in skillLevelItems"
                        :key="`a3-${level}`"
                        :aria-label="`设置技能属性为 +${level}`"
                        class="pip"
                        :class="{
                          active: level <= entry.affix3_level,
                          'pip--max': entry.affix3_level === 3,
                        }"
                        role="button"
                        tabindex="0"
                        @click.stop="setEntryAffixLevel(entry, 3, level)"
                        @keydown.enter.stop.prevent="setEntryAffixLevel(entry, 3, level)"
                        @keydown.space.stop.prevent="setEntryAffixLevel(entry, 3, level)"
                      />
                    </div>
                    <span
                      class="attr-value"
                      :class="{ 'attr-value--full': entry.affix3_level === 3 }"
                    >
                      +{{ entry.affix3_level }} / 3
                    </span>
                    <span v-if="entry.affix3_level === 3" class="max-label">MAX</span>
                  </div>
                </section>

                <section class="card-action-rail">
                  <v-tooltip text="计算此武器的刷取建议">
                    <template #activator="{ props }">
                      <v-btn
                        v-bind="props"
                        class="matrix-action matrix-action--calc"
                        color="primary"
                        icon="mdi-calculator"
                        size="small"
                        variant="tonal"
                        @click.stop="computeSingle(entry)"
                      />
                    </template>
                  </v-tooltip>
                  <v-tooltip text="移除此武器">
                    <template #activator="{ props }">
                      <v-btn
                        v-bind="props"
                        class="matrix-action matrix-action--delete"
                        color="error"
                        icon="mdi-delete-outline"
                        size="small"
                        variant="tonal"
                        @click.stop="removeEntry(index)"
                      />
                    </template>
                  </v-tooltip>
                </section>
              </div>
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
                id="treasure-matrix-target-affix1"
                v-model="targetAffix1"
                density="compact"
                hide-details
                :items="affixLevelItems"
                label="目标基础属性"
                name="treasure-matrix-target-affix1"
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
                id="treasure-matrix-target-affix2"
                v-model="targetAffix2"
                density="compact"
                hide-details
                :items="affixLevelItems"
                label="目标附加属性"
                name="treasure-matrix-target-affix2"
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
                id="treasure-matrix-target-affix3"
                v-model="targetAffix3"
                density="compact"
                hide-details
                :items="skillLevelItems"
                label="目标技能属性"
                name="treasure-matrix-target-affix3"
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
                <custom-stat-icon v-if="isCustomEntry(rec.weapon_id)" hide-name :name="getCustomStatName(rec.weapon_id)" small />
                <item-icon v-else class="weapon-icon-small" :item-id="rec.weapon_id" />
              </template>
              <v-card-title>{{ isCustomEntry(rec.weapon_id) ? getCustomStatName(rec.weapon_id) : rec.weapon_name }}</v-card-title>
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
            id="treasure-matrix-weapon-search"
            v-model="weaponSearch"
            class="mb-4"
            clearable
            density="compact"
            hide-details
            label="搜索武器名称..."
            name="treasure-matrix-weapon-search"
            prepend-inner-icon="mdi-magnify"
            variant="outlined"
          />
          <!-- 自定义基质区段 -->
          <template v-if="customMatrixEntries.length > 0">
            <h4 class="mt-4 mb-2 d-flex align-center">
              <v-icon class="me-2" color="#ff5a36">mdi-diamond-stone</v-icon>
              自定义基质
            </h4>
            <div class="weapon-grid">
              <div
                v-for="entry in customMatrixEntries"
                :key="entry.syntheticId"
                class="weapon-item"
                @click="onAddCustomStat(entry.index)"
              >
                <custom-stat-icon :name="entry.displayName" />
              </div>
            </div>
          </template>
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
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import BackToTop from '@/components/BackToTop.vue'
import CustomStatIcon from '@/components/CustomStatIcon.vue'
import ItemIcon from '@/components/ItemIcon.vue'
import WeaponOverview from '@/components/WeaponOverview.vue'
import { type TreasureMatrixEntry, useProfiles } from '@/composables/useProfiles'
import { useRarityFilters } from '@/composables/useRarityFilters'
import { useStaticData } from '@/utils/gameData/staticData'
import { getGemTagName, getStatsForWeapon } from '@/utils/gameData/weapon'
import { safeLoadJson, safeRemoveJson, safeSetJson } from '@/utils/safeStorage'

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

const showAddWeaponDialog = ref(false)
const weaponSearch = ref('')
const computing = ref(false)

// --- 自定义基质相关 ---

/** 判断是否为自定义基质条目（weapon_id 以 custom_stat_ 开头） */
function isCustomEntry(weaponId: string): boolean {
  return weaponId.startsWith('custom_stat_')
}

/** 获取自定义基质的显示名称 */
function getCustomStatName(weaponId: string): string {
  const index = Number.parseInt(weaponId.replace('custom_stat_', ''), 10)
  return customStats.value[index]?.name || `自定义基质 ${index + 1}`
}

/** 自定义宝藏基质属性配置列表，用于读取自定义条目的属性名 */
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

/** 自定义基质条目列表，用于添加武器对话框展示 */
const customMatrixEntries = computed(() => {
  return customStats.value.map((stat, index) => ({
    syntheticId: `custom_stat_${index}`,
    displayName: stat.name || `自定义基质 ${index + 1}`,
    index,
  }))
})

/** 添加自定义基质条目到宝藏基质配置 */
async function onAddCustomStat(index: number) {
  const syntheticId = `custom_stat_${index}`
  // 检查是否已添加
  if (matrixEntries.value.some((e) => e.weapon_id === syntheticId)) return
  const stat = customStats.value[index]
  await addTreasureMatrixEntry({
    weapon_id: syntheticId,
    weapon_name: stat?.name || `自定义基质 ${index + 1}`,
    affix1_level: 1,
    affix2_level: 1,
    affix3_level: 1,
  })
  showAddWeaponDialog.value = false
}

const targetAffix1 = ref(6)
const targetAffix2 = ref(6)
const targetAffix3 = ref(3)

const affixLevelItems = [1, 2, 3, 4, 5, 6]
const skillLevelItems = [1, 2, 3]

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

// 缓存 key 绑定到账号，避免跨账号数据污染
const recommendationsKey = computed(
  () => `treasureMatrixRecommendations:${activeProfileName.value}`,
)
const frozenOrderKey = computed(
  () => `treasureMatrixFrozenOrder:${activeProfileName.value}`,
)

const recommendations = ref<Recommendation[]>([])
let saveRecommendationsTimer: number | undefined
let saveFrozenOrderTimer: number | undefined

// 跟踪每个武器的每个步骤是否使用冷却脂
// 格式: { weaponId: { 'affixIndex-fromLevel': boolean } }
const useGreaseForSteps = ref<Record<string, Record<string, boolean>>>({})

// 排序后的推荐列表：初始排序后保持稳定，用户切换冷却脂时不重新排序
const frozenSortOrder = ref<string[] | null>(null)

// 账号切换时重新加载缓存
watch(
  activeProfileName,
  () => {
    recommendations.value = safeLoadJson<Recommendation[]>(recommendationsKey.value, [])
    frozenSortOrder.value = safeLoadJson<string[] | null>(frozenOrderKey.value, null)
  },
  { immediate: true },
)

// Keep cached recommendations as the only initially open panel to avoid mounting every panel on route enter.
const openedPanels = ref<number[]>([])

// 监听 recommendations 变化，更新面板状态和保存到 localStorage
watch(
  recommendations,
  (newValue) => {
    openedPanels.value = newValue.length > 0 ? [2] : [0, 1, 2]
    window.clearTimeout(saveRecommendationsTimer)
    saveRecommendationsTimer = window.setTimeout(() => {
      if (newValue.length > 0) {
        safeSetJson(recommendationsKey.value, newValue)
      } else {
        safeRemoveJson(recommendationsKey.value)
      }
    }, 300)
  },
  { deep: true }
)

// 保存冻结的排序顺序到 localStorage
watch(
  frozenSortOrder,
  (newValue) => {
    window.clearTimeout(saveFrozenOrderTimer)
    saveFrozenOrderTimer = window.setTimeout(() => {
      if (newValue) {
        safeSetJson(frozenOrderKey.value, newValue)
      } else {
        safeRemoveJson(frozenOrderKey.value)
      }
    }, 300)
  },
  { deep: true }
)

onUnmounted(() => {
  window.clearTimeout(saveRecommendationsTimer)
  window.clearTimeout(saveFrozenOrderTimer)
  if (debounceTimer) {
    clearTimeout(debounceTimer)
    debounceTimer = null
  }
})

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

  // 过滤稀有度（自定义条目按 6★ 处理）
  entries = entries.filter((entry) => {
    if (isCustomEntry(entry.weapon_id)) {
      return selectedRarities.value.includes('6')
    }
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

  // 按优先级降序排序，优先级相同时按稀有度降序排序（6★ -> 3★）
  return entries.toSorted((a, b) => {
    // 自定义条目始终排在最前面
    const aCustom = isCustomEntry(a.weapon_id) ? 1 : 0
    const bCustom = isCustomEntry(b.weapon_id) ? 1 : 0
    if (aCustom !== bCustom) return bCustom - aCustom

    const pa = a.priority || 0
    const pb = b.priority || 0
    if (pa !== pb) return pb - pa
    const wa = weaponsMap.value.get(a.weapon_id)
    const wb = weaponsMap.value.get(b.weapon_id)
    if (wa && wb) return wb.rarity - wa.rarity
    return 0
  })
})

/**
 * 获取武器的属性名称列表
 * 自定义条目从 customStats 配置中读取
 */
function getWeaponTraitNames(weaponId: string): string[] {
  // 自定义条目：从配置中读取属性
  if (isCustomEntry(weaponId)) {
    const index = Number.parseInt(weaponId.replace('custom_stat_', ''), 10)
    const stat = customStats.value[index]
    if (!stat) return ['自定义基质']
    const parts: string[] = []
    if (stat.attribute) parts.push(getGemTagName(stat.attribute))
    if (stat.secondary) parts.push(getGemTagName(stat.secondary))
    if (stat.skill) parts.push(getGemTagName(stat.skill))
    return parts.length > 0 ? parts : ['自定义基质']
  }

  const stats = getStatsForWeapon(weaponId)
  const parts: string[] = []
  if (stats.attribute) parts.push(getGemTagName(stats.attribute))
  if (stats.secondary) parts.push(getGemTagName(stats.secondary))
  if (stats.skill) parts.push(getGemTagName(stats.skill))
  return parts.length > 0 ? parts : ['无属性']
}

/**
 * 获取武器稀有度
 * 自定义条目默认为 6★
 */
function getWeaponRarity(weaponId: string): number | null {
  if (isCustomEntry(weaponId)) return 6
  return weaponsMap.value.get(weaponId)?.rarity ?? null
}

function getWeaponTierClass(weaponId: string): string {
  const rarity = getWeaponRarity(weaponId)
  return rarity ? `tier-${rarity}` : ''
}

function getWeaponRarityText(weaponId: string): string {
  const rarity = getWeaponRarity(weaponId)
  return rarity ? `${rarity}★` : '??'
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

function calculateAdjustedStats(rec: Recommendation) {
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

const adjustedStatsByWeaponId = computed(() => {
  const result = new Map<string, ReturnType<typeof calculateAdjustedStats>>()
  for (const rec of recommendations.value) {
    result.set(rec.weapon_id, calculateAdjustedStats(rec))
  }
  return result
})

function getAdjustedStats(rec: Recommendation) {
  // 模板中同一推荐项会多次读取统计值，集中缓存可避免每次渲染重复遍历升级步骤。
  return adjustedStatsByWeaponId.value.get(rec.weapon_id) ?? calculateAdjustedStats(rec)
}

function persistMatrix(entries: TreasureMatrixEntry[]) {
  void updateTreasureMatrix(entries).catch(() => {
    // 错误已由 useProfiles 的 lastError 处理
  })
}

function toggleIncludeInCalculation(entry: TreasureMatrixEntry) {
  entry.include_in_calculation = !entry.include_in_calculation
  persistMatrix([...matrixEntries.value])
}

let debounceTimer: ReturnType<typeof setTimeout> | null = null

function setEntryAffixLevel(entry: TreasureMatrixEntry, affixIndex: 1 | 2 | 3, level: number) {
  if (affixIndex === 1) entry.affix1_level = level
  if (affixIndex === 2) entry.affix2_level = level
  if (affixIndex === 3) entry.affix3_level = level
  onEntryChange()
}

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
    persistMatrix([...matrixEntries.value])
    debounceTimer = null
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

        // 自定义基质始终参与计算
        if (isCustomEntry(entry.weapon_id)) return true

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
    const sortedResults = results.toSorted(
      (a: Recommendation, b: Recommendation) => a.total_expected_runs - b.total_expected_runs,
    )
    frozenSortOrder.value = null
    recommendations.value = sortedResults

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
  fetchCustomStats()
})
</script>

<style scoped lang="scss">
$weapon-icon-size: clamp(2.5rem, 14vw, 5rem);

.treasure-matrix-page {
  .entry-card {
    position: relative;
    overflow: hidden;
    border-color: rgba(var(--v-border-color), 0.12);
    border-radius: 18px;
    background:
      linear-gradient(135deg, rgba(var(--v-theme-surface), 1), rgba(var(--v-theme-primary), 0.035)),
      rgb(var(--v-theme-surface));
    box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
    transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease,
      opacity 0.18s ease, filter 0.18s ease;

    &:hover {
      transform: translateY(-1px);
      border-color: rgba(var(--v-theme-primary), 0.35);
      box-shadow: 0 12px 28px rgba(15, 23, 42, 0.09), 0 2px 8px rgba(15, 23, 42, 0.06) !important;
    }

    &.entry-card--muted {
      opacity: 0.58;
      filter: grayscale(0.25);

      &:hover {
        opacity: 0.82;
        filter: grayscale(0);
      }
    }

    .clickable-card {
      cursor: pointer;
      user-select: none;
    }

    .matrix-card-body {
      display: flex;
      align-items: stretch;
      min-height: 76px;
    }

    .weapon-identity {
      position: relative;
      display: flex;
      flex: 0 0 270px;
      align-items: center;
      gap: 12px;
      padding: 0 20px;
      background: linear-gradient(135deg, rgba(var(--v-theme-surface), 0.98), rgba(var(--v-theme-primary), 0.06));
      border-right: 1px solid rgba(var(--v-border-color), 0.12);

      &::after {
        content: '';
        position: absolute;
        top: 18px;
        right: 0;
        bottom: 18px;
        width: 1px;
        background: linear-gradient(
          to bottom,
          transparent,
          rgba(var(--v-border-color), 0.28),
          transparent
        );
      }
    }

    .weapon-icon-wrap {
      position: relative;
      width: 46px;
      height: 46px;
      flex-shrink: 0;
      border: 2px solid rgba(var(--v-theme-primary), 0.35);
      border-radius: 10px;
      box-shadow: 0 4px 12px rgba(var(--v-theme-primary), 0.16);
    }

    .weapon-icon-wrap .weapon-icon-small {
      width: 100% !important;
      height: 100% !important;
      border-radius: 8px;
    }

    /* 自定义基质条目图标样式 */
    .weapon-icon-wrap.tier-6 {
      border-color: #ff5a36;
      box-shadow: 0 4px 14px rgba(255, 90, 54, 0.28);
    }

    .weapon-icon-wrap.tier-6 .weapon-tier {
      background: #ff5a36;
    }

    .weapon-icon-wrap.tier-5 {
      border-color: #ffb020;
      box-shadow: 0 4px 14px rgba(255, 176, 32, 0.28);
    }

    .weapon-icon-wrap.tier-5 .weapon-tier {
      background: #ffb020;
    }

    .weapon-icon-wrap.tier-4 {
      border-color: #8e5cff;
      box-shadow: 0 4px 14px rgba(142, 92, 255, 0.24);
    }

    .weapon-icon-wrap.tier-4 .weapon-tier {
      background: #8e5cff;
    }

    .weapon-icon-wrap.tier-3 {
      border-color: #2196f3;
      box-shadow: 0 4px 14px rgba(33, 150, 243, 0.22);
    }

    .weapon-icon-wrap.tier-3 .weapon-tier {
      background: #2196f3;
    }

    .weapon-tier {
      position: absolute;
      right: -8px;
      bottom: -7px;
      padding: 1px 6px;
      border-radius: 999px;
      color: #fff;
      background: rgba(15, 23, 42, 0.82);
      font-size: 0.625rem;
      font-weight: 800;
      line-height: 1.5;
      box-shadow: 0 2px 6px rgba(15, 23, 42, 0.2);
    }

    .weapon-info {
      min-width: 0;
      flex: 1;
    }

    .weapon-name {
      overflow: hidden;
      color: rgba(var(--v-theme-on-surface), 0.92);
      font-size: 0.95rem;
      font-weight: 800;
      line-height: 1.3;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .weapon-traits {
      display: flex;
      flex-wrap: wrap;
      gap: 2px 0;
      margin-top: 4px;
      color: rgba(var(--v-theme-on-surface), 0.58);
      font-size: 0.75rem;
      line-height: 1.35;
    }

    .trait {
      white-space: nowrap;

      &::after {
        content: ' / ';
        opacity: 0.42;
      }

      &:last-child::after {
        display: none;
      }
    }

    .participation-chip {
      margin-top: 8px;
      font-weight: 700;
    }

    .attribute-section {
      display: flex;
      flex: 1;
      align-items: center;
      gap: 12px;
      padding: 8px 18px;
    }

    .attr-control {
      position: relative;
      display: flex;
      flex: 1;
      min-width: 118px;
      flex-direction: column;
      align-items: center;
      gap: 4px;
      padding: 0 10px;
      border: 1px solid transparent;
      border-radius: 12px;
      transition: background 0.18s ease, border-color 0.18s ease, transform 0.18s ease;

      &:hover {
        transform: translateY(-1px);
        border-color: rgba(var(--v-border-color), 0.16);
        background: rgba(var(--v-theme-on-surface), 0.035);
      }
    }

    .attr-label {
      color: rgba(var(--v-theme-on-surface), 0.52);
      font-size: 0.68rem;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      white-space: nowrap;
    }

    .attr-pips {
      display: flex;
      align-items: center;
      gap: 3px;
      min-height: 18px;
    }

    .pip {
      width: 8px;
      height: 17px;
      border-radius: 999px;
      background: rgba(var(--v-theme-on-surface), 0.12);
      cursor: pointer;
      transition: background 0.18s ease, box-shadow 0.18s ease, transform 0.18s ease;

      &:hover,
      &:focus-visible {
        outline: none;
        transform: translateY(-1px) scaleY(1.08);
      }
    }

    .attr-control--primary .pip.active {
      background: rgb(var(--v-theme-primary));
      box-shadow: 0 2px 7px rgba(var(--v-theme-primary), 0.32);
    }

    .attr-control--teal .pip.active {
      background: #48a9a6;
      box-shadow: 0 2px 7px rgba(72, 169, 166, 0.34);
    }

    .attr-control--indigo .pip.active {
      background: #5c6bc0;
      box-shadow: 0 2px 7px rgba(92, 107, 192, 0.34);
    }

    .pip.pip--max.active {
      animation: matrixPipPulse 2.2s ease-in-out infinite;
    }

    .attr-value {
      color: rgba(var(--v-theme-on-surface), 0.68);
      font-family: 'JetBrains Mono', 'Fira Code', monospace;
      font-size: 0.82rem;
      font-weight: 800;
    }

    .attr-value--full {
      color: rgb(var(--v-theme-primary));
    }

    .max-label {
      position: absolute;
      top: 8px;
      right: 8px;
      padding: 1px 6px;
      border-radius: 999px;
      color: rgb(var(--v-theme-primary));
      background: rgba(var(--v-theme-primary), 0.1);
      font-size: 0.62rem;
      font-weight: 900;
      letter-spacing: 0.04em;
    }

    .card-action-rail {
      display: flex;
      flex: 0 0 auto;
      flex-direction: column;
      justify-content: center;
      gap: 8px;
      padding: 10px 16px 10px 0;
    }

    .matrix-action {
      border-radius: 10px;
    }

  }

  @keyframes matrixPipPulse {
    0%,
    100% {
      transform: scaleY(1);
      filter: brightness(1);
    }

    50% {
      transform: scaleY(1.08);
      filter: brightness(1.18);
    }
  }

  @media (max-width: 900px) {
    .entry-card {
      .matrix-card-body {
        flex-direction: column;
      }

      .weapon-identity {
        flex: none;
        border-right: none;
        border-bottom: 1px solid rgba(var(--v-border-color), 0.12);

        &::after {
          display: none;
        }
      }

      .attribute-section {
        padding: 14px 16px;
      }

      .card-action-rail {
        flex-direction: row;
        justify-content: flex-end;
        padding: 0 16px 14px;
      }
    }
  }

  @media (max-width: 640px) {
    .entry-card {
      .weapon-identity {
        padding: 16px;
      }

      .attribute-section {
        display: grid;
        grid-template-columns: 1fr;
        gap: 10px;
      }

      .attr-control {
        display: grid;
        grid-template-columns: 72px 1fr 104px;
        align-items: center;
        width: 100%;
      }

      .attr-pips {
        justify-content: center;
      }

      .max-label {
        top: 50%;
        right: 122px;
        transform: translateY(-50%);
      }
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
