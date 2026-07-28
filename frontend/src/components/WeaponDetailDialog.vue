<template>
  <v-dialog :model-value="modelValue" max-width="680" @update:model-value="emit('update:modelValue', $event)">
    <v-card v-if="weaponId">
      <v-card-item>
        <template #prepend>
          <slot name="prepend-icon">
            <custom-stat-icon
              v-if="isCustom"
              class="weapon-icon-detail"
              hide-name
              :name="isNewCustom ? (customEntryName || '新基质') : getCustomStatName(weaponId)"
              :skill-stat-id="isNewCustom ? customEditSkill : getCustomStatSkill(weaponId)"
            />
            <item-icon v-else class="weapon-icon-detail" :item-id="weaponId" />
          </slot>
        </template>
        <v-card-title>
          <slot name="title">
            <v-text-field
              v-if="isCustom && editableAttributes"
              :model-value="customEntryName"
              density="compact"
              hide-details
              placeholder="自定义基质名称"
              variant="underlined"
              @update:model-value="emit('update:customEntryName', $event)"
            />
            <template v-else>
              {{ isCustom ? getCustomStatName(weaponId) : weaponName }}
            </template>
          </slot>
        </v-card-title>
        <template #append>
          <v-btn icon="mdi-close" variant="text" @click="emit('update:modelValue', false)" />
        </template>
      </v-card-item>
      <v-divider />
      <v-card-text>
        <!-- 基质属性 -->
        <div class="mb-4">
          <div class="text-subtitle-2 mb-2">基质属性</div>
          <v-row dense>
            <v-col cols="12" sm="4">
              <v-select
                :clearable="editableAttributes"
                density="compact"
                :disabled="!editableAttributes"
                hide-details
                :items="attributeStatOptions"
                label="基础属性"
                :model-value="attributeStatId"
                variant="outlined"
                @update:model-value="emit('update:customEditAttribute', $event)"
              />
            </v-col>
            <v-col cols="12" sm="4">
              <v-select
                :clearable="editableAttributes"
                density="compact"
                :disabled="!editableAttributes"
                hide-details
                :items="secondaryStatOptions"
                label="附加属性"
                :model-value="secondaryStatId"
                variant="outlined"
                @update:model-value="emit('update:customEditSecondary', $event)"
              />
            </v-col>
            <v-col cols="12" sm="4">
              <v-select
                :clearable="editableAttributes"
                density="compact"
                :disabled="!editableAttributes"
                hide-details
                :items="skillStatOptions"
                label="技能属性"
                :model-value="skillStatId"
                variant="outlined"
                @update:model-value="emit('update:customEditSkill', $event)"
              />
            </v-col>
          </v-row>
        </div>

        <!-- 基质等级 -->
        <div class="mb-4">
          <div class="text-subtitle-2 mb-2">当前基质等级</div>
          <div class="detail-level-wrapper">
            <div class="detail-level-section">
              <div class="detail-attr-control detail-attr-control--primary">
                <span class="detail-attr-label">基础属性</span>
                <div class="detail-attr-pips">
                  <span
                    v-for="level in affixLevelItems"
                    :key="`d-a1-${level}`"
                    class="detail-pip"
                    :class="{
                      active: level <= affix1,
                      'detail-pip--max': affix1 === 6,
                    }"
                    @click="emit('update:affix1', level)"
                  />
                </div>
                <span class="detail-attr-value" :class="{ 'detail-attr-value--full': affix1 === 6 }">
                  +{{ affix1 }} / 6
                </span>
              </div>

              <div class="detail-attr-control detail-attr-control--teal">
                <span class="detail-attr-label">附加属性</span>
                <div class="detail-attr-pips">
                  <span
                    v-for="level in affixLevelItems"
                    :key="`d-a2-${level}`"
                    class="detail-pip"
                    :class="{
                      active: level <= affix2,
                      'detail-pip--max': affix2 === 6,
                    }"
                    @click="emit('update:affix2', level)"
                  />
                </div>
                <span class="detail-attr-value" :class="{ 'detail-attr-value--full': affix2 === 6 }">
                  +{{ affix2 }} / 6
                </span>
              </div>

              <div class="detail-attr-control detail-attr-control--indigo">
                <span class="detail-attr-label">技能属性</span>
                <div class="detail-attr-pips detail-attr-pips--skill">
                  <span
                    v-for="level in skillLevelItems"
                    :key="`d-a3-${level}`"
                    class="detail-pip"
                    :class="{
                      active: level <= affix3,
                      'detail-pip--max': affix3 === 3,
                    }"
                    @click="emit('update:affix3', level)"
                  />
                </div>
                <span class="detail-attr-value" :class="{ 'detail-attr-value--full': affix3 === 3 }">
                  +{{ affix3 }} / 3
                </span>
              </div>
            </div>

            <!-- 未拥有斜向胶带遮罩 -->
            <div v-if="!isOwned" class="not-owned-tape-detail">
              <span class="not-owned-tape-detail-text">» 未拥有 » NOT OWNED » 未拥有 » NOT OWNED » </span>
            </div>
          </div>

          <!-- 拥有状态切换 -->
          <div class="mt-2">
            <v-chip
              :color="isOwned ? 'success' : 'grey'"
              :prepend-icon="isOwned ? 'mdi-check-circle' : 'mdi-close-circle'"
              size="small"
              variant="tonal"
              @click="emit('toggle-ownership')"
            >
              {{ isOwned ? '已拥有' : '未拥有 · 点击切换为拥有' }}
            </v-chip>
          </div>
        </div>

        <!-- 扩展插槽：等级之后的内容（如优先级选择器） -->
        <slot name="after-levels" />

        <!-- 同类武器 -->
        <slot name="same-stat-weapons">
          <div v-if="!isCustom && !isNewCustom && sameStatWeapons.length > 0">
            <div class="text-subtitle-2 mb-2">同类属性武器</div>
            <div class="d-flex flex-column ga-2">
              <v-card
                v-for="same in sameStatWeapons"
                :key="same.id"
                class="pa-2"
                variant="outlined"
              >
                <div class="d-flex align-center justify-space-between">
                  <div class="d-flex align-center ga-2">
                    <item-icon class="weapon-icon-same" :item-id="same.id" />
                    <div>
                      <div class="font-weight-bold text-body-2">
                        {{ same.name }}
                      </div>
                      <div v-if="same.levelText || same.priorityText" class="text-caption text-medium-emphasis">
                        {{ same.levelText }}
                        <span v-if="same.priorityText" class="ml-1">{{ same.priorityText }}</span>
                      </div>
                    </div>
                  </div>
                  <slot name="same-stat-action" :weapon-id="same.id">
                    <v-btn
                      v-if="showSwap"
                      color="primary"
                      size="small"
                      variant="tonal"
                      @click="emit('swap-matrix', weaponId!, same.id)"
                    >
                      交换
                    </v-btn>
                  </slot>
                </div>
              </v-card>
            </div>
          </div>
          <div v-else-if="!isCustom && !isNewCustom && sameStatWeapons.length === 0" class="text-medium-emphasis text-caption">
            没有其他武器与此武器共享相同属性组合。
          </div>
        </slot>
      </v-card-text>

      <!-- 操作按钮 -->
      <v-divider />
      <v-card-actions>
        <slot name="actions" />
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script lang="ts" setup>
import { computed } from 'vue'
import CustomStatIcon from '@/components/CustomStatIcon.vue'
import ItemIcon from '@/components/ItemIcon.vue'
import { useStaticData } from '@/utils/gameData/staticData'
import { getGemTagName } from '@/utils/gameData/weapon'

export interface SameStatWeapon {
  id: string
  name: string
  levelText?: string
  priorityText?: string
}

const { weaponsMap, essencesMap } = useStaticData()

const props = withDefaults(defineProps<{
  modelValue: boolean
  weaponId: string | null
  isNewCustom?: boolean
  customEntryName?: string
  customEditAttribute?: string | null
  customEditSecondary?: string | null
  customEditSkill?: string | null
  editableAttributes?: boolean
  isOwned?: boolean
  affix1?: number
  affix2?: number
  affix3?: number
  sameStatWeapons?: SameStatWeapon[]
  showSwap?: boolean
  customStats?: Array<{ name: string; attribute: string | null; secondary: string | null; skill: string | null }>
}>(), {
  isNewCustom: false,
  customEntryName: '',
  customEditAttribute: null,
  customEditSecondary: null,
  customEditSkill: null,
  editableAttributes: false,
  isOwned: false,
  affix1: 1,
  affix2: 1,
  affix3: 1,
  sameStatWeapons: () => [],
  showSwap: false,
  customStats: () => [],
})

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  'update:customEntryName': [value: string]
  'update:customEditAttribute': [value: string | null]
  'update:customEditSecondary': [value: string | null]
  'update:customEditSkill': [value: string | null]
  'update:affix1': [value: number]
  'update:affix2': [value: number]
  'update:affix3': [value: number]
  'toggle-ownership': []
  'save-custom': []
  'delete-custom': []
  'remove-entry': [weaponId: string]
  'swap-matrix': [weaponA: string, weaponB: string]
}>()

// --- 等级选项 ---
const affixLevelItems = [1, 2, 3, 4, 5, 6]
const skillLevelItems = [1, 2, 3]

// --- 属性选项列表 ---
const allAttributeStats = computed(() =>
  Array.from(essencesMap.value.values())
    .filter((e) => e.type === 'ATTRIBUTE')
    .map((e) => e.id),
)
const allSecondaryStats = computed(() =>
  Array.from(essencesMap.value.values())
    .filter((e) => e.type === 'SECONDARY')
    .map((e) => e.id),
)
const allSkillStats = computed(() =>
  Array.from(essencesMap.value.values())
    .filter((e) => e.type === 'SKILL')
    .map((e) => e.id),
)

const attributeStatOptions = computed(() =>
  allAttributeStats.value.map((id) => ({ title: getGemTagName(id), value: id })),
)
const secondaryStatOptions = computed(() =>
  allSecondaryStats.value.map((id) => ({ title: getGemTagName(id), value: id })),
)
const skillStatOptions = computed(() =>
  allSkillStats.value.map((id) => ({ title: getGemTagName(id), value: id })),
)

// --- 计算属性 ---
const isCustom = computed(() => {
  if (!props.weaponId) return false
  return props.weaponId.startsWith('custom_stat_') || props.isNewCustom
})

const weaponName = computed(() => {
  if (!props.weaponId) return ''
  return weaponsMap.value.get(props.weaponId)?.name || props.weaponId
})

const attributeStatId = computed(() => {
  if (props.isNewCustom || (props.weaponId?.startsWith('custom_stat_') && props.editableAttributes)) {
    return props.customEditAttribute
  }
  if (props.weaponId?.startsWith('custom_stat_')) {
    return getCustomStatAttribute(props.weaponId)
  }
  return weaponsMap.value.get(props.weaponId!)?.attributeStatId ?? null
})

const secondaryStatId = computed(() => {
  if (props.isNewCustom || (props.weaponId?.startsWith('custom_stat_') && props.editableAttributes)) {
    return props.customEditSecondary
  }
  if (props.weaponId?.startsWith('custom_stat_')) {
    return getCustomStatSecondary(props.weaponId)
  }
  return weaponsMap.value.get(props.weaponId!)?.secondaryStatId ?? null
})

const skillStatId = computed(() => {
  if (props.isNewCustom || (props.weaponId?.startsWith('custom_stat_') && props.editableAttributes)) {
    return props.customEditSkill
  }
  if (props.weaponId?.startsWith('custom_stat_')) {
    return getCustomStatSkill(props.weaponId)
  }
  return weaponsMap.value.get(props.weaponId!)?.skillStatId ?? null
})

// --- 自定义基质辅助函数 ---
function getCustomStatName(weaponId: string): string {
  const index = Number.parseInt(weaponId.replace('custom_stat_', ''), 10)
  return props.customStats[index]?.name || `自定义基质 ${index + 1}`
}

function getCustomStatAttribute(weaponId: string): string | null {
  const index = Number.parseInt(weaponId.replace('custom_stat_', ''), 10)
  return props.customStats[index]?.attribute || null
}

function getCustomStatSecondary(weaponId: string): string | null {
  const index = Number.parseInt(weaponId.replace('custom_stat_', ''), 10)
  return props.customStats[index]?.secondary || null
}

function getCustomStatSkill(weaponId: string): string | null {
  const index = Number.parseInt(weaponId.replace('custom_stat_', ''), 10)
  return props.customStats[index]?.skill || null
}
</script>

<style scoped lang="scss">
.weapon-icon-detail {
  width: 3rem !important;
  height: 3rem !important;
}

.detail-level-wrapper {
  position: relative;
}

.detail-level-section {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}

.detail-attr-control {
  flex: 1;
  min-width: 120px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 10px 12px;
  border: 1px solid rgba(var(--v-border-color), 0.12);
  border-radius: 12px;
  transition: background 0.18s;

  &:hover {
    background: rgba(var(--v-theme-on-surface), 0.03);
  }
}

.detail-attr-label {
  color: rgba(var(--v-theme-on-surface), 0.52);
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.detail-attr-pips {
  display: flex;
  align-items: center;
  gap: 4px;
  min-height: 20px;
}

.detail-pip {
  width: 10px;
  height: 20px;
  border-radius: 999px;
  background: rgba(var(--v-theme-on-surface), 0.12);
  cursor: pointer;
  transition: background 0.18s, box-shadow 0.18s, transform 0.18s;

  &:hover {
    transform: translateY(-1px) scaleY(1.08);
  }
}

.detail-attr-control--primary .detail-pip.active {
  background: rgb(var(--v-theme-primary));
  box-shadow: 0 2px 7px rgba(var(--v-theme-primary), 0.32);
}

.detail-attr-control--teal .detail-pip.active {
  background: #48a9a6;
  box-shadow: 0 2px 7px rgba(72, 169, 166, 0.34);
}

.detail-attr-control--indigo .detail-pip.active {
  background: #5c6bc0;
  box-shadow: 0 2px 7px rgba(92, 107, 192, 0.34);
}

.detail-pip.detail-pip--max.active {
  animation: detailPipPulse 2.2s ease-in-out infinite;
}

.detail-attr-value {
  color: rgba(var(--v-theme-on-surface), 0.68);
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
  font-size: 0.85rem;
  font-weight: 800;
}

.detail-attr-value--full {
  color: rgb(var(--v-theme-primary));
}

@keyframes detailPipPulse {
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

.not-owned-tape-detail {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 110%;
  height: 24px;
  background: linear-gradient(
    135deg,
    rgba(255, 193, 7, 0.95) 0%,
    rgba(255, 193, 7, 0.88) 40%,
    rgba(255, 193, 7, 0.8) 100%
  );
  transform: translate(-50%, -50%) rotate(-8deg);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 5;
  pointer-events: none;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.25);
}

.not-owned-tape-detail-text {
  color: rgba(0, 0, 0, 0.8);
  font-size: 0.8rem;
  font-weight: 900;
  letter-spacing: 0.2em;
  white-space: nowrap;
}

.weapon-icon-same {
  width: 2rem !important;
  height: 2rem !important;
  flex-shrink: 0;
}
</style>
