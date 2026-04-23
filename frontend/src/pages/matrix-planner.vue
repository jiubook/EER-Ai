<template>
  <v-container class="h-100 d-flex flex-column matrix-planner-page">
    <v-row>
      <!-- 左侧：最优刷取方案 -->
      <v-col cols="12" lg="6">
        <v-expansion-panels model-value="计算结果">
          <v-expansion-panel value="计算结果">
            <v-expansion-panel-title>
              <v-icon class="mr-2">mdi-map-search</v-icon>
              最优刷取方案
            </v-expansion-panel-title>
            <v-expansion-panel-text>
              <template v-if="bestChoices.length > 0">
                <v-card
                  v-for="(choice, i) in bestChoices"
                  :key="choice.battleId + '-' + choice.selectedSecondary + '-' + choice.selectedSkill"
                  class="mb-4 choice-card"
                  :class="{ 'choice-card--top': i === 0 }"
                  elevation="2"
                  rounded="lg"
                  variant="outlined"
                >
                  <v-card-item :class="i === 0 ? 'bg-primary' : 'bg-info'" class="py-3">
                    <v-card-title class="text-h6 font-weight-bold d-flex align-center">
                      <v-icon v-if="i === 0" class="mr-2" size="small">mdi-trophy</v-icon>
                      方案 {{ i + 1 }}
                    </v-card-title>
                    <template #append>
                      <v-chip class="font-weight-bold mr-2" color="white" size="small" variant="flat">
                        {{ choice.matchedSelectedIndices.length }} 项需求满足
                      </v-chip>
                      <v-chip class="font-weight-bold" color="white" size="small" variant="flat">
                        {{ choice.matchedWeaponIds.length }} 把武器匹配
                      </v-chip>
                    </template>
                  </v-card-item>
                  <v-divider />
                  <v-card-text class="pt-4">
                    <v-row>
                      <v-col cols="12" md="5">
                        <div class="d-flex align-center mb-3">
                          <v-icon class="mr-2" color="primary" icon="mdi-map-marker" size="small" />
                          <span class="text-subtitle-1 font-weight-bold">刷取地点</span>
                        </div>
                        <div class="pl-1 mb-4">
                          <v-chip color="info" label variant="flat">
                            <v-icon start size="small">mdi-sword-cross</v-icon>
                            {{ choice.battleName }}
                          </v-chip>
                        </div>
                        <div class="d-flex align-center mb-3">
                          <v-icon class="mr-2" color="primary" icon="mdi-tune" size="small" />
                          <span class="text-subtitle-1 font-weight-bold">预刻属性</span>
                        </div>
                        <div class="pl-1">
                          <div class="mb-3">
                            <div class="text-medium-emphasis mb-1">基础属性</div>
                            <div class="d-flex flex-wrap ga-2">
                              <v-chip v-for="attr in choice.selectedAttribute" :key="attr" color="primary" label size="small" variant="flat">
                                {{ attr }}
                              </v-chip>
                            </div>
                          </div>
                          <div v-if="choice.selectedSecondary" class="mb-3">
                            <div class="text-medium-emphasis mb-1">附加属性</div>
                            <v-chip color="teal" label size="small" variant="flat">
                              {{ choice.selectedSecondary }}
                            </v-chip>
                          </div>
                          <div v-if="choice.selectedSkill" class="mb-3">
                            <div class="text-medium-emphasis mb-1">技能属性</div>
                            <v-chip color="blue" label size="small" variant="flat">
                              {{ choice.selectedSkill }}
                            </v-chip>
                          </div>
                        </div>
                      </v-col>
                      <v-divider class="hidden-sm-and-down" vertical />
                      <v-divider class="hidden-md-and-up my-4" />
                      <v-col cols="12" md="7">
                        <div class="d-flex align-center mb-3">
                          <v-icon class="mr-2" color="success" icon="mdi-check-circle-outline" size="small" />
                          <span class="text-subtitle-1 font-weight-bold">
                            满足 {{ choice.matchedSelectedIndices.length }} 项需求，匹配 {{ choice.matchedWeaponIds.length }} 把武器
                          </span>
                        </div>
                        <div class="pl-1">
                          <div class="mb-3">
                            <div class="text-medium-emphasis mb-1">满足的需求</div>
                            <div class="d-flex flex-wrap ga-2">
                              <div v-for="index in choice.matchedSelectedIndices" :key="index">
                                <v-tooltip activator="parent" location="bottom">
                                  {{ getRequirementTooltip(index) }}
                                </v-tooltip>
                                <v-card class="pa-2" variant="tonal">
                                  <div class="text-center font-weight-bold text-caption">
                                    #{{ index + 1 }}
                                    {{ getEssenceStatDescription(requiredEssenceStats[index]!) }}
                                  </div>
                                </v-card>
                              </div>
                            </div>
                          </div>
                          <div>
                            <div class="text-medium-emphasis mb-1">匹配的武器</div>
                            <div class="d-flex flex-wrap ga-2">
                              <div v-for="weaponId in sortedWeaponIds(choice.matchedWeaponIds)" :key="weaponId">
                                <item-icon class="weapon-item" :item-id="weaponId" show-item-name />
                              </div>
                            </div>
                          </div>
                        </div>
                      </v-col>
                    </v-row>
                  </v-card-text>
                </v-card>
              </template>
              <v-alert v-else border="start" type="info" variant="tonal">
                请在右侧添加需求的基质属性，系统会自动计算最优刷取方案。
              </v-alert>
            </v-expansion-panel-text>
          </v-expansion-panel>
        </v-expansion-panels>
      </v-col>

      <!-- 右侧：需求设定 -->
      <v-col cols="12" lg="6">
        <v-expansion-panels model-value="需求设定">
          <v-expansion-panel value="需求设定">
            <v-expansion-panel-title>
              <v-icon class="mr-2">mdi-cog</v-icon>
              需求设定
            </v-expansion-panel-title>
            <v-expansion-panel-text>
              <p class="mb-4 text-medium-emphasis">
                选择你需要的基质属性组合，系统会自动找到最佳的能量淤积点刷取方案。
                你可以从武器预设中选择，也可以自定义属性组合。
              </p>

              <!-- Selected requirements -->
              <v-card
                v-for="(stat, index) in requiredEssenceStats"
                :key="stat.id"
                class="pa-2 my-2 stat-card"
                elevation="1"
                variant="outlined"
              >
                <v-row align="center">
                  <v-col cols="12" md="2">
                    <div class="d-flex align-center">
                      <v-avatar class="mr-2" color="primary" size="small" variant="tonal">
                        <span class="text-caption font-weight-bold">{{ index + 1 }}</span>
                      </v-avatar>
                      <span class="text-caption text-medium-emphasis">{{ getEssenceStatDescription(stat) }}</span>
                    </div>
                  </v-col>
                  <v-col cols="12" md="2">
                    <v-select
                      v-if="stat.isCustom"
                      v-model="stat.attribute"
                      density="compact"
                      hide-details
                      :items="allAttributeStats.map((s) => ({ title: s, value: s }))"
                      label="基础属性"
                      variant="outlined"
                    />
                    <v-chip v-else color="primary" size="small" variant="flat">
                      {{ getStatDisplayName(stat.attribute) }}
                    </v-chip>
                  </v-col>
                  <v-col cols="12" md="2">
                    <v-select
                      v-if="stat.isCustom"
                      v-model="stat.secondary"
                      density="compact"
                      hide-details
                      :items="allSecondaryStats.map((s) => ({ title: s, value: s }))"
                      label="附加属性"
                      variant="outlined"
                    />
                    <v-chip v-else color="teal" size="small" variant="flat">
                      {{ getStatDisplayName(stat.secondary) }}
                    </v-chip>
                  </v-col>
                  <v-col cols="12" md="2">
                    <v-select
                      v-if="stat.isCustom"
                      v-model="stat.skill"
                      density="compact"
                      hide-details
                      :items="allSkillStats.map((s) => ({ title: s, value: s }))"
                      label="技能属性"
                      variant="outlined"
                    />
                    <v-chip v-else color="blue" size="small" variant="flat">
                      {{ getStatDisplayName(stat.skill) }}
                    </v-chip>
                  </v-col>
                  <v-col cols="12" md="4">
                    <div class="d-flex ga-1">
                      <v-btn :disabled="index === 0" icon="mdi-chevron-up" size="small" variant="text" @click="moveStatUp(index)" />
                      <v-btn
                        :disabled="index === requiredEssenceStats.length - 1"
                        icon="mdi-chevron-down"
                        size="small"
                        variant="text"
                        @click="moveStatDown(index)"
                      />
                      <v-btn color="error" icon="mdi-delete" size="small" variant="text" @click="removeStat(index)" />
                    </div>
                  </v-col>
                </v-row>
              </v-card>

              <div v-if="requiredEssenceStats.length === 0" class="text-center py-6">
                <v-icon class="mb-2" color="medium-emphasis" size="48">mdi-plus-circle-outline</v-icon>
                <div class="text-medium-emphasis">尚未添加任何需求，点击下方按钮开始</div>
              </div>

              <!-- Add buttons -->
              <div class="mt-4 mb-4">
                <v-btn
                  class="mr-2"
                  color="primary"
                  prepend-icon="mdi-plus"
                  variant="flat"
                  @click="addCustomStat"
                >
                  自定义属性
                </v-btn>
              </div>

              <!-- Weapon presets -->
              <v-divider class="my-4" />
              <h3 class="mb-3 d-flex align-center">
                <v-icon class="mr-2" size="small">mdi-sword</v-icon>
                从武器预设添加
              </h3>
              <v-text-field
                v-model="weaponSearch"
                class="mb-4"
                density="compact"
                hide-details
                label="搜索武器名称..."
                prepend-inner-icon="mdi-magnify"
                variant="outlined"
              />
              <template v-for="wType in weaponTypes" :key="wType.id">
                <div class="d-flex align-center mb-2 mt-4">
                  <img
                    :alt="wType.name"
                    class="group-icon me-2"
                    :src="wType.iconUrl"
                  />
                  <h4>{{ wType.name }}</h4>
                </div>
                <div class="weapon-grid">
                  <div
                    v-for="weaponId in filteredWeaponIds(wType.weaponIds)"
                    :key="weaponId"
                    class="weapon-item"
                    :class="{ 'weapon-selected': isWeaponSelected(weaponId) }"
                    @click="addStatFromWeapon(weaponId)"
                  >
                    <item-icon :item-id="weaponId" show-item-name />
                    <div v-if="isWeaponSelected(weaponId)" class="weapon-selected-overlay">
                      <v-icon color="white" size="small">mdi-check-circle</v-icon>
                    </div>
                  </div>
                </div>
              </template>
            </v-expansion-panel-text>
          </v-expansion-panel>
        </v-expansion-panels>
      </v-col>
    </v-row>
  </v-container>
</template>

<script lang="ts" setup>
import { ref } from 'vue'
import ItemIcon from '@/components/ItemIcon.vue'
import { useMatrixPlanner } from '@/composables/useMatrixPlanner'
import { useStaticData } from '@/utils/gameData/staticData'

const { weaponTypes, weaponsMap } = useStaticData()
const {
  requiredEssenceStats,
  allAttributeStats,
  allSecondaryStats,
  allSkillStats,
  addStatFromWeapon,
  addCustomStat,
  removeStat,
  moveStatUp,
  moveStatDown,
  getEssenceStatDescription,
  getStatDisplayName,
  bestChoices,
} = useMatrixPlanner()

const weaponSearch = ref('')

function filteredWeaponIds(weaponIds: string[]): string[] {
  if (!weaponSearch.value.trim()) return weaponIds
  const search = weaponSearch.value.trim().toLowerCase()
  return weaponIds.filter((id) => {
    const weapon = weaponsMap.value.get(id)
    return weapon && weapon.name.toLowerCase().includes(search)
  })
}

function isWeaponSelected(weaponId: string): boolean {
  return requiredEssenceStats.value.some((s) => !s.isCustom && s.weaponId === weaponId)
}

function getRequirementTooltip(index: number): string {
  const stat = requiredEssenceStats.value[index]
  if (!stat) return ''
  const parts: string[] = []
  if (stat.attribute) parts.push(getStatDisplayName(stat.attribute))
  if (stat.secondary) parts.push(getStatDisplayName(stat.secondary))
  if (stat.skill) parts.push(getStatDisplayName(stat.skill))
  return parts.join('、') || '未设置'
}

function sortedWeaponIds(weaponIds: string[]): string[] {
  return weaponIds.toSorted((a, b) => {
    const wa = weaponsMap.value.get(a)
    const wb = weaponsMap.value.get(b)
    if (wa && wb) return wb.rarity - wa.rarity
    return 0
  })
}
</script>

<style scoped lang="scss">
$weapon-icon-size: clamp(2.5rem, 12vw, 4.5rem);

.matrix-planner-page {
  .choice-card {
    transition: transform 0.2s ease, box-shadow 0.2s ease;
    &:hover {
      transform: translateY(-2px);
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1) !important;
    }
    &--top {
      border-width: 2px;
    }
  }

  .stat-card {
    transition: background-color 0.15s ease;
    &:hover {
      background-color: rgba(var(--v-theme-primary), 0.04);
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
  position: relative;
  transition: transform 0.15s;
  border-radius: 6px;
  &:hover {
    transform: scale(1.1);
  }
}

.weapon-selected-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.45);
  border-radius: 6px;
  pointer-events: none;
}
</style>
